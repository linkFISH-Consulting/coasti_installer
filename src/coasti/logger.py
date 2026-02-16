from __future__ import annotations

import logging

from rich.console import Console, ConsoleRenderable
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.text import Text
from rich.theme import Theme
from rich.traceback import install

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
                "message.debug": "dim",
                "message.warning": "yellow",
                "message.critical": "red",
                "message.error": "bold red",
            }
            if verbose_level < 2
            else {}
        )
    )

    if verbose_level < 2:
        install(show_locals=False, extra_lines=0)

    # Map verbose_level to actual logging levels
    level_mapping = {
        0: logging.INFO,  # info with minimal formatting
        1: logging.DEBUG,  # debug with minimal formatting
        2: logging.DEBUG,  # debug with extended formatting and traces
        3: logging.DEBUG,  # debug incl. other modules with extended formatting
    }

    level = level_mapping.get(verbose_level, logging.INFO)
    handler = ColoredHandler(
        console=console,
        markup=False,
        tracebacks_max_frames=1,
        tracebacks_show_locals=(verbose_level >= 2),
        show_path=(verbose_level >= 1),
        show_level=(verbose_level >= 2),
        show_time=(verbose_level >= 2),
        highlighter=NullHighlighter(),  # otherwise we get bold numbers etc
    )
    if verbose_level == 3:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(name)s] %(message)s",
            datefmt="[%X]",
            handlers=[handler],
        )
    else:
        log.handlers.clear()
        log.propagate = False

        handler.setFormatter(
            logging.Formatter(
                "%(message)s",
                datefmt="[%X]",
            ),
        )
        log.addHandler(handler)
        log.setLevel(level)

    log.debug(f"Set logging level to {logging.getLevelName(level)}")


class ColoredHandler(RichHandler):
    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        """Render message text in to Text, with style depending on log level.

        Args:
            record (LogRecord): logging Record.
            message (str): String containing log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """

        message_text = super().render_message(record, message)

        if isinstance(message_text, Text):
            message_text.stylize(style=f"message.{record.levelname.lower()}")

        return message_text
