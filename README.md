# Coasti installer

## Get started
```bash
pip install coasti

mkdir new-repo
cd new-repo

# create a fresh local git repo
git init
git add .
git commit -m "Initial commit from coasti template"

# optional: link to an online repo
git remote add origin https://github.com/yourusername/new-repo.git
git push -u origin main

# generic help:
coasti --help

# -> copy/edit config.example.yml to config.yml

# translate config.yml to .env
coasti parse

# install products
coasti install

# create the dagster workspace
coasti update-workspace-config-file
```


## Upload to pypi
```bash
python3 -m pip install --upgrade build twine

# build the package
python3 -m build
twine check dist/*

# upload, needs api token
twine upload dist/*
```
