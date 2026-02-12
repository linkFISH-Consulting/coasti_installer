import os
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

yaml = YAML()

if TYPE_CHECKING:
    pass


class CoastiConfig:
    def __init__(self) -> None:
        self.products_config = None

    @property
    def base_dir(self):
        """Current projects coasti base directory."""
        coasti_root = Path(os.getenv("COASTI_BASE_DIR", Path.cwd()))
        return coasti_root


_config: CoastiConfig = None  # type: ignore


def get_config():
    global _config
    if _config is None:
        _config = CoastiConfig()
    return _config
