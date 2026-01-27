from __future__ import annotations

from pathlib import Path
from typing import Any

import ruamel.yaml
import typer
from copier import JSONSerializable, Phase, Worker, run_copy
from copier._types import RelativePath

from .init import app as init_app
from .product import app as product_app

app = typer.Typer()


app.add_typer(init_app, name="init", help="Initialize a coasti repository")
app.add_typer(product_app, name="product", help="List, add or update products")
