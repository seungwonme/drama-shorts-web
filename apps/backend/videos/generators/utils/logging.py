"""Logging utilities with color support."""

import json
from datetime import datetime


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


def log(message: str, level: str = "INFO") -> None:
    """Print colored log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    level_colors = {
        "INFO": Colors.CYAN,
        "SUCCESS": Colors.BRIGHT_GREEN,
        "WARNING": Colors.BRIGHT_YELLOW,
        "ERROR": Colors.BRIGHT_RED,
        "DEBUG": Colors.DIM,
    }

    color = level_colors.get(level, Colors.WHITE)
    timestamp_color = Colors.DIM

    print(
        f"{timestamp_color}[{timestamp}]{Colors.RESET} "
        f"{color}[{level}]{Colors.RESET} {message}"
    )


def log_separator(title: str = "") -> None:
    """Print separator line with optional title."""
    if title:
        print(f"\n{Colors.BRIGHT_MAGENTA}{'='*60}")
        print(f"  {Colors.BOLD}{title}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{'='*60}{Colors.RESET}")
    else:
        print(f"{Colors.DIM}{'-' * 60}{Colors.RESET}")


def log_json(data: dict, title: str = "") -> None:
    """Pretty print JSON data with color."""
    if title:
        print(f"\n{Colors.BRIGHT_BLUE}[{title}]{Colors.RESET}")
    print(f"{Colors.DIM}{json.dumps(data, indent=2, ensure_ascii=False)}{Colors.RESET}")


def log_prompt(prompt: str, title: str = "") -> None:
    """Print prompt with highlighting."""
    if title:
        print(f"\n{Colors.BRIGHT_CYAN}[{title}]{Colors.RESET}")
    print(f"{Colors.DIM}{'-' * 40}{Colors.RESET}")
    print(f"{Colors.WHITE}{prompt}{Colors.RESET}")
    print(f"{Colors.DIM}{'-' * 40}{Colors.RESET}")
