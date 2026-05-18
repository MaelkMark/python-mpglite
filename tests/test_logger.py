import logging
import os
from unittest.mock import patch
from mpglite.logger import Loglevel, ColoredFormatter, get_logger


def test_loglevel_order():
    """Verify that Loglevel enum values match standard logging levels and custom OFF level."""
    assert (
        Loglevel.DEBUG.value
        < Loglevel.INFO.value
        < Loglevel.WARNING.value
        < Loglevel.ERROR.value
        < Loglevel.CRITICAL.value
        < Loglevel.OFF.value
    ), "Incorrect log level order"


def test_loglevel_aliases():
    """Verify aliases for log levels."""
    assert Loglevel.FATAL == Loglevel.CRITICAL
    assert Loglevel.WARN == Loglevel.WARNING


def test_colored_formatter_logic():
    """Verify that ColoredFormatter applies ANSI codes and formatting correctly."""
    formatter = ColoredFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Hello World",
        args=None,
        exc_info=None,
    )
    formatted = formatter.format(record)

    # Check color/format codes
    assert ColoredFormatter.blue in formatted, "Missing blue color code"
    assert ColoredFormatter.bold in formatted, "Missing bold code"
    assert ColoredFormatter.reset in formatted, "Missing reset code"

    # Check content fields
    assert "INFO" in formatted, "Missing log level"
    assert "Hello World" in formatted, "Missing log message"
    assert "test_file.py:42" in formatted, "Missing log location"


def test_get_logger_setup():
    """Verify get_logger correctly configures a logger with standard settings."""
    # Clear handlers first to ensure a clean state for the singleton logger instance
    test_logger = logging.getLogger("mpglite.logger")
    test_logger.handlers = []

    logger = get_logger(Loglevel.DEBUG)

    assert logger.level == logging.DEBUG, "Incorrect log level"
    assert logger.propagate is False, "Logger should not propagate"

    # By default, it should have at least one StreamHandler with ColoredFormatter
    assert len(logger.handlers) >= 1
    stream_handlers = [
        h for h in logger.handlers if isinstance(h, logging.StreamHandler)
    ]
    assert len(stream_handlers) > 0, "No StreamHandler found"
    assert isinstance(
        stream_handlers[0].formatter, ColoredFormatter
    ), "StreamHandler formatter is not ColoredFormatter"


def test_get_logger_file_output(tmp_path):
    """Verify get_logger adds a FileHandler and writes the starting header."""
    log_file = tmp_path / "app.log"
    log_file_str = str(log_file)

    test_logger = logging.getLogger("mpglite.logger")
    test_logger.handlers = []

    get_logger(Loglevel.INFO, logfile_path=log_file_str)

    # Check if FileHandler was added
    file_handlers = [
        h for h in test_logger.handlers if isinstance(h, logging.FileHandler)
    ]
    assert len(file_handlers) == 1, "No FileHandler found"
    assert os.path.abspath(file_handlers[0].baseFilename) == os.path.abspath(
        log_file_str
    ), "Incorrect log file path"


@patch("mpglite.logger.open_error")
def test_get_logger_open_file_error(mock_open_error):
    """Verify error handling when header writing fails via open_error."""
    mock_open_error.return_value.__enter__.return_value = (
        None,
        IOError("Permission denied"),
    )

    test_logger = logging.getLogger("mpglite.logger")
    test_logger.handlers = []

    with patch.object(test_logger, "critical") as mock_critical:
        get_logger(Loglevel.INFO, logfile_path="bogus.log")
        mock_critical.assert_any_call(
            "An unhandled exception occurred when opening the bogus.log file: Permission denied"
        )
