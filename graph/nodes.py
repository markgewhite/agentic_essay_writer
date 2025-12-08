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
from config.prompts import PLANNER_PROMPT, WRITER_PROMPT, CRITIC_PROMPT, SUMMARISER_PROMPT
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

    # Determine task based on iteration
    if state["planning_iteration"] == 0:
        task = "Analyze the topic and identify what research is needed to develop a strong thesis and outline."
    else:
        task = "Review the research results and decide if you have sufficient information to create a complete outline, or if you need additional research."

    # Construct user message
    user_message = f"""Topic: {state['topic']}

Current Iteration: {state['planning_iteration'] + 1}/{state['max_planning_iterations']}

{research_context}

Task: {task}

Please provide your thesis, outline, and any additional research queries needed.
If you have sufficient research to proceed with writing, set READY_TO_WRITE to Yes.
"""

    # Create messages for LLM
    messages = [
        HumanMessage(content=PLANNER_PROMPT),
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
        "current_outline": parsed["outline"],  # For streaming to UI
        "messages": [response]
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

                # Include up to 3000 chars per source for the summarizer
                if len(content) > 3000:
                    content = content[:3000] + "..."

                research_content += f"\n[Source {i}] {title}\nURL: {url}\n{content}\n"

            # Build context message
            context_message = f"""Essay Topic: {state['topic']}

Current Thesis: {state.get('thesis', 'Not yet developed')}

Research Query: {result['query']}

Raw Research Findings:
{research_content}"""

            # Create messages using the SUMMARISER_PROMPT
            messages = [
                HumanMessage(content=SUMMARISER_PROMPT),
                HumanMessage(content=context_message)
            ]

            # Get summary from LLM
            summary_response = llm.invoke(messages)

            # Store summary in the result
            result['summary'] = summary_response.content

    # Append to existing research results
    all_results = state.get("research_results", []) + results

    return {
        "research_results": all_results,
        "research_queries": []  # Clear queries after execution
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

        user_message = f"""Topic: {state['topic']}

Thesis: {state['thesis']}

Outline:
{state['outline']}

Research Summary:
{research_summary}

Target Length: {state['max_essay_length']} words

Task: Write the initial essay draft following the outline exactly. Integrate the research findings to support your arguments. Aim for approximately {state['max_essay_length']} words.
"""

    else:
        # Revision based on feedback
        user_message = f"""Current Draft:
{state['draft']}

Critic Feedback:
{state['feedback']}

Target Length: {state['max_essay_length']} words
Current Iteration: {state['writing_iteration']}/{state['max_writing_iterations']}

Task: Revise the draft addressing ALL feedback points. Preserve the strengths identified and improve the areas that need work. Maintain overall coherence.
"""

    # Create messages for LLM
    messages = [
        HumanMessage(content=WRITER_PROMPT),
        HumanMessage(content=user_message)
    ]

    # Invoke LLM
    response = llm.invoke(messages)

    return {
        "draft": response.content,
        "writing_iteration": state["writing_iteration"] + 1,
        "messages": [response]
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

    # Construct user message
    user_message = f"""Essay Draft:
{state['draft']}

Original Outline:
{state['outline']}

Thesis:
{state['thesis']}

Target Length: {state['max_essay_length']} words
Current Word Count: ~{word_count} words
Current Iteration: {state['writing_iteration']}/{state['max_writing_iterations']}

Task: Evaluate the draft thoroughly against all criteria. Provide specific, actionable feedback. If the essay meets high standards, approve it. If not, identify specific improvements needed.
"""

    # Create messages for LLM
    messages = [
        HumanMessage(content=CRITIC_PROMPT),
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
        "current_feedback": parsed["feedback"],  # For streaming to UI
        "messages": [response]
    }
