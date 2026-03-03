from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import cast

import copier
from ruamel.yaml import YAML, CommentedMap

from coasti.git import copier_git_injection
from coasti.logger import log
from coasti.prompt import PromptResponse

from .questions import ProductDetails

yaml = YAML()


class ProductsConfig:
    """
    Manage products configuration.

    Convenient access to config/products.yml and writing into it
    """

    coasti_base_dir: Path
    _products_config: CommentedMap | None

    def __init__(self, coast_base_dir: Path | None = None) -> None:
        self.coasti_base_dir = coast_base_dir or Path(
            os.getenv("COASTI_BASE_DIR", Path.cwd())
        )
        self._products_config = None

    @property
    def products_config(self) -> CommentedMap:
        if self._products_config is None:
            self._products_config = self._load_products_config()
        return cast(CommentedMap, self._products_config)

    @property
    def products_yaml_path(self):
        """Get the abs path to the products yaml."""
        products_yaml_path = self.coasti_base_dir / "config" / "products.yml"
        if not products_yaml_path.is_file():
            raise ValueError(
                "Could not find config/products.yml. Call from a coasti project, "
                "or set COASTI_BASE_DIR"
            )
        return products_yaml_path

    @property
    def products(self) -> list[ProductDetails]:
        """Loaded product details from config/products.yml"""
        return self.products_config["products"]

    @property
    def product_ids(self) -> list[str]:
        return [p["id"] for p in self.products_config["products"]]

    def get_product_details(self, pid):
        return [p for p in self.products if p.get("id") == pid][0]

    def get_product(self, pid: str):
        details = self.get_product_details(pid)
        return Product(
            details=details, coasti_base_dir=self.coasti_base_dir, config=self
        )

    def _load_products_config(self):
        config = yaml.load(self.products_yaml_path)
        if not isinstance(config, CommentedMap) or "products" not in config.keys():
            raise ValueError(
                "Could not find the products section in config/products.yml."
            )
        # this is a list in yaml, but it might not have any entries, and be none.
        config["products"] = config.get("products") or []
        return config

    def save_products_config(self):
        with self.products_yaml_path.open("w") as f:
            yaml.dump(self.products_config, f)

    def upsert_product_from_answers(self, p_res: PromptResponse[ProductDetails]):
        """
        Insert or update a product to our yaml based on a questionaire.
        The `.answers` in the PromptResponse should be ProductDetails.
        """
        p = Product(details=p_res.answers, coasti_base_dir=self.coasti_base_dir)
        p.save_secrets()

        pid = p_res.answers["id"]
        if pid in self.product_ids:
            product = [p for p in self.products if p["id"] == pid][0]
            product.update(p_res.answers_to_remember)
        else:
            self.products.append(p_res.answers_to_remember)


class Product:
    """
    Thin wrapper around ProductDetails with functions to install.

    ProductDetails are a set of yaml variables, that is consistent for each
    list item in config/products.yml.
    """

    details: ProductDetails
    coasti_base_dir: Path
    config: ProductsConfig | None

    def __init__(
        self,
        coasti_base_dir: Path,
        details: ProductDetails,
        config: ProductsConfig | None = None,
    ) -> None:
        self.details = details
        self.coasti_base_dir = coasti_base_dir.absolute()
        self.config = config

    @property
    def id(self):
        return self.details["id"]

    @property
    def secret_path(self):
        return self.coasti_base_dir / "config" / "secrets" / f"vcs_auth_{self.id}"

    @property
    def dst_path(self):
        return self.coasti_base_dir / self.details["dst_path"]

    @property
    def vcs_auth_token(self):
        if self.details["vcs_auth_type"] != "Auth Token":
            return None

        res = self.details.get("vcs_auth_token", None)
        if res is None:
            if not self.secret_path.exists():
                log.warning(f"{self.id} auth token neither in details nor in file")
            res = self.secret_path.read_text()
        return res

    @property
    def vcs_auth_sshkeypath(self):
        if self.details["vcs_auth_type"] != "SSH Key":
            return None

        res = self.details.get("vcs_auth_sshkeypath", None)
        if res is None:
            if not self.secret_path.exists():
                log.warning(f"{self.id} sshkeypath neither in details nor in file")
            res = self.secret_path.read_text()
        return res

    def save_secrets(self):
        """Take unmasked answers and save auth token or ssh key path to file."""
        if self.details["vcs_auth_type"] == "Auth Token":
            auth = self.details.get("vcs_auth_token")
        elif self.details["vcs_auth_type"] == "SSH Key":
            auth = self.details.get("vcs_auth_sshkeypath")
        else:
            log.debug(
                f"No secrets to write for auth type {self.details['vcs_auth_type']}"
            )
            return

        if auth is None:
            raise ValueError("To save secrets, provide them in ProductDetails.")

        self.secret_path.write_text(auth)

    def install(self):
        """
        Install this product by getting its resources via copier.
        Authentication is retrieved from disk and injected into the git commands.
        """

        # Clone template
        with copier_git_injection(
            https_token=self.vcs_auth_token,
            ssh_key_path=self.vcs_auth_sshkeypath,
        ):
            log.info(f"Using copier to install {self.id}. Downloading...")
            copier.run_copy(
                src_path=self.details["vcs_repo"],
                dst_path=self.dst_path,
                vcs_ref=self.details["vcs_ref"],
                unsafe=True,
            )

        self._create_symlinks()

    def update(self, vcs_ref: str | None):
        """
        Update this product by getting its resources via copier.
        Authentication is retrieved from disk and injected into the git commands.

        Notes
        -----
        - Copier might log "No git tags found in template; using HEAD as ref",
          because it looks for tags in the outer (coasti) repo to compare with
          the remote (content) repo, and you will likely not have tags there.
        """

        if vcs_ref is None:
            vcs_ref = self.details["vcs_ref"]
        elif vcs_ref != self.details["vcs_ref"] and self.config is not None:
            log.debug(f"Updating products.yml to new vcs_ref '{vcs_ref}'")
            # FIXME: add upsert method in ProductsConfig that handles token removal etc
            pid = self.id
            product_yaml = [p for p in self.config.products if p["id"] == pid][0]
            product_yaml["vcs_ref"] = vcs_ref
            self.details["vcs_ref"] = vcs_ref
            self.config.save_products_config()

        # Clone template
        with copier_git_injection(
            https_token=self.vcs_auth_token,
            ssh_key_path=self.vcs_auth_sshkeypath,
        ):
            log.info(
                f"Using copier to update {self.id} (vcs_ref {vcs_ref}). Downloading..."
            )
            copier.run_update(
                dst_path=self.dst_path,
                answers_file="config/install_answers.yml",
                unsafe=True,  # trust templates, needed because they might have tasks
                overwrite=True,  # needs to be true for copier update of subprojects
                skip_answered=True,
                skip_tasks=False,  # Content package can and should decide this per task
                vcs_ref=vcs_ref,
            )

    def _create_symlinks(self):
        log.info(f"Creating symlinks for {self.id}")
        for part in ["config", "config/secrets", "data", "logs"]:
            if (dst := self.dst_path / part).exists():
                src = self.coasti_base_dir / part / self.id
                try:
                    src.symlink_to(dst)
                    log.debug(f"Created symlink {str(src)} -> {str(dst)}")
                except FileExistsError:
                    log.debug(f"Link target already exists ({str(dst)})")
                except OSError as e:
                    if sys.platform == "win32":
                        log.info(
                            "Cannot create symlinks on Windows "
                            f"without admin permissions ({str(dst)})"
                        )
                    else:
                        log.error(e)
                except Exception as e:
                    log.error(e)


