from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

import copier
import copier._vcs as copier_vcs
from ruamel.yaml import YAML, CommentedMap

from coasti.logger import log
from coasti.prompt import PromptResponse

yaml = YAML()


class ProductsConfig:
    coasti_base_dir: Path
    products_config: CommentedMap

    def __init__(self, coast_base_dir: Path | None = None) -> None:
        self.coasti_base_dir = coast_base_dir or Path(
            os.getenv("COASTI_BASE_DIR", Path.cwd())
        )
        self._load_products_config()

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

    def get_product(self, pid : str):
        details = self.get_product_details(pid)
        return Product(details=details, coasti_base_dir=self.coasti_base_dir)

    def _load_products_config(self):
        config = yaml.load(self.products_yaml_path)
        if not isinstance(config, CommentedMap) or "products" not in config.keys():
            raise ValueError(
                "Could not find the products section in config/products.yml."
            )
        # this is a list in yaml, but it might not have any entries, and be none.
        config["products"] = config.get("products") or []
        self.products_config = config
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
    details: ProductDetails
    coasti_base_dir: Path

    def __init__(self, coasti_base_dir: Path, details: ProductDetails) -> None:
        self.details = details
        self.coasti_base_dir = coasti_base_dir.absolute()

    @property
    def id(self):
        return self.details["id"]

    @property
    def secret_path(self):
        return self.coasti_base_dir / "config" / "secrets" / f"vcs_auth_{self.id}"

    @property
    def dst_path(self):
        return Path(self.details["dst_path"]).absolute()

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

    def update(self):
        """
        Update this product by getting its resources via copier.
        Authentication is retrieved from disk and injected into the git commands.
        """

        # Clone template
        with copier_git_injection(
            https_token=self.vcs_auth_token,
            ssh_key_path=self.vcs_auth_sshkeypath,
        ):
            log.info(f"Using copier to update {self.id}. Downloading...")
            copier.run_update(
                dst_path=self.dst_path,
                answers_file="config/install_answers.yml",
                unsafe=True,
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


class ProductDetails(TypedDict):
    # see questions/copier.yml
    vcs_repo: str
    id: str
    dst_path: str
    vcs_ref: str
    vcs_auth_type: Literal["skip", "Auth Token", "SSH Key"]
    vcs_auth_token: NotRequired[str]
    vcs_auth_sshkeypath: NotRequired[str]


@contextmanager
def copier_git_injection(
    *,
    https_token: str | None = None,
    ssh_key_path: str | Path | None = None,
) -> Iterator[None]:
    """
    Inject auth settings into all git commands executed by Copier.

    - https_token: used for HTTPS clones/fetches via GIT_ASKPASS.
    - ssh_key_path: absolute path to an SSH private key to force for SSH clones/fetches.

    We monkeypatch copiers get_git() command to keep env vars in a small scope.
    """
    if ssh_key_path is not None and https_token is not None:
        raise ValueError("Provide either https_token or ssh_key_path")

    if ssh_key_path is not None and not Path(ssh_key_path).is_absolute():
        raise ValueError("ssh_key_path must be an absolute path")

    original_get_git = copier_vcs.get_git

    try:
        extra_env = {}

        if https_token:
            with resources.as_file(
                resources.files("coasti.product").joinpath(
                    "askpass" + (".bat" if sys.platform == "win32" else ".sh")
                )
            ) as askpass_script:
                extra_env["GIT_ASKPASS"] = askpass_script
                # scripts simply return the token env var

            extra_env["GIT_AUTH_TOKEN"] = https_token
            extra_env["GIT_TERMINAL_PROMPT"] = "0"
            # Some git flows require this to force askpass in non-tty contexts:

        elif ssh_key_path:
            extra_env["GIT_SSH_COMMAND"] = (
                f"ssh -i {ssh_key_path} -o IdentitiesOnly=yes"
            )

        def patched_get_git():
            git = original_get_git()
            # Attach env to the command object.
            # (Plumbum supports cmd.with_env(VAR=...))
            cmd = git.with_env(**extra_env) if extra_env else git
            return cmd

        copier_vcs.get_git = patched_get_git
        yield
    finally:
        copier_vcs.get_git = original_get_git
