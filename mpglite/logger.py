from .utils import open_error

import math
import logging
import datetime

CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0
OFF = 10000

class ColoredFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    blue = "\033[36m"
    yellow = "\033[93m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    bold = "\033[1m"
    format = f"%(asctime)s.%(msecs)03d %(levelname)s: {bold}%(message)s{reset} (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

def get_logger(loglevel: int = logging.DEBUG, logfile_path: str | None = None) -> logging.Logger:    
    logger: logging.Logger = logging.getLogger(__name__)
    logger.propagate = False
    logger.setLevel(loglevel)

    # Logging to the terminal (colored)
    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    ch.setFormatter(ColoredFormatter())
    logger.addHandler(ch)


    if logfile_path is not None:
        # Logging to a file (uncolored)
        try:
            fh = logging.FileHandler(logfile_path)
            fh.setLevel(loglevel)
            fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s (%(filename)s:%(lineno)d)"))
            logger.addHandler(fh)
        except Exception as e:
            logger.critical(f"An unhandled exception occurred when adding the file handler ({logfile_path}) to the logger: {e}")

        with open_error(logfile_path, "a") as (file, e):
            if not e:
                width = 80
                file.write(f"\n{'='*width}\n{f'Server started ({datetime.now().strftime("%Y.%m.%d. %H:%M:%S")})':^80}\n{'='*width}\n")
            else:
                logger.critical(f"An unhandled exception occurred when opening the {logfile_path} file: {e}")

    return logger