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
from config.prompts import EDITOR_PROMPTS, WRITER_PROMPTS, CRITIC_PROMPTS, RESEARCHER_PROMPTS
from graph.tools import format_research_results, summarize_research, execute_research
from utils.parsers import parse_planner_response, parse_editor_review_response, parse_critic_response, estimate_word_count
from langchain_core.messages import HumanMessage, AIMessage


def editor_node(state: EssayState) -> dict:
    """
    Editor agent performs three roles based on workflow context:

    1. Initial Editing (when draft is empty):
       - Develops thesis and outline
       - Requests research to support arguments
       - Refines based on research results

    2. Post-Research Handoff (after commissioning research during critique):
       - Just received new research that was commissioned
       - Pass directly to writer without making another decision
       - Uses the direction already provided

    3. Critique Review (when draft exists with feedback):
       - Reviews critic's feedback
       - Decides: commission research, revise outline, or approve
       - Provides direction to writer

    Args:
        state: Current essay state

    Returns:
        Dict with updated state fields depending on context
    """
    # Get LLM for editor
    llm = get_llm(state["editor_model"]["provider"], state["editor_model"]["name"])

    # Check node history to determine context
    node_history = state.get("node_history", [])

    # Check if we just returned from researcher (commissioned research in previous editor call)
    # Pattern: [..., "editor", "researcher", "editor" (current)]
    just_returned_from_research = (
        len(node_history) >= 2 and
        node_history[-1] == "researcher" and
        node_history[-2] == "editor" and
        state.get("draft", "") != ""  # Only applies when we have a draft
    )

    # Determine context: Are we in initial editing or reviewing a critique?
    is_reviewing_critique = (
        state.get("draft", "") != "" and
        state.get("feedback", "") != "" and
        not just_returned_from_research  # Don't review again if we just got research back
    )

    if just_returned_from_research:
        # ====================================================================
        # CONTEXT: Just received research commissioned during critique review
        # ====================================================================
        # We already made a decision and provided direction in the previous
        # editor call. Now we just pass the new research to the writer.
        # Don't make another approve/research/revise decision yet.

        # Get current node history and append this visit
        updated_history = state.get("node_history", []) + ["editor"]

        return {
            "editor_decision": "pass_to_writer",  # Signal to routing to go to writer
            "writing_iteration": 0,  # Reset for new writing cycle with research
            "node_history": updated_history
        }

    elif is_reviewing_critique:
        # ====================================================================
        # CONTEXT: Reviewing critic feedback on a draft
        # ====================================================================

        user_message = EDITOR_PROMPTS["review_critique"].format(
            topic=state['topic'],
            thesis=state['thesis'],
            outline=state['outline'],
            draft=state['draft'],
            feedback=state['feedback'],
            critique_iteration=state['critique_iteration'] + 1,
            max_critique_iterations=state['max_critique_iterations']
        )

        messages = [
            HumanMessage(content=EDITOR_PROMPTS["system"]),
            HumanMessage(content=user_message)
        ]

        response = llm.invoke(messages)
        parsed = parse_editor_review_response(response.content)

        # Increment critique iteration
        new_critique_iteration = state["critique_iteration"] + 1

        # Only mark complete if editor explicitly approves
        # (The routing function will handle max iterations safety check)
        essay_complete = (parsed["editor_decision"] == "approve")

        # Get current node history and append this visit
        updated_history = state.get("node_history", []) + ["editor"]

        return {
            "thesis": parsed["thesis"],
            "outline": parsed["outline"],
            "research_queries": parsed["new_queries"],
            "editor_direction": parsed["direction_to_writer"],
            "editor_decision": parsed["editor_decision"],
            "critique_iteration": new_critique_iteration,
            "essay_complete": essay_complete,
            "writing_iteration": 0,  # Reset writing iteration for new cycle
            "current_outline": parsed["outline"],  # For streaming to UI
            "node_history": updated_history
        }

    else:
        # ====================================================================
        # CONTEXT: Initial editing phase (developing outline and research)
        # ====================================================================

        research_context = format_research_results(state["research_results"])

        # Select appropriate prompt
        if state["editing_iteration"] == 0:
            prompt_key = "initial"
        else:
            prompt_key = "subsequent"

        user_message = EDITOR_PROMPTS[prompt_key].format(
            topic=state['topic'],
            iteration=state['editing_iteration'] + 1,
            max_iterations=state['max_editing_iterations'],
            research_context=research_context
        )

        messages = [
            HumanMessage(content=EDITOR_PROMPTS["system"]),
            HumanMessage(content=user_message)
        ]

        response = llm.invoke(messages)
        parsed = parse_planner_response(response.content)

        # Increment iteration
        new_iteration = state["editing_iteration"] + 1

        # Determine completion
        is_complete = (
            parsed["ready_to_write"] or
            new_iteration >= state["max_editing_iterations"] or
            len(parsed["new_queries"]) == 0
        )

        # Get current node history and append this visit
        updated_history = state.get("node_history", []) + ["editor"]

        return {
            "thesis": parsed["thesis"],
            "outline": parsed["outline"],
            "research_queries": parsed["new_queries"],
            "editing_iteration": new_iteration,
            "editing_complete": is_complete,
            "current_outline": parsed["outline"],  # For streaming to UI
            "node_history": updated_history
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

    # Get LLM for summarization (use researcher model)
    llm = get_llm(state["researcher_model"]["provider"], state["researcher_model"]["name"])

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

    # Get current node history and append this visit
    updated_history = state.get("node_history", []) + ["researcher"]

    return {
        "research_results": all_results,
        "research_queries": [],  # Clear queries after execution
        "current_research_highlights": highlights,  # For streaming to UI
        "node_history": updated_history
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
    # Get LLM for writer
    llm = get_llm(state["writer_model"]["provider"], state["writer_model"]["name"])

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
        # Revision based on feedback and editor direction
        # Summarize any new research (from latest queries)
        new_research_summary = ""
        if state.get("research_queries"):
            # If there are pending queries, that means new research was just gathered
            # Get only the most recent research results
            all_results = state.get("research_results", [])
            num_queries = len(state.get("research_queries", []))
            if num_queries > 0 and len(all_results) >= num_queries:
                recent_results = all_results[-num_queries:]
                new_research_summary = summarize_research(recent_results)
            else:
                new_research_summary = "No new research was commissioned for this revision."
        else:
            new_research_summary = "No new research was commissioned for this revision."

        user_message = WRITER_PROMPTS["revision"].format(
            draft=state['draft'],
            outline=state['outline'],
            feedback=state['feedback'],
            editor_direction=state.get('editor_direction', 'Please address the critic\'s feedback.'),
            new_research=new_research_summary,
            max_essay_length=state['max_essay_length'],
            critique_iteration=state.get('critique_iteration', 1),
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

    # Get current node history and append this visit
    updated_history = state.get("node_history", []) + ["writer"]

    return {
        "draft": response.content,
        "writing_iteration": state["writing_iteration"] + 1,
        "current_draft": response.content,  # For streaming to UI
        "node_history": updated_history
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
    # Get LLM for critic
    llm = get_llm(state["critic_model"]["provider"], state["critic_model"]["name"])

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

    # Get current node history and append this visit
    updated_history = state.get("node_history", []) + ["critic"]

    return {
        "feedback": parsed["feedback"],
        "writing_complete": is_complete,
        "current_feedback": parsed["feedback"],  # For streaming to UI
        "node_history": updated_history
    }
