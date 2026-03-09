# Documentation

For documentation we use [sphinx](https://www.sphinx-doc.org/en/master/) and [MyST](https://myst-parser.readthedocs.io/en/latest/).

We deploy the documentation on [readthedocs](https://app.readthedocs.org/).

## Build locally

```bash
# Install the requirements
uv sync --group docs
# Build the documentation
cd ./docs
make html
```

This will create a `docs/_build/html` folder with the documentation. You can open the `index.html` file in any browser to view the documentation locally.

## Extensions

Currently included `sphinxcontrib-typer` to render typer commands. For all options for the directive, see the [references](https://sphinxcontrib-typer.readthedocs.io/en/stable/reference/directive.html#directive-typer).
