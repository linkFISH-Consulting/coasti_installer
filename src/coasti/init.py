# ------------------------------------------------------------------------------ #
# @Author:        F. Paul Spitzner
# @Created:       2026-01-26 13:41:54
# @Last Modified: 2026-01-29 09:40:52
# ------------------------------------------------------------------------------ #

"""
`coasti init`

Initialize project structure.
"""

import importlib.resources
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
        typer.Argument(
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            writable=True,
            help="Where to place coasti?",
        ),
    ] = None,
    trust: Annotated[
        bool,
        typer.Option(
            "--trust",
            help="Passed to copier, so that potentially unsafe features are allowed.",
        ),
    ] = False,
    recopy: Annotated[
        bool,
        typer.Option(
            "--recopy",
            help="Use copiers' recopy option, ignores your git changes.",
        ),
    ] = False,
):
    """Initialize a coasti workspace"""
    if coasti_dir is None:
        coasti_dir = cast(
            Path,
            typer.prompt(
                "Where to place coasti?\n",
                type=Path,
                default=Path.cwd() / "coasti",
            ),
        )

    if (coasti_dir / "config" / ".coasti-setup-answers.yml").exists() and not recopy:
        copier.run_update(
            dst_path=coasti_dir,
            answers_file="./config/.coasti-setup-answers.yml",
            unsafe=trust,
        )
    else:
        # get our coasti installers module location. templates are included.
        with importlib.resources.path("coasti", "") as module_path:
            copier.run_copy(
                src_path=str(module_path / "templates" / "coasti"),
                dst_path=coasti_dir,
                answers_file="./config/.coasti-setup-answers.yml",
                unsafe=trust,
            )
