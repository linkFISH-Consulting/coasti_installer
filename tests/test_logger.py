import logging
from unittest.mock import patch

import pytest

from coasti.logger import log, setup_logging_handler


@pytest.mark.parametrize(
    "verbose_level,expected_level",
    [
        (0, logging.INFO),
        (1, logging.DEBUG),
        (2, logging.DEBUG),
        (3, logging.DEBUG),
        (4, logging.INFO),  # Default for out-of-range
        (-1, logging.INFO),  # Default for negative
    ],
)
def test_setup_logging_handler_level_mapping(verbose_level, expected_level):
    """Test that verbose_level maps to correct logging levels."""
    with (
        patch("logging.basicConfig") as mock_basicConfig,  # noqa: N806
        patch.object(log, "handlers", []),
        patch.object(log, "addHandler"),
        patch.object(log, "setLevel") as mock_setLevel,  # noqa: N806
    ):
        setup_logging_handler(verbose_level)

        if verbose_level == 3:
            # For verbose_level=3, basicConfig should be called with DEBUG level
            mock_basicConfig.assert_called_once()
            call_kwargs = mock_basicConfig.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG
            mock_setLevel.assert_not_called()
        else:
            # For other levels, setLevel should be called on the log object
            mock_basicConfig.assert_not_called()
            mock_setLevel.assert_called_once_with(expected_level)
