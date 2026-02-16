from __future__ import annotations

import json
from importlib import resources
from typing import Annotated, Any, Literal

import copier
import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml import YAML

from coasti.logger import log
from coasti.prompt import prompt_like_copier_from_template, prompt_single

from .product import ProductsConfig

yaml = YAML()
app = typer.Typer()


@app.command()
def list():
    """List installed products"""

    table = Table(title="Installed Products")
    table.add_column("Product", style="cyan", no_wrap=True)
    table.add_column("Property", style="magenta", justify="right")
    table.add_column("Value", style="green")

    config = ProductsConfig()
    for p in config.products:
        for idx, (key, value) in enumerate(p.items()):
            table.add_row(
                p["id"] if idx == 0 else "",
                key,
                str(value),
                end_section=(idx == len(p) - 1),
            )

    console = Console()
    console.print(table)


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
    data: Annotated[
        str | None,
        typer.Option(
            "--data",
            help="Avoid prompts by providing answers as a JSON object like: "
            ' \'{"vcs_ref": "my_dev_branch"}\'',
        ),
    ] = None,
):
    """Add a product to coasti"""

    # Parse skip-prompt answers and internal variables for answers_file
    extra_data: dict = {}
    if data is not None:
        try:
            extra_data = json.loads(data)
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON in --data: {e}")
            log.error(f"Input was: {data!r}")
            raise typer.Exit(code=1)

    copier_data: dict[str, Any] = {}
    copier_data.update(extra_data)

    vcs_repo = (
        vcs_repo
        or extra_data.get("vcs_repo")
        or prompt_single("Url of the product's git repo:", type=str)
    )
    copier_data.update({"vcs_repo": vcs_repo})

    config = ProductsConfig()

    with resources.path("coasti", "") as module_path:
        p_res = prompt_like_copier_from_template(
            src_path=str(module_path / "product" / "questions"),
            data=copier_data,
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

    if not quiet and prompt_single(
        f"Do you want to install {pid} now?", type=bool, default=True
    ):
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
