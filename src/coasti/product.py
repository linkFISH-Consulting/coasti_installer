import json
import logging
import os
import random
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import typer

from .logger import log


@dataclass(init=False)
class Product:
    name: str
    url: str
    branch: str
    auth_token: str | None
    path: Path  # products live in a products/ folder inside another repo

    def __init__(
        self,
        name: str,
        url: str,
        path: Path,
        auth_token: str | None = None,
        branch: str = "main",
    ):
        self.name = name
        self.url = url
        self.branch = branch
        self.auth_token = auth_token
        self.path = path

    @classmethod
    def from_yaml_config(cls, config: dict, path: Path | None = None):
        return cls(
            name=config["name"],
            url=config["url"],
            branch=config.get("branch", "main"),
            auth_token=config.get("auth_token"),
            path=path or Path.cwd(),
        )

    @property
    def install_method(self) -> Literal["subtree", "clone"]:
        """
        How was this product installed? Checks for the presence of a .git folder.
        """
        if (Path(f"products/{self.name}/.git")).is_dir():
            return "clone"
        else:
            return "subtree"

    def install(self, method=Literal["subtree", "clone", "update"]):
        """
        Install or update the product.

        Parameters
        ----------
        method : str
            Method to install the product. Can be either "subtree" or "clone".
            Defaults to "subtree" which will create a commit in the git history and
            is recommended for production.
            "clone" will only clone the repo, and not touch the version control
            of the parent repo.
            "update" will detect the used install method (is a .git folder present?)
            and update either via subtree or git pull.
        path_prefix : str
            Prefix for the path where the product will be installed. Defaults to "products/".
        """

        is_update = False
        if method == "update":
            is_update = True
            method = self.install_method
            log.debug(f"Updating {self.name} (as installed via '{method}')")
            if method == "subtree":
                # ask for cli confirm
                if not typer.confirm(
                    f"{self.name} was installed via subtree. "
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
                    f"Automatic install of {self.name} (branch {self.branch})\n{self.url}"
                    if not is_update
                    else f"Automatic update of {self.name} (branch {self.branch})\n{self.url}",
                ]
                subprocess.run(
                    cmd,
                    check=True,  # raise if not successfull
                )
            except subprocess.CalledProcessError:
                log.error(
                    f"Failed to clone {self.name} from {self.url} on branch {self.branch}"
                )
                raise typer.Exit(code=1)
        elif method == "clone":
            log.info(f"Installing {self.name} via git clone.")
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
                    f"Failed to clone {self.name} from {self.url} on branch {self.branch}"
                )
                raise typer.Exit(code=1)

    @property
    def url_authenticated(self):
        if self.auth_token is None or self.url.startswith("git@"):
            log.debug(f"Using ssh to get {self.url}")
            return self.url

        # https://forum.gitlab.com/t/how-to-git-clone-via-https-with-personal-access-token-in-private-project/43418/4

        repo = self.url.lstrip("https://").lstrip("http://")
        return f"https://oauth2:{self.auth_token}@{repo}"

    @property
    def version(self):
        # this is our code version. Read git?
        # or .version file in the installed code.
        pass

    @property
    def vorsystem_version(self):
        # Note: this is inside the container!
        # helper to get the version needed before ingestion
        # 1. ingestions tool gets version
        # 2. coasti checks compatibilities, and possibly haults
        # 3. ingestion runs, (depending on version, but checks version internally again)
        pass

    @property
    def is_ingestion_tool_working(self):
        # inside the container!
        pass

    def __str__(self):
        return f"{self.name} ({self.url})"

    def __repr__(self):
        return str(self)
