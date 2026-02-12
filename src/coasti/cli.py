import sys

import typer

from coasti.logger import setup_logging

from .init import app as init_app
from .product import app as product_app

app = typer.Typer()


@app.callback()
def main(
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Enable debug logging.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        callback=lambda value: (
            typer.echo(f"Coasti version {get_version()}"),
            sys.exit(0)
        )
        if value
        else None,
        is_eager=True,
    ),
):
    """Coasti Installer - Initialize projects and install products."""
    if verbose:
        setup_logging("DEBUG")


def get_version():
    from importlib import metadata

    try:
        return metadata.version("coasti")
    except metadata.PackageNotFoundError:
        return "[not found] Use `uv sync` when developing!"


app.add_typer(init_app)  # only one command so far
app.add_typer(product_app, name="product", help="List, add or update products.")
