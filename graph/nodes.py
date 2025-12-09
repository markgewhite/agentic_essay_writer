"""
Agent node implementations for the essay writing workflow.

Based on reference: /Users/markgewhite/MyFiles/Projects/training/ztm/llm_web_apps/agent/react_agent_langgraph.py:128-162

Each node follows the pattern:
- Takes state: EssayState as input
- Returns dict with updated state fields
- LangGraph automatically merges returned dict into state
"""

from graph.state import EssayState
from config.models import get_llm
from config.prompts import PLANNER_PROMPTS, WRITER_PROMPTS, CRITIC_PROMPTS, RESEARCHER_PROMPTS
from graph.tools import format_research_results, summarize_research, execute_research
from utils.parsers import parse_planner_response, parse_critic_response, estimate_word_count
from langchain_core.messages import HumanMessage, AIMessage


def planner_node(state: EssayState) -> dict:
    """
    Planner agent develops thesis and outline, requests research.

    Decision logic:
    - Iteration 0: Analyze topic, identify research needs
    - Later iterations: Evaluate research, refine outline
    - Set planning_complete=True when satisfied or max iterations reached

    Args:
        state: Current essay state

    Returns:
        Dict with updated: thesis, outline, research_queries, planning_iteration,
        planning_complete, current_outline (for streaming), messages
    """
    # Get LLM
    llm = get_llm(state["model_provider"], state["model_name"])

    # Build context from previous research
    research_context = format_research_results(state["research_results"])

    # Select appropriate prompt based on iteration
    if state["planning_iteration"] == 0:
        prompt_key = "initial"
    else:
        prompt_key = "subsequent"

    # Construct user message using appropriate template
    user_message = PLANNER_PROMPTS[prompt_key].format(
        topic=state['topic'],
        iteration=state['planning_iteration'] + 1,
        max_iterations=state['max_planning_iterations'],
        research_context=research_context
    )

    # Create messages for LLM
    messages = [
        HumanMessage(content=PLANNER_PROMPTS["system"]),
        HumanMessage(content=user_message)
    ]

    # Invoke LLM
    response = llm.invoke(messages)

    # Parse response
    parsed = parse_planner_response(response.content)

    # Increment iteration
    new_iteration = state["planning_iteration"] + 1

    # Determine completion with multiple safety mechanisms
    is_complete = (
        parsed["ready_to_write"] or                       # Agent decides ready
        new_iteration >= state["max_planning_iterations"] or  # Hard limit
        len(parsed["new_queries"]) == 0                   # No more queries
    )

    return {
        "thesis": parsed["thesis"],
        "outline": parsed["outline"],
        "research_queries": parsed["new_queries"],
        "planning_iteration": new_iteration,
        "planning_complete": is_complete,
        "current_outline": parsed["outline"]  # For streaming to UI
    }


def researcher_node(state: EssayState) -> dict:
    """
    Researcher agent executes Tavily searches and summarizes findings.

    This node:
    1. Executes Tavily searches for all queries
    2. Uses an LLM to intelligently summarize each query's results in context
    3. Stores both raw results and intelligent summaries

    Args:
        state: Current essay state

    Returns:
        Dict with updated: research_results, research_queries (cleared)
    """
    # Execute all research queries
    results = execute_research(state["research_queries"])

    # Get LLM for summarization
    llm = get_llm(state["model_provider"], state["model_name"])

    # Summarize each query's results using LLM
    for result in results:
        if "error" not in result:
            # Prepare research content for summarization
            research_content = ""
            for i, item in enumerate(result.get('results', []), 1):
                title = item.get('title', 'N/A')
                content = item.get('raw_content', item.get('content', 'N/A'))
                url = item.get('url', 'N/A')

                # Include up to 5000 chars per source for the summarizer (more depth)
                if len(content) > 5000:
                    content = content[:5000] + "..."

                # Add clear separators between sources within a query
                research_content += f"\n[Source {i}] {title}\nURL: {url}\n{content}\n"
                research_content += "\n" + "-" * 80 + "\n"  # Separator between sources

            # Build context message using template
            context_message = RESEARCHER_PROMPTS["user"].format(
                topic=state['topic'],
                thesis=state.get('thesis', 'Not yet developed'),
                query=result['query'],
                research_content=research_content
            )

            # Create messages using the RESEARCHER_PROMPTS
            messages = [
                HumanMessage(content=RESEARCHER_PROMPTS["system"]),
                HumanMessage(content=context_message)
            ]

            # Get summary from LLM
            summary_response = llm.invoke(messages)

            # Store summary in the result
            result['summary'] = summary_response.content

    # Append to existing research results
    all_results = state.get("research_results", []) + results

    # Prepare highlights for UI display (first 200 chars of each summary)
    highlights = []
    for result in results:
        if "error" not in result and "summary" in result:
            preview = {
                "query": result["query"],
                "preview": result["summary"][:200] + "..." if len(result["summary"]) > 200 else result["summary"]
            }
            highlights.append(preview)

    return {
        "research_results": all_results,
        "research_queries": [],  # Clear queries after execution
        "current_research_highlights": highlights  # For streaming to UI
    }


def writer_node(state: EssayState) -> dict:
    """
    Writer agent generates initial draft or revises based on feedback.

    Decision logic:
    - Iteration 0: Generate initial draft from outline and research
    - Later iterations: Revise draft based on critic's feedback

    Args:
        state: Current essay state

    Returns:
        Dict with updated: draft, writing_iteration, messages
    """
    # Get LLM
    llm = get_llm(state["model_provider"], state["model_name"])

    if state["writing_iteration"] == 0:
        # Initial draft generation
        research_summary = summarize_research(state["research_results"])

        user_message = WRITER_PROMPTS["initial_draft"].format(
            topic=state['topic'],
            thesis=state['thesis'],
            outline=state['outline'],
            research_summary=research_summary,
            max_essay_length=state['max_essay_length']
        )

    else:
        # Revision based on feedback
        user_message = WRITER_PROMPTS["revision"].format(
            draft=state['draft'],
            feedback=state['feedback'],
            max_essay_length=state['max_essay_length'],
            iteration=state['writing_iteration'],
            max_iterations=state['max_writing_iterations']
        )

    # Create messages for LLM
    messages = [
        HumanMessage(content=WRITER_PROMPTS["system"]),
        HumanMessage(content=user_message)
    ]

    # Invoke LLM
    response = llm.invoke(messages)

    return {
        "draft": response.content,
        "writing_iteration": state["writing_iteration"] + 1,
        "current_draft": response.content  # For streaming to UI
    }


def critic_node(state: EssayState) -> dict:
    """
    Critic agent evaluates draft quality and provides feedback.

    Evaluation criteria:
    - Structure alignment with outline
    - Argument strength and coherence
    - Use of research evidence
    - Writing quality and clarity
    - Length requirements

    Args:
        state: Current essay state

    Returns:
        Dict with updated: feedback, writing_complete, current_feedback (for streaming), messages
    """
    # Get LLM
    llm = get_llm(state["model_provider"], state["model_name"])

    # Estimate current word count
    word_count = estimate_word_count(state["draft"])

    # Construct user message using template
    user_message = CRITIC_PROMPTS["user"].format(
        draft=state['draft'],
        outline=state['outline'],
        thesis=state['thesis'],
        max_essay_length=state['max_essay_length'],
        word_count=word_count,
        iteration=state['writing_iteration'],
        max_iterations=state['max_writing_iterations']
    )

    # Create messages for LLM
    messages = [
        HumanMessage(content=CRITIC_PROMPTS["system"]),
        HumanMessage(content=user_message)
    ]

    # Invoke LLM
    response = llm.invoke(messages)

    # Parse response
    parsed = parse_critic_response(response.content)

    # Determine if writing is complete
    is_complete = (
        parsed["approved"] or                              # Critic approves
        state["writing_iteration"] >= state["max_writing_iterations"]  # Hard limit
    )

    return {
        "feedback": parsed["feedback"],
        "writing_complete": is_complete,
        "current_feedback": parsed["feedback"]  # For streaming to UI
    }
