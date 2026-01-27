"""LangGraph workflow definition for video generation."""

from langgraph.graph import END, StateGraph

from .nodes import (
    concatenate_videos,
    generate_video_segment,
    handle_error,
    plan_script,
    prepare_assets,
)
from .state import VideoGeneratorState


def should_continue_generation(state: VideoGeneratorState) -> str:
    """Determine if we should continue generating segments or move to concatenation."""
    if state.get("error"):
        return "handle_error"

    current_idx = state.get("current_segment_index", 0)
    segments = state.get("segments", [])

    if current_idx < len(segments):
        return "generate_video_segment"
    else:
        return "concatenate_videos"


def after_planning(state: VideoGeneratorState) -> str:
    """Determine next step after script planning."""
    if state.get("error"):
        return "handle_error"
    return "prepare_assets"


def after_assets(state: VideoGeneratorState) -> str:
    """Determine next step after asset preparation."""
    if state.get("error"):
        return "handle_error"
    return "generate_video_segment"


def build_graph() -> StateGraph:
    """Build and return the video generation workflow graph.

    Workflow:
        plan_script → prepare_assets → generate_video_segment (loop) → concatenate_videos → END
                 ↘                ↘                          ↘
               handle_error    handle_error              handle_error → END
    """
    workflow = StateGraph(VideoGeneratorState)

    # Add nodes (split plan_scenes into plan_script + prepare_assets)
    workflow.add_node("plan_script", plan_script)
    workflow.add_node("prepare_assets", prepare_assets)
    workflow.add_node("generate_video_segment", generate_video_segment)
    workflow.add_node("concatenate_videos", concatenate_videos)
    workflow.add_node("handle_error", handle_error)

    # Set entry point
    workflow.set_entry_point("plan_script")

    # plan_script → prepare_assets or handle_error
    workflow.add_conditional_edges(
        "plan_script",
        after_planning,
        {
            "prepare_assets": "prepare_assets",
            "handle_error": "handle_error",
        },
    )

    # prepare_assets → generate_video_segment or handle_error
    workflow.add_conditional_edges(
        "prepare_assets",
        after_assets,
        {
            "generate_video_segment": "generate_video_segment",
            "handle_error": "handle_error",
        },
    )

    # generate_video_segment → loop or concatenate_videos or handle_error
    workflow.add_conditional_edges(
        "generate_video_segment",
        should_continue_generation,
        {
            "generate_video_segment": "generate_video_segment",
            "concatenate_videos": "concatenate_videos",
            "handle_error": "handle_error",
        },
    )

    workflow.add_edge("concatenate_videos", END)
    workflow.add_edge("handle_error", END)

    return workflow


# Compile the graph
graph = build_graph().compile()
