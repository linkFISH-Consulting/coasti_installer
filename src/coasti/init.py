# ------------------------------------------------------------------------------ #
# @Author:        F. Paul Spitzner
# @Created:       2026-01-26 13:41:54
# @Last Modified: 2026-01-26 16:56:59
# ------------------------------------------------------------------------------ #

"""
`coasti init`

Initialize project structure.
"""

import os
from pathlib import Path
from typing import Annotated, cast

import copier
import typer

from .logger import log

app = typer.Typer()


@app.command()
def init(
    coasti_dir: Annotated[
        Path | None,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            writable=True,
            help="Where to place coasti?",
        ),
    ] = None,
):
    if coasti_dir is None:
        coasti_dir = cast(
            Path,
            typer.prompt(
                "Where to place coasti?\n",
                type=Path,
                default=Path.cwd() / "coasti",
            ),
        )

    copier.run_copy("./template", coasti_dir)
