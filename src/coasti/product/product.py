"""
Product related backend logic.

# Abstraction

config/products.yml

ProductsYamlIO  (loaded yaml of all products with io features, getters for products)
    .get_product()      -> Product
    .get_product_data() -> ProductData

ProductData  (yaml fields per Prodouct inside config/products.yml)

Product         (in RAM Instance around ProductData with functions to install etc)
    .write()    to update ProductData and write back into yaml
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import os
import sys
from pathlib import Path
from typing import cast

import copier
from ruamel.yaml import YAML, CommentedMap

from coasti.git import copier_git_injection
from coasti.logger import log
from coasti.prompt import PromptResponse

from .questions import ProductData, AUTH_SENTINEL

yaml = YAML()


class ProductsYamlIO:
    """
    Manage products configuration.

    Convenient r/w access to config/products.yml
    """

    coasti_base_dir: Path
    _yaml_data: CommentedMap | None

    def __init__(self, coast_base_dir: Path | None = None) -> None:
        # FIXME: this should be a typer callback.
        self.coasti_base_dir = coast_base_dir or Path(
            os.getenv("COASTI_BASE_DIR", Path.cwd())
        )
        self._yaml_data = None

    @classmethod
    @contextmanager
    def edit(cls, coast_base_dir: Path | None = None):
        """
        Create a ProductsYamlIO, allow edits, and persist products.yml on exit.

        All changes to products should happen in this context.

        Usage:
        ```
        with ProductsYamlIO.edit() as pio:
            product = pio.get_product("some_id")
            product.write()
        ```
        """
        self = cls(coast_base_dir=coast_base_dir)
        _ = self.yaml_data  # ensure loaded before edits
        try:
            yield self
        finally:
            self.write()

    @property
    def yaml_data(self) -> CommentedMap:
        if self._yaml_data is None:
            self._yaml_data = self._load_products_config()
        return cast(CommentedMap, self._yaml_data)

    @property
    def yaml_path(self):
        """Get the abs path to the products yaml."""
        products_yaml_path = self.coasti_base_dir / "config" / "products.yml"
        if not products_yaml_path.is_file():
            raise ValueError(
                "Could not find config/products.yml. Call from a coasti project, "
                "or set COASTI_BASE_DIR"
            )
        return products_yaml_path

    @property
    def product_ids(self) -> list[str]:
        """Product ids"""
        return [p["id"] for p in self.yaml_data["products"]]

    def get_product(self, pid: str):
        entry = self.get_enry(pid)
        return Product(data=entry, yaml_io=self)

    def get_enry(self, pid: str):
        entries = self.yaml_data["products"]
        return [e for e in entries if e.get("id") == pid][0]

    def _load_products_config(self):
        config = yaml.load(self.yaml_path)
        if not isinstance(config, CommentedMap) or "products" not in config.keys():
            raise ValueError(
                "Could not find the products section in config/products.yml."
            )
        # this is a list in yaml, but it might not have any entries, and be none.
        config["products"] = config.get("products") or []
        return config

    def write(self):
        with self.yaml_path.open("w") as f:
            yaml.dump(self.yaml_data, f)

    def upsert_product(self, product: Product):
        """Save product data to yaml, overwriting if already found.

        Does not handle anything beyond the yaml writes."""

        # FIXME: remove this check once we are sure it stripped reliably by product.
        assert product.data.get("vcs_auth_value", AUTH_SENTINEL) == AUTH_SENTINEL

        if product.id in self.product_ids:
            entry = self.get_enry(product.id)
            log.debug(
                f"Upating {product.id} in products.yml: {entry} ---> {product.data}"
            )
            entry.update(product.data)
        else:
            log.debug(f"Adding {product.id} to products.yml: {product.data}")
            self.yaml_data["products"].append(product.data)

        log.info(f"Updated {product.id} in products.yml")


class Product:
    """
    View on an individual product.

    Contains:
    - ProductData that resembles the yaml, for this particular product
    - write method, to update the (many-products) yaml via ProductsYamlIO
    - io for this products features, like the secrets
    - install and update methods

    To presist a product, use an io context:
    ```
    with ProductsYamlIO.edit() as pio:
        product = pio.get_product("some_id")
        product.write()
    ```
    """

    data: ProductData
    # try not to keep auth_tokens in ram, when constructing, dump and then use properties.
    # use senitnal value for load_from_disk
    yaml_io: ProductsYamlIO

    def __init__(
        self,
        yaml_io: ProductsYamlIO,
        data: ProductData | PromptResponse[ProductData],
    ) -> None:

        self.yaml_io = yaml_io
        if isinstance(data, PromptResponse):
            data = data.answers
        self.data = deepcopy(data)

    @property
    def id(self):
        return self.data["id"]

    @property
    def secret_path(self):
        return self.coasti_base_dir / "config" / "secrets" / f"vcs_auth_{self.id}"

    @property
    def coasti_base_dir(self):
        return self.yaml_io.coasti_base_dir.absolute()

    @property
    def dst_path(self):
        return self.coasti_base_dir / self.data["dst_path"]

    @property
    def vcs_auth_type(self):
        return self.data["vcs_auth_type"]

    @property
    def vcs_auth_value(self):
        """Get auth secret from file (or ram).

        None if no auth configured.
        """
        if self.vcs_auth_type == "skip":
            return None

        res = self.data.get("vcs_auth_token", AUTH_SENTINEL)
        if res := AUTH_SENTINEL:
            if not self.secret_path.is_file():
                log.warning(f"{self.id} auth value neither in details nor in file")
            res = self.secret_path.read_text()
        return res

    @property
    def vcs_auth_token(self):
        if self.data["vcs_auth_type"] != "Auth Token":
            return None
        return self.vcs_auth_value

    @property
    def vcs_auth_sshkeypath(self):
        if self.data["vcs_auth_type"] != "SSH Key":
            return None
        return self.vcs_auth_value

    def write(self):
        """Persiste the current state of this product.

        Updates the yaml, and persists auth tokens.
        """
        if (
            self.vcs_auth_type != "skip"
            and self.data.get("vcs_auth_value", AUTH_SENTINEL) != AUTH_SENTINEL
        ):
            self._write_and_clear_secrets()
        self.yaml_io.upsert_product(self)

    def _write_and_clear_secrets(self):
        """Take unmasked answers and save auth token or ssh key path to file.

        After export, sets the unmasked answers to AUTH_SENTINEL.
        """

        auth = self.data.get("vcs_auth_value", AUTH_SENTINEL)

        if auth == AUTH_SENTINEL:
            log.debug("Secret only holds sentinale value, skipping export")
        elif not self.secret_path.is_file():
            log.debug(f"New secret, saving to {str(self.secret_path)}")
            self.secret_path.write_text(auth)
        elif self.secret_path.read_text() != auth:
            log.info(f"Secret changed, overwriting {str(self.secret_path)}")
            self.secret_path.write_text(auth)
        else:
            log.debug("Secret has not changed, skipping export")

        # Now we are sure that secrets are in file, so lets remove them from RAM
        self.data["vcs_auth_value"] = AUTH_SENTINEL

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
                src_path=self.data["vcs_repo"],
                dst_path=self.dst_path,
                vcs_ref=self.data["vcs_ref"],
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
            vcs_ref = self.data["vcs_ref"]
        elif vcs_ref != self.data["vcs_ref"] and self.yaml_io is not None:
            log.debug(f"Updating products.yml to new vcs_ref '{vcs_ref}'")
            # FIXME: add upsert method in ProductsConfig that handles token removal etc
            pid = self.id
            product_yaml = [p for p in self.yaml_io.products if p["id"] == pid][0]
            product_yaml["vcs_ref"] = vcs_ref
            self.data["vcs_ref"] = vcs_ref
            self.yaml_io.write()

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
