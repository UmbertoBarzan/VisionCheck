import logging
import os
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

class ColorFormatter(logging.Formatter):
    """Formatter that adds color to log messages."""
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m',# Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[95m' # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        level = record.levelname
        msg = super().format(record)
        color = self.COLORS.get(level, self.RESET)
        return f"{color}[{level}] {msg}{self.RESET}"
    
def get_logger(name='visioncheck', level=logging.DEBUG):
    '''Initialize and return a logger with file and console handlers.'''
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger  # Return existing logger if already configured
    
    console_handler = logging.StreamHandler()
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(ColorFormatter(console_format._fmt))
    logger.addHandler(console_handler)
    
    log_file = LOGS_DIR / f"{name}.log"
    file_handler = logging.FileHandler(log_file)
    file_format = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger
