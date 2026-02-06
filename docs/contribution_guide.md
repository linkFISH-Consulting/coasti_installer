# Contributing

## Build and upload to pypi
```bash
# create the git template bundle that we need to ship
python ./src/create_template_bundle.py

uv build

# publish on pypi test
export UV_TEST_PYPI_TOKEN="pypi-XXXXXXXXXXXXXXXXXXXXXXXX"
uv publish --index-url https://test.pypi.org/legacy/

# test it works
uv pip install --index-url https://test.pypi.org/simple/ --no-deps coasti

# final publish to pypi
export UV_PYPI_TOKEN="pypi-XXXXXXXXXXXXXXXXXXXXXXXX"
uv publish
```

## Dev Container

See [docker/README.md](docker/README.md)
