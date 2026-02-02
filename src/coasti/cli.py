import typer

from .init import app as init_app
from .product import app as product_app

app = typer.Typer()


app.add_typer(init_app) # only one command so far
app.add_typer(product_app, name="product", help="List, add or update products")
