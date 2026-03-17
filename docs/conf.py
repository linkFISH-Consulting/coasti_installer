# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = "coasti"
copyright = "2026, LinkFISH Consulting"
author = "LinkFISH Consulting"

master_doc = "index"
language = "en"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    # "myst_parser",
    "myst_nb",
    "sphinxcontrib.typer",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "*.ipynb_checkpoints"]

nb_execution_mode = "off"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_logo = "_static/logo.svg"
html_css_files = ["custom.css"]

html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        "sidebar/scroll-end.html",
    ]
}

html_context = {
    "default_mode": "light",  # "dark"
}

html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#115572",
        "color-brand-content": "#0C4255",
        "color-brand-visited": "#3381AC",
    },
    "dark_css_variables": {
        "color-brand-primary": "#F2FF41",
        "color-brand-content": "#6EC6EF",
        "color-brand-visited": "#115572",
        # "color-background-primary": "#0C4255",
        # "color-background-secondary": "#115572"
    },
}
