"""
LangGraph workflow construction for multi-agent essay writing.

Based on reference: /Users/markgewhite/MyFiles/Projects/training/ztm/llm_web_apps/agent/react_agent_langgraph.py:198-254

Graph structure:
    START → planner → researcher → [should_continue_planning?]
                                     ├─> planner (continue)
                                     └─> writer → critic → [should_continue_writing?]
                                                            ├─> writer (continue)
                                                            └─> END (complete)
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from graph.state import EssayState
from graph.nodes import planner_node, researcher_node, writer_node, critic_node


def should_continue_planning(state: EssayState) -> Literal["continue", "complete"]:
    """
    Routing logic for planning loop.

    Continue planning if:
    - planning_complete is False
    - Haven't reached max iterations

    Args:
        state: Current essay state

    Returns:
        "continue" to loop back to planner, "complete" to move to writer
    """
    if state["planning_complete"]:
        return "complete"

    # Safety check: shouldn't happen but prevents infinite loops
    if state["planning_iteration"] >= state["max_planning_iterations"]:
        return "complete"

    return "continue"


def should_continue_writing(state: EssayState) -> Literal["continue", "complete"]:
    """
    Routing logic for writing loop.

    Continue writing if:
    - writing_complete is False
    - Haven't reached max iterations

    Args:
        state: Current essay state

    Returns:
        "continue" to loop back to writer, "complete" to end
    """
    if state["writing_complete"]:
        return "complete"

    # Safety check
    if state["writing_iteration"] >= state["max_writing_iterations"]:
        return "complete"

    return "continue"


def create_essay_workflow():
    """
    Create the multi-agent essay writing workflow.

    Graph Structure:

        START → planner → researcher → [conditional]
                                        ├─> planner (if more research needed)
                                        └─> writer → critic → [conditional]
                                                               ├─> writer (if revisions needed)
                                                               └─> END (if approved)

    Two feedback loops:
    1. Planning Loop: planner <-> researcher
       - Continues until planner has sufficient research or max iterations
    2. Writing Loop: writer <-> critic
       - Continues until critic approves or max iterations

    Returns:
        Compiled LangGraph that can be invoked or streamed
    """
    # Create state graph
    graph = StateGraph(EssayState)

    # ========================================================================
    # ADD NODES
    # ========================================================================

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)

    # ========================================================================
    # DEFINE EDGES
    # ========================================================================

    # Planning Loop: START → planner → researcher → conditional
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")

    # Conditional routing after research
    graph.add_conditional_edges(
        "researcher",
        should_continue_planning,
        {
            "continue": "planner",    # More research/planning needed
            "complete": "writer"      # Planning done, start writing
        }
    )

    # Writing Loop: writer → critic → conditional
    graph.add_edge("writer", "critic")

    # Conditional routing after critique
    graph.add_conditional_edges(
        "critic",
        should_continue_writing,
        {
            "continue": "writer",     # Revisions needed
            "complete": END           # Essay approved/complete
        }
    )

    # ========================================================================
    # COMPILE
    # ========================================================================

    compiled_graph = graph.compile()

    return compiled_graph
