from __future__ import annotations

from importlib import resources
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Annotated

import copier
import copier._vcs as copier_vcs
import typer
from ruamel.yaml import YAML, CommentedMap

from ..logger import log, setup_logging
from .answer import get_answers_from_template

yaml = YAML()
app = typer.Typer()


@app.command()
def list():
    """List installed products."""

    _, config = get_and_check_products_yaml()
    products = config.get("products") or []

    typer.echo(typer.style("products:", fg=typer.colors.BRIGHT_BLACK))
    for p in products:
        typer.echo(
            typer.style(f"- name: {p.get('name')}", fg=typer.colors.WHITE, bold=True)
        )
        for key, value in p.items():
            if key != "name":
                typer.echo(
                    typer.style(f"  {key}: {value}", fg=typer.colors.BRIGHT_BLACK)
                )


@app.command()
def add(
    vcs_repo: Annotated[
        str | None,
        typer.Argument(
            help="Url of the product's git repo.",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q",
            "--quiet",
            help="Don't ask questions, use all defaults, and overwrite.",
        ),
    ] = False,
):
    """Add a product to coasti."""

    products_yaml_path, config = get_and_check_products_yaml()

    with resources.path("coasti", "") as module_path:
        answers = get_answers_from_template(
            src_path=str(module_path / "product" / "questions"),
            data={"vcs_repo": vcs_repo},
            defaults=quiet,
        )

    # add to products.yml
    products = config.get("products") or []
    config["products"] = products
    product_ids = [p.get("id") for p in products if p.get("id")]
    pid = answers["id"]
    if pid in product_ids:
        if not quiet and not typer.prompt(
            f"Product id {pid} already exists. Overwrite? (y/n)\n", type=bool
        ):
            log.info("Exiting")
            raise typer.Exit(code=1)

        product: CommentedMap = [p for p in products if p["id"] == pid][0]
        product.clear()
        # to clear or not to clear?
        # dont want to loose comments but want to loose obsolete keys.
        product.update(answers)
    else:
        config["products"].append(answers)

    with products_yaml_path.open("w") as f:
        yaml.dump(config, f)

    # if we got auth info, place it in coasti-level secrets
    secrets_path = products_yaml_path.parent / "secrets" / f"vcs_auth_{pid}"
    if answers["vcs_auth_type"] == "Auth Token":
        secrets_path.write_text(answers["vcs_auth_token"])
    elif answers["vcs_auth_type"] == "SSH Key":
        secrets_path.write_text(answers["vcs_auth_sshkeypath"])

    log.info(f"Updated {pid} in {str(products_yaml_path)}")

    if answers["install_after_add"]:
        install(pid)


@app.command()
def install(
    pid: Annotated[
        str,
        typer.Argument(
            help="Id of the product.",
        ),
    ],
    verbose: Annotated[
        bool,
        typer.Option(
            "-v",
            "--verbose",
            help="Enable debug logging.",
        ),
    ] = False,
):
    """
    Fetch resources for a product that has already been added.

    Uses copier, git and details from config/products.yml
    """

    if verbose:
        setup_logging("DEBUG")

    products_yaml_path, config = get_and_check_products_yaml()
    products = config.get("products") or []
    product_ids = [p.get("id") for p in products if p.get("id")]
    if pid not in product_ids:
        log.error(
            f"{pid} not found in products. Available for install:\n  {product_ids}"
        )
        raise typer.Exit(code=1)

    # TODO: lets add a `products` class that knows the yaml and has getters, setters,
    # and the install logic
    details = [p for p in products if p.get("id") == pid][0]

    coasti_root = Path(os.getenv("COASTI_BASE_DIR", Path.cwd()))
    dst_path = coasti_root / details["dst_path"]
    src_path = str(details["vcs_repo"])
    vcs_ref = str(details["vcs_ref"])
    vcs_auth_type = str(details["vcs_auth_type"])
    vcs_auth = (products_yaml_path.parent / "secrets" / f"vcs_auth_{pid}").read_text()

    log.debug(f"Using copier copy on {pid} : {details}")

    with copier_git_injection(
        https_token=vcs_auth if vcs_auth_type == "Auth Token" else None,
        ssh_key_path=vcs_auth if vcs_auth_type == "SSH Key" else None,
    ):
        copier.run_copy(
            src_path=src_path,
            dst_path=dst_path,
            vcs_ref=vcs_ref,
            unsafe=True,
        )


def get_and_check_products_yaml():
    """Get the path to the products yaml, and check its structure is valid."""
    coasti_root = Path(os.getenv("COASTI_BASE_DIR", Path.cwd()))
    products_yaml_path = coasti_root / "config" / "products.yml"

    if not products_yaml_path.is_file():
        log.error(
            "Could not find config/products.yml. Call from a coasti project, "
            "or set COASTI_BASE_DIR"
        )
        raise typer.Exit(code=1)

    config = yaml.load(products_yaml_path)
    if not isinstance(config, CommentedMap) or "products" not in config.keys():
        raise ValueError("Could not find the products section in config/products.yml.")

    return products_yaml_path, config


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
