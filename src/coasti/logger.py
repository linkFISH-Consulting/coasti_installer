import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

log = logging.getLogger("coasti")


def setup_logging_handler(
    verbose_level: int = 0,
) -> None:
    """
    Configure the logging handler for the cli app give its verbosity level.
    """

    console = Console(
        theme=Theme(
            {
                "logging.level.warning": "dark_orange",
            }
        )
    )

    # Map verbose_level to actual logging levels
    level_mapping = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: logging.DEBUG,
    }

    level = level_mapping.get(verbose_level, logging.WARNING)
    handler = RichHandler(console=console, markup=True)
    if verbose_level == 3:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[bold cyan]%(name)s[/] %(message)s",
            datefmt="[%X]",
            handlers=[handler],
        )
    else:
        log.handlers.clear()
        log.propagate = False

        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
        log.addHandler(handler)
        log.setLevel(level)

    log.debug(f"Set logging level to {logging.getLevelName(level)}")
