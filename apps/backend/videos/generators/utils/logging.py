"""Logging utilities with color support.

Integrates with Python's standard logging module while providing
colored terminal output for development.
"""

import json
import logging
import sys

# Create module logger
logger = logging.getLogger("videos.generators")


class Colors:
    """ANSI Color Codes for terminal output."""

    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def _is_tty() -> bool:
    """Check if stdout is a terminal (supports colors)."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def log(message: str, level: str = "INFO") -> None:
    """Log message using Python logging with optional color for terminals.

    Args:
        message: The message to log
        level: Log level (INFO, SUCCESS, WARNING, ERROR, DEBUG)
    """
    level_map = {
        "INFO": logging.INFO,
        "SUCCESS": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "DEBUG": logging.DEBUG,
    }

    log_level = level_map.get(level, logging.INFO)

    # Add color prefix for terminal output
    if _is_tty():
        level_colors = {
            "INFO": Colors.CYAN,
            "SUCCESS": Colors.BRIGHT_GREEN,
            "WARNING": Colors.BRIGHT_YELLOW,
            "ERROR": Colors.BRIGHT_RED,
            "DEBUG": Colors.DIM,
        }
        color = level_colors.get(level, Colors.WHITE)
        message = f"{color}{message}{Colors.RESET}"

    logger.log(log_level, message)


def log_separator(title: str = "") -> None:
    """Log separator line with optional title."""
    if title:
        if _is_tty():
            msg = f"\n{Colors.BRIGHT_MAGENTA}{'='*60}\n  {Colors.BOLD}{title}{Colors.RESET}\n{Colors.BRIGHT_MAGENTA}{'='*60}{Colors.RESET}"
        else:
            msg = f"\n{'='*60}\n  {title}\n{'='*60}"
        logger.info(msg)
    else:
        if _is_tty():
            logger.debug(f"{Colors.DIM}{'-' * 60}{Colors.RESET}")
        else:
            logger.debug("-" * 60)


def log_json(data: dict, title: str = "") -> None:
    """Pretty print JSON data."""
    formatted = json.dumps(data, indent=2, ensure_ascii=False)
    if title:
        if _is_tty():
            logger.debug(f"{Colors.BRIGHT_BLUE}[{title}]{Colors.RESET}\n{Colors.DIM}{formatted}{Colors.RESET}")
        else:
            logger.debug(f"[{title}]\n{formatted}")
    else:
        logger.debug(formatted)


def log_prompt(prompt: str, title: str = "") -> None:
    """Log prompt with highlighting."""
    separator = "-" * 40
    if title:
        if _is_tty():
            msg = f"{Colors.BRIGHT_CYAN}[{title}]{Colors.RESET}\n{Colors.DIM}{separator}{Colors.RESET}\n{prompt}\n{Colors.DIM}{separator}{Colors.RESET}"
        else:
            msg = f"[{title}]\n{separator}\n{prompt}\n{separator}"
        logger.debug(msg)
    else:
        logger.debug(f"{separator}\n{prompt}\n{separator}")
