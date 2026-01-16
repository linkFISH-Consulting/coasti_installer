# Specification for the coasti installer and folder structure



## Getting started and CLI

```bash
pip install coasti

# interactive, creates at least customer repo from template
coasti init

# install coasti products
coasti product list # show whats installed etc
coasti product add  # should this install, or only add to config? [wrapper for more subcommands]
coasti product update
coasti product configure

# install stack components ('tools') like superset or sling
coasti tool add
```

## Folder structure

### Root config

- no product specific configs, except how to install them, and which ones are enabled.

```bash
├── coasti/
    ├── config/
        ├── secrets/
            ├── secret_one  # files, holding one secret each
            ├── secret_two
        ├── products.yml    # which to enable, how to get it
        ├── tools.yml       # which to enable, how to get it
        ├── [product]/      # symlink
    ├── products/
    ├── tools/              # shared between products. TBD: or in products, weil eh images.
    ├── data/
        ├── [product]/      # symlink
    ├── logs/               # log on a per-product level as much as possible, and link.
        ├── [product]/      # symlink
        ├── [tool]/         # symlink
    ├── run_all.sh          # TBD, aim is: `coasti product run` and `coasti run` (for all products)
                            # to that end, think about how to have product-level full stack
```

### Requirements for products

```bash
├── [product]/
    ├── config/
        ├── secrets/
            ├── secret_one  # files, holding one secret each
            ├── secret_two
    ├── logs/               # log on a per-product level as much as possible, and link.
    ├── run_product.sh      # TBD
    ├── data/
    ├── tools/              # TBD
    ├── info.yml            # or coasti.yml information about this product. required, think pyproject.toml
```

### Gotchas, Future Proofing
- all our self-designed yaml should have a `version` to reflect the coasti spec, just so our cli tool and conventions can go through changes.
