"""Shared legacy logger formatting and destinations."""
import logging
import os
import sys
import colorlog

def init_logger(name: str, level: int = logging.ERROR, dump: bool = False, silent: bool = False) -> logging.Logger:
    """Create the legacy console/file logger; stream and file errors propagate."""
    if silent:
        class empty_logger():
            def __init__(self):
                pass

            def info(self, *args, **kwargs):
                pass

            def debug(self, *args, **kwargs):
                pass

            def warning(self, *args, **kwargs):
                pass

            def error(self, *args, **kwargs):
                pass

            def critical(self, *args, **kwargs):
                pass

        return empty_logger()
    
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(level)

    # Define the output format of the handler
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    color_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        log_colors={
            'DEBUG': 'green',
            'INFO': 'cyan',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    console_handler = logging.StreamHandler(
        # Force UTF-8 encoding to resolve GBK encoding issues on Windows
        stream=open(sys.stdout.fileno(), 'w', encoding='utf-8', closefd=False)
    )
    console_handler.setLevel(level)
    console_handler.setFormatter(color_formatter)
    logger.addHandler(console_handler)

    if dump:
        if not os.path.exists("logs"):
            os.mkdir("logs")
        file_name = f"logs/{name}.log"
        file_handler = logging.FileHandler(
            file_name, 
            encoding='utf-8'  # Explicitly specify UTF-8 encoding
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

    return logger

