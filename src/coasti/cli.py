import typer

from .logger import log, setup_logging

app = typer.Typer()

@app.command()
def test():
    log.success("Foo")
    setup_logging(level="DEBUG")
    log.debug("Bar")
    log.success("FooBar")
    lorem()

def lorem():
    log.debug("lorem")



@app.command()
def test2():
    pass

from .init import app as init_app

app.add_typer(init_app)
