"""LangGraph nodes for video generation workflow."""

from .assets import prepare_assets, prepare_cta_frame, prepare_first_frame
from .concatenator import concatenate_videos
from .error_handler import handle_error
from .planner import plan_script
from .video_generator import generate_scene1, generate_scene2, generate_video_segment

# Game character nodes
from .game_planner import plan_game_scripts
from .game_assets import generate_game_frames
from .game_video_generator import generate_game_videos
from .game_concatenator import merge_game_videos

__all__ = [
    # Drama nodes
    "plan_script",
    "prepare_assets",
    "prepare_first_frame",
    "prepare_cta_frame",
    "generate_video_segment",
    "generate_scene1",
    "generate_scene2",
    "concatenate_videos",
    "handle_error",
    # Game character nodes
    "plan_game_scripts",
    "generate_game_frames",
    "generate_game_videos",
    "merge_game_videos",
]
