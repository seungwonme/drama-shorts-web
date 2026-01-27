"""Error handler node - handles workflow errors."""

from ..state import VideoGeneratorState
from ..utils.logging import log, log_separator


def handle_error(state: VideoGeneratorState) -> dict:
    """Handle errors in the workflow."""
    log_separator("Error Handling")

    error = state.get("error", "Unknown error")
    log(f"Error occurred: {error}", "ERROR")

    return {
        "status": "error",
    }
