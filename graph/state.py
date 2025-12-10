"""
State schema for the multi-agent essay writing workflow.

Based on reference: /Users/markgewhite/MyFiles/Projects/training/ztm/llm_web_apps/agent/react_agent_langgraph.py:111-121
"""

from typing import TypedDict, Annotated, List, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class EssayState(TypedDict):
    """
    Comprehensive state for the multi-agent essay writing workflow.

    The workflow follows this pattern:
    1. Editor develops outline and requests research
    2. Researcher gathers information
    3. Writer creates draft based on outline and research
    4. Critic evaluates draft and provides feedback
    5. Editor reviews feedback and decides: more research, revise, or approve

    This creates a feedback loop where the editor can commission additional research
    or provide direction for revisions based on the critic's assessment.

    State fields are automatically managed by LangGraph, with the 'messages' field
    using the add_messages reducer for automatic message accumulation.
    """

    # Message history (automatically managed by add_messages reducer)
    # This maintains the full conversation context across all agents
    messages: Annotated[List[BaseMessage], add_messages]

    # User input
    topic: str

    # ============================================================================
    # EDITORIAL/RESEARCH STATE
    # ============================================================================

    # Core editorial outputs
    thesis: str                              # Developed by editor
    outline: str                             # Structured essay outline

    # Research coordination
    research_queries: List[str]              # Queries requested by editor
    research_results: List[dict]             # Results from Tavily searches

    # Editorial control
    editing_iteration: int                   # Current editing iteration (research requests)
    editing_complete: bool                   # Flag when initial outline is complete

    # ============================================================================
    # WRITING/CRITIQUE STATE
    # ============================================================================

    # Core writing outputs
    draft: str                               # Current essay draft
    feedback: str                            # Critic's feedback

    # Editor direction to writer
    editor_direction: str                    # Instructions from editor for revision
    editor_decision: str                     # Editor's decision: "research", "revise", or "approve"

    # Loop control
    critique_iteration: int                  # Full cycles through editor→write→critique
    writing_iteration: int                   # Revisions within a critique cycle
    essay_complete: bool                     # Flag when essay is approved

    # ============================================================================
    # CONFIGURATION
    # ============================================================================

    # Iteration limits
    max_editing_iterations: int              # Max research/outline iterations
    max_critique_iterations: int             # Max full critique cycles
    max_writing_iterations: int              # Max revisions per critique cycle

    # Essay parameters
    max_essay_length: int                    # Target word count

    # Model configuration (per-agent)
    editor_model: dict                       # {"provider": "openai", "name": "gpt-4o"}
    researcher_model: dict                   # {"provider": "openai", "name": "gpt-4o-mini"}
    writer_model: dict                       # {"provider": "anthropic", "name": "claude-3-5-sonnet-latest"}
    critic_model: dict                       # {"provider": "openai", "name": "gpt-4o"}

    # ============================================================================
    # ROUTING CONTROL
    # ============================================================================

    # Track node execution history for routing decisions
    node_history: List[str]                  # History of nodes visited (for routing logic)

    # ============================================================================
    # STREAMING FIELDS (for real-time UI updates)
    # ============================================================================

    # These fields are updated by agents for display in Streamlit
    current_outline: str                     # Updated by editor
    current_feedback: str                    # Updated by critic
    current_research_highlights: List[dict]  # Updated by researcher - preview of results
    current_draft: str                       # Updated by writer - current draft text


def create_initial_state(
    topic: str,
    editor_model: dict,
    researcher_model: dict,
    writer_model: dict,
    critic_model: dict,
    max_editing_iterations: int = 3,
    max_critique_iterations: int = 3,
    max_writing_iterations: int = 3,
    max_essay_length: int = 2000
) -> EssayState:
    """
    Create an initial EssayState with default values.

    This centralizes state initialization to ensure consistency and
    makes it easy to maintain when new fields are added.

    Args:
        topic: The essay topic
        editor_model: Model config for editor agent {"provider": "openai", "name": "gpt-4o"}
        researcher_model: Model config for researcher agent (recommend cheap model)
        writer_model: Model config for writer agent
        critic_model: Model config for critic agent
        max_editing_iterations: Max research/outline iterations (default: 3)
        max_critique_iterations: Max full critique cycles (default: 3)
        max_writing_iterations: Max revisions per critique cycle (default: 3)
        max_essay_length: Target word count (default: 2000)

    Returns:
        A fully initialized EssayState ready for workflow execution
    """
    return {
        "messages": [],
        "topic": topic,
        "thesis": "",
        "outline": "",
        "research_queries": [],
        "research_results": [],
        "editing_iteration": 0,
        "editing_complete": False,
        "draft": "",
        "feedback": "",
        "editor_direction": "",
        "editor_decision": "",
        "critique_iteration": 0,
        "writing_iteration": 0,
        "essay_complete": False,
        "max_editing_iterations": max_editing_iterations,
        "max_critique_iterations": max_critique_iterations,
        "max_writing_iterations": max_writing_iterations,
        "max_essay_length": max_essay_length,
        "editor_model": editor_model,
        "researcher_model": researcher_model,
        "writer_model": writer_model,
        "critic_model": critic_model,
        "node_history": [],
        "current_outline": "",
        "current_feedback": "",
        "current_research_highlights": [],
        "current_draft": ""
    }
