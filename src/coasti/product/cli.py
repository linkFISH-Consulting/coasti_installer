from __future__ import annotations

import importlib.resources
import os
from pathlib import Path
from typing import Annotated

import typer
from ruamel.yaml import YAML, CommentedMap

from ..logger import log


from .answer import get_answers_from_template

yaml = YAML()
app = typer.Typer()


@app.command()
def list():
    """List installed products"""

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
    source: Annotated[
        str,
        typer.Argument(
            help="Url of the product's git repo.",
        ),
    ],
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

    products_yaml_path, config = get_and_check_products_yaml()

    with importlib.resources.path("coasti", "") as module_path:
        answers = get_answers_from_template(
            src_path=str(module_path / "templates" / "product_install"),
            data={"source": source},
            defaults=quiet,
        )


    # add to products.yml
    products = config.get("products") or []
    product_ids = [p.get("id") for p in products if p.get("id")]
    id = answers["id"]
    if id in product_ids:
        if not quiet and not typer.prompt(
            f"Product id {id} already exists. Overwrite? (y/n)\n", type=bool
        ):
            log.info("Exiting")
            raise typer.Exit(code=1)

        product : CommentedMap = [p for p in products if p["id"] == id][0]
        product.clear()
        # to clear or not to clear?
        # dont want to loose comments but want to loose obsolete keys.
        product.update(answers)
    else:
        config["products"].append(answers)

    with products_yaml_path.open("w") as f:
        yaml.dump(config, f)

    log.info(f"Updated {id} in {str(products_yaml_path)}")



def get_and_check_products_yaml():
    """Get the path to the products yaml, and check its structure is valid."""
    coasti_root = Path(os.getenv("COASTI_BASE_DIR", Path.cwd()))
    products_yaml_path = coasti_root / "config" / "products.yml"

    if not products_yaml_path.is_file():
        log.error("Could not find config/products.yml. Have you called `coasti init`?")
        raise typer.Exit(code=1)

    config = yaml.load(products_yaml_path)
    if not isinstance(config, CommentedMap) or "products" not in config.keys():
        log.info("No products found in config/products.yml.")
        raise typer.Exit(code=0)

    return products_yaml_path, config
