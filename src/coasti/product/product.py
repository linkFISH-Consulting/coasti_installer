import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import typer

from ..logger import log


@dataclass(init=False)
class Product:
    id: str
    url: str
    branch: str
    auth: str
    path: Path  # products live in a products/ folder inside another repo

    def __init__(
        self,
        id: str,
        url: str,
        path: Path,
        auth: str = "skip",
        branch: str = "main",
    ):
        self.id = id
        self.url = url
        self.branch = branch
        self.auth = auth
        self.path = path


    @classmethod
    def from_yaml_config(cls, config: dict, path: Path | None = None):
        return cls(
            id=config["id"],
            url=config["url"],
            branch=config.get("branch", "main"),
            auth=config.get("auth", "skip"),
            path=path or Path.cwd(),
        )

    def install(self, method=Literal["subtree", "clone", "update"]):
        """
        Install or update the product.

        Parameters
        ----------
        method : str
            Method to install the product.
            - "subtree" (default) will create a commit in the git history and
            is recommended for production.
            - "clone" will only clone the repo, and not touch the version control
            of the parent repo.
            - "update" will detect the used install method (is a .git folder present?)
            and update either via subtree or git pull.
        """

        is_update = False
        if method == "update":
            is_update = True
            method = self.install_method
            log.debug(f"Updating {self.id} (as installed via '{method}')")
            if method == "subtree":
                # ask for cli confirm
                if not typer.confirm(
                    f"{self.id} was installed via subtree. "
                     "Updating will create a commit.\nContinue?",
                ):
                    log.info("Skipping.")
                    return

        # default for production
        if method == "subtree":
            # check git is clean
            if subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True
            ).stdout:
                log.error(
                    "Cannot install products with uncomitted changes in your repo!"
                )
                raise typer.Exit(code=1)

            try:
                cmd = [
                    "git",
                    "subtree",
                    "add" if not is_update else "pull",
                    "--prefix",
                    f"{self.path}",
                    self.url_authenticated,
                    self.branch,
                    "--squash",
                    "--message",
                    f"Automatic install of {self.id} (branch {self.branch})\n{self.url}"
                    if not is_update
                    else f"Automatic update of {self.id} (branch {self.branch})\n{self.url}",
                ]
                subprocess.run(
                    cmd,
                    check=True,  # raise if not successfull
                )
            except subprocess.CalledProcessError:
                log.error(
                    f"Failed to clone {self.id} from {self.url} on branch {self.branch}"
                )
                raise typer.Exit(code=1)
        elif method == "clone":
            log.info(f"Installing {self.id} via git clone.")
            try:
                if is_update:
                    cmd = [
                        "git",
                        "-C",
                        f"{self.path}",
                        "pull",
                    ]
                else:
                    cmd = [
                        "git",
                        "clone",
                        "--branch",
                        self.branch,
                        self.url_authenticated,
                        f"{self.path}",
                    ]
                subprocess.run(
                    cmd,
                    check=True,  # raise if not successful
                )
            except subprocess.CalledProcessError:
                log.error(
                    f"Failed to clone {self.id} from {self.url} on branch {self.branch}"
                )
                raise typer.Exit(code=1)

    @property
    def url_authenticated(self):
        if self.auth == 'None' or self.url.startswith("git@"):
            log.debug(f"Using ssh to get {self.url}")
            return self.url

        # https://forum.gitlab.com/t/how-to-git-clone-via-https-with-personal-access-token-in-private-project/43418/4

        repo = self.url.lstrip("https://").lstrip("http://")
        return f"https://oauth2:{self.auth}@{repo}"

    @property
    def install_method(self) -> Literal["subtree", "clone"]:
        """
        How was this product installed? Checks for the presence of a .git folder.
        """
        if (Path(f"products/{self.id}/.git")).is_dir():
            return "clone"
        else:
            return "subtree"


    def __str__(self):
        return f"{self.id} ({self.url})"

    def __repr__(self):
        return str(self)
