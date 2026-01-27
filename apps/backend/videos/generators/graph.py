"""LangGraph workflow definition for video generation."""

from langgraph.graph import END, StateGraph

from .nodes import (
    concatenate_videos,
    generate_scene1,
    generate_scene2,
    handle_error,
    plan_script,
    prepare_cta_frame,
    prepare_first_frame,
)
from .state import VideoGeneratorState


def after_planning(state: VideoGeneratorState) -> str:
    """Determine next step after script planning."""
    if state.get("error"):
        return "handle_error"
    return "prepare_first_frame"


def after_first_frame(state: VideoGeneratorState) -> str:
    """Determine next step after first frame preparation."""
    if state.get("error"):
        return "handle_error"
    return "generate_scene1"


def after_scene1(state: VideoGeneratorState) -> str:
    """Determine next step after Scene 1 generation."""
    if state.get("error"):
        return "handle_error"
    return "prepare_cta_frame"


def after_cta_frame(state: VideoGeneratorState) -> str:
    """Determine next step after CTA frame preparation."""
    if state.get("error"):
        return "handle_error"
    return "generate_scene2"


def after_scene2(state: VideoGeneratorState) -> str:
    """Determine next step after Scene 2 generation."""
    if state.get("error"):
        return "handle_error"
    return "concatenate_videos"


def build_graph() -> StateGraph:
    """Build and return the video generation workflow graph.

    New granular workflow:
        plan_script → prepare_first_frame → generate_scene1
            → prepare_cta_frame → generate_scene2 → concatenate_videos → END
                    ↘                     ↘                    ↘
                 handle_error          handle_error        handle_error → END
    """
    workflow = StateGraph(VideoGeneratorState)

    # Add nodes (split into granular steps)
    workflow.add_node("plan_script", plan_script)
    workflow.add_node("prepare_first_frame", prepare_first_frame)
    workflow.add_node("generate_scene1", generate_scene1)
    workflow.add_node("prepare_cta_frame", prepare_cta_frame)
    workflow.add_node("generate_scene2", generate_scene2)
    workflow.add_node("concatenate_videos", concatenate_videos)
    workflow.add_node("handle_error", handle_error)

    # Set entry point
    workflow.set_entry_point("plan_script")

    # plan_script → prepare_first_frame or handle_error
    workflow.add_conditional_edges(
        "plan_script",
        after_planning,
        {
            "prepare_first_frame": "prepare_first_frame",
            "handle_error": "handle_error",
        },
    )

    # prepare_first_frame → generate_scene1 or handle_error
    workflow.add_conditional_edges(
        "prepare_first_frame",
        after_first_frame,
        {
            "generate_scene1": "generate_scene1",
            "handle_error": "handle_error",
        },
    )

    # generate_scene1 → prepare_cta_frame or handle_error
    workflow.add_conditional_edges(
        "generate_scene1",
        after_scene1,
        {
            "prepare_cta_frame": "prepare_cta_frame",
            "handle_error": "handle_error",
        },
    )

    # prepare_cta_frame → generate_scene2 or handle_error
    workflow.add_conditional_edges(
        "prepare_cta_frame",
        after_cta_frame,
        {
            "generate_scene2": "generate_scene2",
            "handle_error": "handle_error",
        },
    )

    # generate_scene2 → concatenate_videos or handle_error
    workflow.add_conditional_edges(
        "generate_scene2",
        after_scene2,
        {
            "concatenate_videos": "concatenate_videos",
            "handle_error": "handle_error",
        },
    )

    workflow.add_edge("concatenate_videos", END)
    workflow.add_edge("handle_error", END)

    return workflow


# Compile the graph
graph = build_graph().compile()
