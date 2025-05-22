"""
Scaffold a new customer repository.

TODOs:
- init for repo creation (and setting upstream url)
- adapt gitignore so products are tracked
- install bug adds products twice to dagster workspace file
- coasti update coasti
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import random
import re
import shutil
from typing import Annotated, Any, Callable, Dict, List, Literal, Optional, TypedDict
import dotenv
import typer
import subprocess
from pprint import pformat
import logging
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from xkcdpass import xkcd_password

app = typer.Typer()
log = logging.getLogger("coasti")


WORD_LIST = xkcd_password.generate_wordlist(min_length=4, max_length=8)

# Define a new log level for success (between INFO and WARNING)
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)


logging.Logger.success = success


class TyperLogHandler(logging.Handler):
    # use logging with typer
    # https://github.com/fastapi/typer/issues/203#issuecomment-840690307

    def emit(self, record: logging.LogRecord) -> None:
        fg = None
        bg = None
        bold = False
        if record.levelno == logging.DEBUG:
            fg = typer.colors.BRIGHT_BLACK
        elif record.levelno == logging.INFO:
            fg = None
        elif record.levelno == SUCCESS_LEVEL_NUM:
            fg = typer.colors.GREEN
        elif record.levelno == logging.WARNING:
            fg = typer.colors.YELLOW
        elif record.levelno == logging.CRITICAL:
            fg = typer.colors.BRIGHT_RED
        elif record.levelno == logging.ERROR:
            fg = typer.colors.RED
            bold = True
        typer.secho(self.format(record), bg=bg, fg=fg, bold=bold)


@app.command()
def install(
    repo_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            writable=True,
            help="Where is the repository? Defaults to the current directory.",
        ),
    ] = None,
    selected_products: Annotated[
        List[str],
        typer.Option(
            "--product",
            "-p",
            help="Product to install. Can be provided multiple times. Defaults to all.",
            show_default=False,
        ),
    ] = None,
    no_commit: Annotated[
        bool,
        typer.Option(
            "--no-commit",
            help="Only clone the product repos, instead of using subtree. Skips the git commit and is not recommended for production.",
            is_eager=True,
            show_default=False,
        ),
    ] = False,
):
    if no_commit is False:
        # ask for cli confirm
        typer.confirm(
            "Are you sure you want to install the products? This will create a commit "
            + "in the git history.",
            abort=True,
        )
    _install(
        repo_path=repo_path,
        selected_products=selected_products,
        method="clone" if no_commit else "subtree",
    )


@app.command()
def update(
    repo_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            writable=True,
            help="Where is the repository? Defaults to the current directory.",
        ),
    ] = None,
    selected_products: Annotated[
        List[str],
        typer.Option(
            "--product",
            "-p",
            help="Product to install. Can be provided multiple times. Defaults to all.",
            show_default=False,
        ),
    ] = None,
):
    _install(repo_path=repo_path, selected_products=selected_products, method="update")


def _install(
    repo_path: Path = None,
    selected_products: List[str] = None,
    method: Literal["subtree", "clone", "update"] = "subtree",
):
    """
    Read the /config folder and install specified products
    """

    # Check the repository path
    if repo_path is None:
        repo_path = Path.cwd()

    # load via ruamel.yaml to keep order
    config_path = repo_path / "config" / "config.yml"
    if not config_path.is_file():
        log.error(f"Config file not found at {config_path}")
        raise typer.Exit(code=1)

    yaml = YAML()

    product_configs = yaml.load(config_path).get("products", [])
    if not product_configs:
        log.info("No products to install, check /config/config.yml")
        return

    if selected_products is None:
        selected_products = list(product_configs.keys())

    wrong_products = [p for p in selected_products if p not in product_configs.keys()]
    if wrong_products:
        log.warning(
            f"Specified product(s) not found in config: {', '.join(wrong_products)}\n"
            + f"Available choices: {', '.join(product_configs.keys())}"
        )
        raise typer.Exit(code=1)

    for name, conf in product_configs.items():
        if name not in selected_products:
            continue
        conf.update({"name": name})
        if conf.get("enabled", True):
            log.info(f"Insalling {name} via {method}")
        else:
            log.info(f"{name} is set to disabled, skipping.")
            continue
        product = Product.from_yaml_config(conf, path=Path(f"./products/{name}"))
        product.install(method=method)

    update_workspace_config_file()


@app.command()
def init(
    path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=False,
            resolve_path=True,
            writable=True,
            help="Where to place the repository? Defaults to `coasti` in the current directory.",
        ),
    ] = None,
):
    """
    Initialize a new coasti repository, by downloading the coasti template.
    """

    if path is None:
        path = Path(
            typer.prompt(
                "Where to place the repository?\n",
                default=Path.cwd() / "coasti_deployment",
            )
        )
        if not path.is_absolute():
            path = Path.cwd() / path
        log.info(f"Using {path}")

    if path.is_dir():
        log.error(f"Directory {path} already exists.")
        raise typer.Exit(code=1)

    # since the install is simply a git clone, with reset history, we use products class
    product = Product(
        name=path.name,
        url="git@github.com:linkFISH-Consulting/fe_bios_cloud.git",
        # currently only for dev puprose, so use ssh
        branch="master",  # TODO: use main
        path=path,
    )

    product.install(method="clone")

    # make new clean git repo out of this
    if (path / ".git").is_dir():
        shutil.rmtree((path / ".git").absolute())

    # create new git repo
    subprocess.run(
        ["git", "init"],
        check=True,
        cwd=path,
    )
    subprocess.run(
        ["git", "add", "."],
        check=True,
        cwd=path,
    )
    subprocess.run(
        ["git", "commit", "-m", "Coasti init"],
        check=True,
        cwd=path,
    )
    subprocess.run(
        ["git", "branch", "-M", "main"],
        check=True,
        cwd=path,
    )


@dataclass(init=False)
class Product:
    name: str
    url: str
    branch: str
    auth_token: str | None
    path: Path  # products live in a products/ folder inside another repo

    def __init__(
        self,
        name: str,
        url: str,
        path: Path,
        auth_token: str | None = None,
        branch: str = "main",
    ):
        self.name = name
        self.url = url
        self.branch = branch
        self.auth_token = auth_token
        self.path = path

    @classmethod
    def from_yaml_config(cls, config: dict, path: Path = None):
        return cls(
            name=config["name"],
            url=config["url"],
            branch=config.get("branch", "main"),
            auth_token=config.get("auth_token"),
            path=path or Path.cwd(),
        )

    @property
    def install_method(self) -> Literal["subtree", "clone"]:
        """
        How was this product installed? Checks for the presence of a .git folder.
        """
        if (Path(f"products/{self.name}/.git")).is_dir():
            return "clone"
        else:
            return "subtree"

    def install(self, method=Literal["subtree", "clone", "update"]):
        """
        Install or update the product.

        Parameters
        ----------
        method : str
            Method to install the product. Can be either "subtree" or "clone".
            Defaults to "subtree" which will create a commit in the git history and
            is recommended for production.
            "clone" will only clone the repo, and not touch the version control
            of the parent repo.
            "update" will detect the used install method (is a .git folder present?)
            and update either via subtree or git pull.
        path_prefix : str
            Prefix for the path where the product will be installed. Defaults to "products/".
        """

        is_update = False
        if method == "update":
            is_update = True
            method = self.install_method
            log.debug(f"Updating {self.name} (as installed via '{method}')")
            if method == "subtree":
                # ask for cli confirm
                if not typer.confirm(
                    f"{self.name} was installed via subtree. "
                    + "Updating will create a commit.\nContinue?",
                ):
                    log.info("Skipping.")
                    return

        # default for production
        if method == "subtree":
            # check git is clean
            if subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True
            ).stdout:
                log.error(
                    "Cannot install products with uncomitted changes in your repo!"
                )
                raise typer.Exit(code=1)

            try:
                cmd = [
                    "git",
                    "subtree",
                    "add" if not is_update else "pull",
                    "--prefix",
                    f"{self.path}",
                    self.url_authenticated,
                    self.branch,
                    "--squash",
                    "--message",
                    f"Automatic install of {self.name} (branch {self.branch})\n{self.url}"
                    if not is_update
                    else f"Automatic update of {self.name} (branch {self.branch})\n{self.url}",
                ]
                subprocess.run(
                    cmd,
                    check=True,  # raise if not successfull
                )
            except subprocess.CalledProcessError:
                log.error(
                    f"Failed to clone {self.name} from {self.url} on branch {self.branch}"
                )
                raise typer.Exit(code=1)
        elif method == "clone":
            log.info(f"Installing {self.name} via git clone.")
            try:
                if is_update:
                    cmd = [
                        "git",
                        "-C",
                        f"{self.path}",
                        "pull",
                    ]
                else:
                    cmd = [
                        "git",
                        "clone",
                        "--branch",
                        self.branch,
                        self.url_authenticated,
                        f"{self.path}",
                    ]
                subprocess.run(
                    cmd,
                    check=True,  # raise if not successful
                )
            except subprocess.CalledProcessError:
                log.error(
                    f"Failed to clone {self.name} from {self.url} on branch {self.branch}"
                )
                raise typer.Exit(code=1)

    @property
    def url_authenticated(self):
        if self.auth_token is None or self.url.startswith("git@"):
            log.debug(f"Using ssh to get {self.url}")
            return self.url

        # https://forum.gitlab.com/t/how-to-git-clone-via-https-with-personal-access-token-in-private-project/43418/4

        repo = self.url.lstrip("https://").lstrip("http://")
        return f"https://oauth2:{self.auth_token}@{repo}"

    @property
    def version(self):
        # this is our code version. Read git?
        # or .version file in the installed code.
        pass

    @property
    def vorsystem_version(self):
        # Note: this is inside the container!
        # helper to get the version needed before ingestion
        # 1. ingestions tool gets version
        # 2. coasti checks compatibilities, and possibly haults
        # 3. ingestion runs, (depending on version, but checks version internally again)
        pass

    @property
    def is_ingestion_tool_working(self):
        # inside the container!
        pass

    def __str__(self):
        return f"{self.name} ({self.url})"

    def __repr__(self):
        return str(self)


# ---------------------------------------------------------------------------- #
#                                Config Parsing                                #
# ---------------------------------------------------------------------------- #


@app.command()
def update_workspace_config_file(workspace_file: Path = None):
    """Update the workspace config file from currently installed products."""

    if workspace_file is None:
        workspace_file = Path.cwd() / "config" / "dagster" / "workspace.yml"

    log.info(f"Updating dagster workspace at {workspace_file}")

    # TODO: Check that this is actually a coasti repo.
    repo_path = workspace_file.parent.parent.parent

    if not workspace_file.is_file():
        log.info(f"No Dagster workspace found at {workspace_file}, creating new one.")
        workspace_file.parent.mkdir(parents=True, exist_ok=True)
        workspace_file.write_text(
            "# This file was automatically generated by coasti "
            + "and might change in the future.\n\n"
            + "\nload_from:\n"
        )

    # keep track of all products found on disk via the working_directory
    installed_products = dict()
    for p in list(repo_path.glob("products/*/dagster_*")):
        wdir = f"./{p.relative_to(repo_path)}".rstrip("/")
        product_yaml = {
            "python_module": {
                "location_name": p.stem.replace("dagster_", ""),
                "module_name": f"{p.stem}.definitions",
                # not sure why the .definitions is needed as mod name, but it wont run
                # otherwise. Questions is what about schedulers etc?
                # Try again import * in the __init__
                "working_directory": wdir,
                # we can avoid the working directory if we pip install the package.
                # relative paths work, but start from where the `dagster dev` is executed,
                # not the location of the workspace file!
            }
        }
        installed_products[wdir] = product_yaml
        log.debug(f"Found installed product at: {wdir}")

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    with open(workspace_file, "r") as f:
        data: CommentedMap = yaml.load(f)

    if "load_from" not in data.keys() or data["load_from"] is None:
        # this happens when we create the file ourself
        data["load_from"] = []

    # warn about configured but not installed products
    configured_products = []
    for p in data["load_from"]:
        wdir = p.get("python_module", {}).get("working_directory").rstrip("/")
        p_name = p.get("python_module", {}).get("location_name")
        configured_products.append(wdir)
        if wdir not in installed_products.keys():
            log.warning(
                f"Found '{p_name}' in workspace file, but not on disk. Expected at {wdir}\n"
                + "Consider removing it from your ./config/dagster/workspace.yml"
            )

    # upsert all installed products to the workspace file
    for wdir, product_yaml in installed_products.items():
        if wdir in configured_products:
            log.debug(f"Updating product: {wdir}")
            idx = configured_products.index(wdir)
            if "python_module" not in data["load_from"][idx].keys():
                log.error(
                    "No python_module key found in workspace file."
                    + f"This should not happen. Try manually removing this product. {wdir}"
                )
                continue

            new = product_yaml["python_module"]
            old = data["load_from"][idx]["python_module"]

            # keep customized name, but the rest needs to be updated
            old["location_name"] = old.get("location_name", new["location_name"])
            for k, v in new.items():
                if k != "location_name":
                    if old[k] != v:
                        log.info(f"Changed `{k}` {old[k]} -> {v}")
                    old[k] = v
        else:
            log.debug(f"Adding product: {wdir}")
            data["load_from"].append(product_yaml)

    with open(workspace_file, "w") as f:
        yaml.dump(data, f)


@app.command()
def parse(
    repo_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            readable=True,
            exists=True,
            help="Where is the repository? Defaults to the current directory.",
        ),
    ] = None,
    generate_config: Annotated[
        bool,
        typer.Option(
            "--generate-config",
            help="Generate a config.yml file from the sample, before translating to .env file",
            is_eager=True,
            show_default=False,
        ),
    ] = True,
):
    """
    Parses the config.yml (in /config) to a .env file.

    Can deal with strings, ints, floats, bools and lists (parsed to json).\n
    So far, only updates .env if it already exists.\n
    Does not clear unused values.\n\n
    """
    # Check the repository path
    if repo_path is None:
        repo_path = Path.cwd()

    if generate_config:
        log.info("Generating config.yml from config.sample.yml.")
        create_config_from_sample(repo_path)

    config_file = repo_path / "config" / "config.yml"
    if not config_file.is_file():
        log.error(
            f"No config.yml found in {repo_path}/config. "
            + "Have a look a the config.sample.yml!"
        )
        raise typer.Exit(code=1)

    log.debug(f"Loading {config_file}")
    yaml = YAML(typ="safe")
    with open(config_file, "r") as f:
        loaded: CommentedMap | None = yaml.load(f)
        if loaded is None:
            log.error(f"{config_file} is empty")
            raise typer.Exit(code=1)

    # ------------------------------- Rearrange ------------------------------ #

    parsed = {}
    # copy everything in the general section, prefix with coasti
    parsed["coasti"] = loaded.get("coasti", {})

    # copy everything in the products section, prefix with product name
    products = loaded.get("products", [])
    for k, v in products.items():
        parsed[k] = v

    # copy everything else - but this is not encouraged
    for k, v in loaded.items():
        if k in ["coasti", "products"]:
            continue
        parsed[k] = v

    # --------------------------- save to .env file -------------------------- #

    env_data = {}

    def flatten(data, parent_key=""):
        for k, v in data.items():
            # we have the convention to use lower_case names and split folders with __.
            # iterate all substructures and flatten them
            new_key = f"{parent_key}__{k}" if parent_key else k
            if isinstance(v, dict):
                flatten(v, new_key)
            else:
                # we want upper casing for env variables
                env_data[new_key.upper()] = v

    flatten(parsed)

    # log.debug(f"env_data:\n{pformat(env_data, width=180)}")

    output_path = repo_path / "config" / ".env"
    for k, v in env_data.items():
        if isinstance(v, (bool, int)):
            v = str(int(v))
        elif isinstance(v, float):
            v = str(v)
        elif isinstance(v, (list, tuple)):
            v = json.dumps(v)
        # set_key creates the file if it does not exist
        dotenv.set_key(output_path, k, v, quote_mode="auto")

    log.success(f"Updated {output_path}\n(We do not remove old values!)")
    log.info(
        "To load environment variables and export from cli, "
        + "use `set -a; source .env; set +a`"
    )


@app.command()
def create_config_from_sample(
    repo_path: Path = None,
):
    """
    Until more products are ready, we collect all config options as placeholders
    in coasti config.sample.

    This function creates a config.yml file from the sample, and populates placedholders.
    """

    repo_path = repo_path or Path.cwd()
    sample_path = repo_path / "config" / "config.sample.yml"
    config_path = repo_path / "config" / "config.yml"

    if config_path.is_file():
        log.error("Cannot auto-generate config.yml, file already exists.")
        overwrite = typer.confirm("Overwrite?", default=False)
        if not overwrite:
            log.info("Keeping config as is")
            return
        else:
            log.info("Overwriting existing config...")

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    with open(sample_path, "r") as f:
        loaded: CommentedMap | None = yaml.load(f)
        if loaded is None:
            log.error(f"{sample_path} is empty")
            raise typer.Exit(code=1)

    # -------------------------- Replace Placeholder ------------------------- #
    # TODO: what about lists? And what about placeholders in keys?

    def _iterate_all(data: dict | list, func: Callable[[str, Any], Any]):
        for key, value in data.items():
            # log.debug(f"key: {key}, value: {value}")
            if isinstance(value, dict):
                _iterate_all(value, func)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _iterate_all(item, func)
                    else:
                        log.error(f"Unexpected item in list: {item}")
            else:
                k_new, v_new = func(key, value)
                data[k_new] = v_new
                # dont log passwords :P
                # if k_new != key or v_new != value:
                #     log.debug(f"Replaced {key}: {value} with {k_new}: {v_new}")

    # replace environment variable placeholders: "{{ env_var('DBT_USER') }}"
    def replace_env_var(key: str, value: Any):
        if not isinstance(value, str):
            return key, value

        # inside env_var(), match everything except ) and whitespace
        pattern = r"\{\{\s*env_var\(\s*([^)\s]+)\s*\)\s*\}\}"
        match = re.fullmatch(pattern, value.strip())
        env_var = match.group(1).lstrip("'").rstrip("'") if match else None
        if env_var is None:
            return key, value
        elif env_var in os.environ:
            return key, os.environ[env_var]
        else:
            log.error(f"Environment variable {env_var} not set (needed for {key}).")
            return key, value

    _iterate_all(loaded, replace_env_var)

    # Generate Passwords
    def replace_passwords(key: str, value: Any):
        if not isinstance(value, str):
            return key, value

        pattern = r"\{\{\s*generate_password\s*\}\}"
        match = re.fullmatch(pattern, value.strip())
        if match is None:
            return key, value
        pw = xkcd_password.generate_xkcdpassword(
            WORD_LIST,
            numwords=5,
            delimiter="_",
            case="first",
        )
        # add a random number, 1-4 digits, at random position
        num_digits = random.randint(1, 4)
        random_num = random.randint(1, 10**num_digits - 1)

        words = pw.split("_")
        words.insert(random.randint(0, len(words)), str(random_num))
        pw = "_".join(words)

        return key, pw

    _iterate_all(loaded, replace_passwords)

    # Generate User logins
    def replace_users(key: str, value: Any):
        if not isinstance(value, str):
            return key, value

        pattern = r"\{\{\s*generate_user\s*\}\}"
        match = re.fullmatch(pattern, value.strip())
        if match is None:
            return key, value
        pw = xkcd_password.generate_xkcdpassword(
            WORD_LIST,
            numwords=2,
            delimiter="-",
            case="lower",
        )
        return key, pw

    _iterate_all(loaded, replace_users)

    # ----------------------------- Write to disk ---------------------------- #

    with open(config_path, "w") as f:
        yaml.dump(loaded, f)
        log.success(f"Created config file from {sample_path} at {config_path}")


def parse_with_product_nesting(
    repo_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            readable=True,
            exists=True,
            help="Where is the repository? Defaults to the current directory.",
        ),
    ] = None,
):
    """
    Just for reference, one idea is to have config defaults in each products'
    folder that serve as a starting point. Needs to be updated!

    Parses all yaml files in products config folders to the global coasti .env file.

    Little helper to parse yaml files to a .env file.

    For now only writes one .env file.

    Can deal with strings, ints, floats, bools and lists (parsed to json).\n
    So far, only updates .env if it already exists.\n
    Does not clear unused values.\n\n
    """
    # Check the repository path
    if repo_path is None:
        repo_path = Path.cwd()

    # get all files in all subfolders that end in .yml or .yml, case insensitive
    base_files = list(repo_path.glob("config/*.yml"))
    if not base_files:
        log.error(f"No yaml files found in {repo_path}")
        raise typer.Exit(code=1)

    # config files off products are placed in the merged config file under
    # the product_name / yaml_file_name key
    product_files = list(repo_path.glob("products/*/config/*.yml"))
    # exclude some, such as dbt profiles
    product_files = [f for f in product_files if f.name not in ["profiles.yml"]]

    # we want to overwrite some_config.default.yml with the custom files
    default_files = [
        f for f in base_files + product_files if f.stem.lower().endswith(".default")
    ]
    custom_files = [
        f for f in base_files + product_files if not f.stem.lower().endswith(".default")
    ]

    # load default files first, then custom
    def update(data, file_list: List[Path]):
        for file in file_list:
            log.debug(f"Loading {file}")
            with open(file, "r") as f:
                loaded = yaml.safe_load(f)
                if loaded is None:
                    log.info(f"Skipped {file} because it is empty")
                    continue
                # products are placed nested
                if file in product_files:
                    loaded = {file.parent.parent.name: {file.stem: loaded}}
                data = deep_update(data, loaded)

    data = {}
    update(data, default_files)
    update(data, custom_files)

    # only consider products and tools listed at the top section
    # this is only for readability and convenience in the config files,
    # to quickly disable some parts
    products = data.get("products_to_load", [])
    tools = data.get("tools_to_load", [])
    valid_data = {}
    for k, v in data.items():
        if k in products or k in tools or not isinstance(v, dict):
            valid_data[k] = v
        else:
            log.info(f"Dropping section {k} because not in products or tools")
    data = valid_data

    output_path = repo_path / "config" / "env.yml"
    with open(output_path, "w") as f:
        yaml.dump(data, f)
    log.success(f"Wrote env.yml file to {output_path}")
    # typer.secho(f"data:\n{pformat(data, width=180)}", fg=typer.colors.BLUE)

    # --------------------------- save to .env file -------------------------- #

    # we have the convention to use lower_case names and split folders with __.
    # iterate all substructures and flatten them
    env_data = {}

    def flatten(data, parent_key=""):
        for k, v in data.items():
            new_key = f"{parent_key}__{k}" if parent_key else k
            if isinstance(v, dict):
                flatten(v, new_key)
            else:
                # we want upper casing for env variables
                env_data[new_key.upper()] = v

    flatten(data)

    # typer.secho(f"env_data:\n{pformat(env_data, width=180)}", fg=typer.colors.BLUE)

    output_path = repo_path / "config" / ".env"
    # TODO: check for existing file
    for k, v in env_data.items():
        if isinstance(v, (bool, int)):
            v = str(int(v))
        elif isinstance(v, float):
            v = str(v)
        elif isinstance(v, (list, tuple)):
            v = json.dumps(v)
        dotenv.set_key(output_path, k, v, quote_mode="auto")

    log.success(f"Wrote .env file to {output_path}")
    log.info(
        "To load environment variables and export from cli, "
        + "use `set -a; source .env; set +a`"
    )


def deep_update(source: dict, other: dict):
    for key, value in other.items():
        if key in source and isinstance(source[key], dict) and isinstance(value, dict):
            source[key] = deep_update(source[key], value)
        else:
            source[key] = value
    return source


# ----------------------------------- Main ----------------------------------- #


def main():
    typer_handler = TyperLogHandler()
    logging.basicConfig(
        level=logging.DEBUG, handlers=(typer_handler,), format="%(message)s"
    )
    app()


if __name__ == "__main__":
    main()
