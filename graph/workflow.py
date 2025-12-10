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
from graph.nodes import editor_node, researcher_node, writer_node, critic_node


def route_after_editor(state: EssayState) -> Literal["researcher", "writer", "complete"]:
    """
    Routing logic after editor node executes.

    The editor serves three roles:
    1. Initial editing: Requests research until outline is ready
    2. Critique review: Decides what to do after critic feedback
    3. Post-research handoff: Passes commissioned research to writer

    Args:
        state: Current essay state

    Returns:
        "researcher" - Need to gather (more) research
        "writer" - Ready to write or revise
        "complete" - Essay is approved
    """
    # Context 1: Initial editing phase (no draft yet)
    if state.get("draft", "") == "":
        # Check if initial editing is complete
        if state.get("editing_complete", False):
            return "writer"  # Ready for first draft
        else:
            return "researcher"  # Need more research for outline

    # Context 2: Reviewing critique (draft exists)
    else:
        # Check if essay is approved
        if state.get("essay_complete", False):
            return "complete"

        # Safety check: max critique iterations
        if state.get("critique_iteration", 0) >= state.get("max_critique_iterations", 3):
            return "complete"

        # Get editor's decision
        decision = state.get("editor_decision", "revise")

        if decision == "research":
            return "researcher"  # Commission more research
        elif decision == "pass_to_writer":
            return "writer"  # Just received research, pass to writer
        else:
            return "writer"  # Revise with direction (approve becomes complete above)


def create_essay_workflow():
    """
    Create the multi-agent essay writing workflow.

    Graph Structure:

        START → editor → researcher → [should_continue_editing?]
                           ↑            ├─> editor (continue editing)
                           │            └─> writer (editing complete)
                           │                  ↓
                           │               critic
                           │                  ↓
                           │               editor (review feedback)
                           │                  ↓
                           │            [route_editor_decision?]
                           │            ├─> researcher (more research needed)
                           │            ├─> writer (revise with direction)
                           └────────────┘  └─> END (essay approved)

    Three main phases:
    1. Initial Editing Loop: editor <-> researcher
       - Develops outline and commissions research
       - Continues until editor is ready to write

    2. First Draft: writer → critic → editor
       - Writer creates draft
       - Critic evaluates and provides feedback
       - Editor reviews feedback

    3. Revision Loop: editor → [researcher OR writer] → critic → editor
       - Editor decides: more research, revise outline, or approve
       - If research: researcher → writer (with new info)
       - If revise: writer (with editor direction)
       - Continues until editor approves or max iterations

    Returns:
        Compiled LangGraph that can be invoked or streamed
    """
    # Create state graph
    graph = StateGraph(EssayState)

    # ========================================================================
    # ADD NODES
    # ========================================================================

    graph.add_node("editor", editor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)

    # ========================================================================
    # DEFINE EDGES
    # ========================================================================

    # Main workflow: START → editor (makes all routing decisions)
    graph.add_edge(START, "editor")

    # Editor routes to researcher, writer, or END based on context
    graph.add_conditional_edges(
        "editor",
        route_after_editor,
        {
            "researcher": "researcher",  # Need (more) research
            "writer": "writer",          # Ready to write or revise
            "complete": END              # Essay approved
        }
    )

    # Researcher always returns to editor for evaluation
    graph.add_edge("researcher", "editor")

    # Writer → Critic → Editor (critique feedback loop)
    graph.add_edge("writer", "critic")
    graph.add_edge("critic", "editor")

    # ========================================================================
    # COMPILE
    # ========================================================================

    compiled_graph = graph.compile()

    return compiled_graph
