from __future__ import annotations

import json
from typing import Annotated, Any, Literal

import copier
import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml import YAML

from coasti.logger import log
from coasti.prompt import (
    prompt_like_copier,
    prompt_single,
)

from .product import Product, ProductsYamlIO
from .questions import PRODUCT_QUESTIONS

yaml = YAML()
app = typer.Typer()


@app.command()
def list():
    """List installed products"""

    table = Table(title="Installed Products")
    table.add_column("Product", style="cyan", no_wrap=True)
    table.add_column("Property", style="magenta", justify="right")
    table.add_column("Value", style="green")

    yaml_io = ProductsYamlIO()
    for pid in yaml_io.product_ids:
        p = yaml_io.get_enry(pid)
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
    ctx: typer.Context,
    vcs_repo: Annotated[
        str | None,
        typer.Argument(
            help="Url of the product's git repo.",
        ),
    ] = None,
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

    quiet : bool = ctx.obj.get("quiet", False)

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

    # check if you can access this
    # if not (or always?) ask for credentials

    with ProductsYamlIO.edit() as pio:
        p_res = prompt_like_copier(
            questions=PRODUCT_QUESTIONS,
            data=copier_data,
        )
        product = Product(yaml_io=pio, data=p_res)

        if product.id in pio.product_ids:
            if quiet or not prompt_single(
                f"Product id {product.id} already exists. Overwrite?",
                type=bool,
                default=True,
            ):
                log.info("Not overwriting product, exciting.")
                raise typer.Exit(code=1)

        product.write()

    if not quiet and prompt_single(
        f"Do you want to install {product.id} now?", type=bool, default=True
    ):
        install(product.id)


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
    pid = _product_id_from_yaml_or_prompt(pid)

    config = ProductsYamlIO()
    try:
        product = config.get_product(pid)
        product.install()
    except copier.ProcessExecutionError as e:
        log.error(f"Failed to install {pid}. Check your connection and authentication.")
        log.info(e)
        raise typer.Exit(code=1)
    except Exception as e:
        # use typer to exit and avoid stack trace (which might contain auth info).
        log.error(e)
        raise typer.Exit(code=1)


@app.command()
def update(
    pid: Annotated[
        str | None,
        typer.Argument(
            help="Id of the product.",
        ),
    ] = None,
    vcs_ref: Annotated[
        str | None,
        typer.Option(
            "--vcs-ref", help="Version control reference, e.g. git branch or commit"
        ),
    ] = None,
):
    """
    Update an installed product

    Uses copier, git and details from config/products.yml
    """
    pid = _product_id_from_yaml_or_prompt(pid)

    config = ProductsYamlIO()
    try:
        product = config.get_product(pid)

        if vcs_ref is None:
            vcs_ref = product.data["vcs_ref"]

        product.update(vcs_ref)
    except copier.ProcessExecutionError as e:
        log.error(f"Failed to update {pid}. Check your connection and authentication.")
        log.info(e)
        raise typer.Exit(code=1)
    except Exception as e:
        # use typer to exit and avoid stack trace (which might contain auth info).
        log.error(e)
        raise typer.Exit(code=1)


def _product_id_from_yaml_or_prompt(
    pid: str | None,
):
    config = ProductsYamlIO()
    if pid is None:
        pid = prompt_single(
            "Select the product to use:", type=str, choices=config.product_ids
        )

    if pid not in config.product_ids:
        log.error(
            f"{pid} not found in products. Available products are:\n"
            f"  {config.product_ids}"
        )
        raise typer.Exit(code=1)

    return pid
