from __future__ import annotations

from importlib import resources
from typing import Annotated, Literal

import copier
import typer
from ruamel.yaml import YAML

from coasti.logger import log
from coasti.prompt import prompt_like_copier_from_template, prompt_single

from .product import ProductsConfig

yaml = YAML()
app = typer.Typer()


@app.command()
def list():
    """List installed products"""

    config = ProductsConfig()

    typer.echo(typer.style("products:", fg=typer.colors.BRIGHT_BLACK))
    for p in config.products:
        typer.echo(typer.style(f"- name: {p['id']}", fg=typer.colors.WHITE, bold=True))
        for key, value in p.items():
            if key != "id":
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
    """Add a product to coasti"""

    config = ProductsConfig()

    with resources.path("coasti", "") as module_path:
        p_res = prompt_like_copier_from_template(
            src_path=str(module_path / "product" / "questions"),
            data={"vcs_repo": vcs_repo},
            defaults=quiet,
        )
        pid = p_res.answers["id"]

    if pid in config.product_ids:
        if not quiet and not prompt_single(
            f"Product id {pid} already exists. Overwrite?", type=bool, default=True
        ):
            log.info("Exiting")
            raise typer.Exit(code=1)

    config.upsert_product_from_answers(p_res)
    config.save_products_config()

    log.info(f"Updated {pid} in {str(config.products_yaml_path)}")

    if prompt_single(f"Do you want to install {pid} now?", type=bool, default=True):
        install(pid)


@app.command()
def install(
    pid: Annotated[
        str | None,
        typer.Argument(
            help="Id of the product.",
        ),
    ] = None,
):
    """
    Fetch resources for a product that has already been added

    Uses copier, git and details from config/products.yml
    """
    _install_or_update("install", pid)


@app.command()
def update(
    pid: Annotated[
        str | None,
        typer.Argument(
            help="Id of the product.",
        ),
    ] = None,
):
    """
    Update an installed product

    Uses copier, git and details from config/products.yml
    """
    _install_or_update("update", pid)


def _install_or_update(
    method: Literal["update", "install"],
    pid: str | None,
):
    config = ProductsConfig()
    if pid is None:
        pid = prompt_single(
            f"Select the product to {method}:", type=str, choices=config.product_ids
        )

    if pid not in config.product_ids:
        log.error(
            f"{pid} not found in products. Available products are:\n"
            f"  {config.product_ids}"
        )
        raise typer.Exit(code=1)

    try:
        product = config.get_product(pid)
        if method == "install":
            product.install()
        elif method == "update":
            product.update()
        else:
            raise NotImplementedError
    except copier.ProcessExecutionError as e:
        log.error(
            f"Failed to {method} {pid}. Check your connection and authentication."
        )
        log.info(e)
        raise typer.Exit(code=1)
    except Exception as e:
        # use typer to exit and avoid stack trace (which might contain auth info).
        log.error(e)
        raise typer.Exit(code=1)
