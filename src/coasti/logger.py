import logging
from typing import Any

import typer

# Define a new log level for success (between INFO and WARNING)
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


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


# Create a type alias for our logger with extra attribute
class EnhancedLogger(logging.Logger):
    def success(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(SUCCESS_LEVEL_NUM):
            self._log(SUCCESS_LEVEL_NUM, msg, args, **kwargs)



def setup_logging(
    level: str | int = "INFO",
    propagate: bool = False,
    name: str = "coasti_installer",
) -> EnhancedLogger:
    """
    Configure our singleton logger instance with TyperLogHandler configured.

    Can be called in functions to update the module level log instance:

    ```python
    from .logger import log, setup_logging

    def test():
        log.info("Foo")
        setup_logging(level="DEBUG")
        log.debug("Bar")
    ```
    """
    global log

    # If we have an existing logger instance, clean it up
    if log is None:
        log = EnhancedLogger(name)
    elif log.name != name:
        log.name = name

    # Remove any existing handlers to avoid duplicates
    for handler in log.handlers[:]:
        log.removeHandler(handler)
        handler.close()

    # do not (!) set level on the log instance, or we will not be able to override it.
    log.propagate = propagate

    # Add our custom handler, define level here.
    typer_handler = TyperLogHandler()
    typer_handler.setLevel(level)
    typer_handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(typer_handler)

    return log


# Singleton logger instance, with default level
log = None
log = setup_logging()
