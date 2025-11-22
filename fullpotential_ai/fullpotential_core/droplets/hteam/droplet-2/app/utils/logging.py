import logging
from ..config import settings


def configure_logging():
    """Configure basic logging"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, settings.log_level.upper())
    )


def get_logger(name: str = None):
    """Get logger instance"""
    return logging.getLogger(name or __name__)