# logger.py — sets up logging for the project
import logging
import os
from config import OUTPUT_DIR

def setup_logger(name="quorum", log_file=None):
    logger = logging.getLogger(name)
    
    # Prevent adding duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Console handler - shows INFO and above during normal use
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Format: timestamp, module name, level, message
    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler - logs everything including DEBUG for detailed diagnostics
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
