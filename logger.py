"""
Wrap the logging setup for the application.
Author: Ronen Ness.
Created: 2025.
"""
import config
import logging
from logging.handlers import RotatingFileHandler
import sys

# Create a rotating log handler
_file_handler = RotatingFileHandler(
    filename=config.LOGS.get("log_file", "app.log"),
    maxBytes=config.LOGS.get("max_bytes", 1024*10),
    backupCount=config.LOGS.get("backup_count", 3)
)

# define log format
formatter = logging.Formatter(config.LOGS.get('format', "%(name)s %(asctime)s - %(levelname)s - %(message)s"))

# Create log to console handler
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(formatter)

# Set log format and level
_file_handler.setFormatter(formatter)

def get_logger(name: str = __name__) -> logging.Logger:
    """
    Returns a logger instance for the current module.
    
    Args:
        name (str): The name for the logger, defaults to the current module name
        
    Returns:
        logging.Logger: Configured logger instance with file and/or console handlers
    """
    logger = logging.getLogger(name)

    log_level = config.LOGS.get("log_level", "INFO")
    if isinstance(log_level, str):
        logger.setLevel(log_level)
    else:
        raise ValueError("log_level must be a string representing the logging level.")

    if config.LOGS.get("enable_log_file", False):
        logger.addHandler(_file_handler) # type: ignore

    if config.LOGS.get("enable_console_log", False):
        logger.addHandler(_console_handler) # type: ignore

    return logger