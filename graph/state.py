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

    The state flows through two distinct feedback loops:
    1. Planning Loop: planner <-> researcher
    2. Writing Loop: writer <-> critic

    State fields are automatically managed by LangGraph, with the 'messages' field
    using the add_messages reducer for automatic message accumulation.
    """

    # Message history (automatically managed by add_messages reducer)
    # This maintains the full conversation context across all agents
    messages: Annotated[List[BaseMessage], add_messages]

    # User input
    topic: str

    # ============================================================================
    # PLANNING LOOP STATE
    # ============================================================================

    # Core planning outputs
    thesis: str                              # Developed by planner
    outline: str                             # Structured essay outline

    # Research coordination
    research_queries: List[str]              # Queries requested by planner
    research_results: List[dict]             # Results from Tavily searches

    # Loop control
    planning_iteration: int                  # Current planning iteration
    planning_complete: bool                  # Flag to exit planning loop

    # ============================================================================
    # WRITING LOOP STATE
    # ============================================================================

    # Core writing outputs
    draft: str                               # Current essay draft
    feedback: str                            # Critic's feedback

    # Loop control
    writing_iteration: int                   # Current writing iteration
    writing_complete: bool                   # Flag to exit writing loop

    # ============================================================================
    # CONFIGURATION
    # ============================================================================

    # Iteration limits (separate for each loop)
    max_planning_iterations: int
    max_writing_iterations: int

    # Essay parameters
    max_essay_length: int                    # Target word count

    # Model configuration
    model_provider: Literal["openai", "anthropic", "google"]
    model_name: str

    # ============================================================================
    # STREAMING FIELDS (for real-time UI updates)
    # ============================================================================

    # These fields are updated by agents for display in Streamlit
    current_outline: str                     # Updated by planner
    current_feedback: str                    # Updated by critic
