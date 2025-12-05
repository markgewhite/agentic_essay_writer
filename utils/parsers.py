"""
Response parsing utilities for extracting structured data from LLM outputs.

These parsers handle text-based responses from different LLM providers,
which is more robust than JSON mode across providers.
"""

import re
from typing import Dict, List, Any


def parse_planner_response(content: str) -> Dict[str, Any]:
    """
    Parse planner agent response expecting specific format markers.

    Expected format:
        THESIS: [text]
        OUTLINE: [text]
        RESEARCH_NEEDED: Yes/No
        QUERIES:
        - [query 1]
        - [query 2]
        READY_TO_WRITE: Yes/No
        REASONING: [text]

    Args:
        content: Raw text output from planner LLM

    Returns:
        Dictionary with parsed fields:
        - thesis (str)
        - outline (str)
        - research_needed (bool)
        - new_queries (List[str])
        - ready_to_write (bool)
        - reasoning (str)
    """
    # Extract thesis
    thesis_match = re.search(r'THESIS:\s*(.+?)(?=\n(?:OUTLINE|$))', content, re.DOTALL | re.IGNORECASE)
    thesis = thesis_match.group(1).strip() if thesis_match else ""

    # Extract outline
    outline_match = re.search(r'OUTLINE:\s*(.+?)(?=\n(?:RESEARCH_NEEDED|$))', content, re.DOTALL | re.IGNORECASE)
    outline = outline_match.group(1).strip() if outline_match else ""

    # Extract research needed flag
    research_match = re.search(r'RESEARCH_NEEDED:\s*(Yes|No)', content, re.IGNORECASE)
    research_needed = research_match.group(1).lower() == "yes" if research_match else True

    # Extract queries (look for bullet points after QUERIES:)
    queries = []
    queries_match = re.search(r'QUERIES:\s*\n((?:[-•*]\s*.+\n?)+)', content, re.IGNORECASE)
    if queries_match:
        query_text = queries_match.group(1)
        # Extract each bullet point
        queries = re.findall(r'[-•*]\s*(.+)', query_text)
        queries = [q.strip() for q in queries if q.strip()]

    # Extract ready to write flag
    ready_match = re.search(r'READY_TO_WRITE:\s*(Yes|No)', content, re.IGNORECASE)
    ready_to_write = ready_match.group(1).lower() == "yes" if ready_match else False

    # Extract reasoning
    reasoning_match = re.search(r'REASONING:\s*(.+?)$', content, re.DOTALL | re.IGNORECASE)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

    return {
        "thesis": thesis,
        "outline": outline,
        "research_needed": research_needed,
        "new_queries": queries,
        "ready_to_write": ready_to_write,
        "reasoning": reasoning
    }


def parse_critic_response(content: str) -> Dict[str, Any]:
    """
    Parse critic agent response expecting specific format markers.

    Expected format:
        EVALUATION: [text]
        STRENGTHS:
        - [strength 1]
        - [strength 2]
        AREAS FOR IMPROVEMENT:
        1. [issue] - Example: [quote]
           Suggestion: [fix]
        LENGTH: [count] / [target] words
        APPROVED: Yes/No
        REASON: [text]

    Args:
        content: Raw text output from critic LLM

    Returns:
        Dictionary with parsed fields:
        - evaluation (str)
        - strengths (List[str])
        - improvements (List[str])
        - length_info (str)
        - approved (bool)
        - reason (str)
        - feedback (str): full formatted feedback for writer
    """
    # Extract evaluation
    eval_match = re.search(r'EVALUATION:\s*(.+?)(?=\n(?:STRENGTHS|$))', content, re.DOTALL | re.IGNORECASE)
    evaluation = eval_match.group(1).strip() if eval_match else ""

    # Extract strengths (bullet points)
    strengths = []
    strengths_match = re.search(r'STRENGTHS:\s*\n((?:[-•*]\s*.+\n?)+)', content, re.IGNORECASE)
    if strengths_match:
        strength_text = strengths_match.group(1)
        strengths = re.findall(r'[-•*]\s*(.+)', strength_text)
        strengths = [s.strip() for s in strengths if s.strip()]

    # Extract areas for improvement (numbered list with suggestions)
    improvements = []
    improvements_section = re.search(
        r'AREAS FOR IMPROVEMENT:\s*\n(.+?)(?=\n(?:LENGTH|APPROVED|$))',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if improvements_section:
        improvement_text = improvements_section.group(1)
        # Match numbered items with potential multi-line format
        improvement_items = re.findall(
            r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\Z)',
            improvement_text,
            re.DOTALL
        )
        improvements = [imp.strip() for imp in improvement_items if imp.strip()]

    # Extract length info
    length_match = re.search(r'LENGTH:\s*(.+?)(?=\n|$)', content, re.IGNORECASE)
    length_info = length_match.group(1).strip() if length_match else ""

    # Extract approved flag
    approved_match = re.search(r'APPROVED:\s*(Yes|No)', content, re.IGNORECASE)
    approved = approved_match.group(1).lower() == "yes" if approved_match else False

    # Extract reason
    reason_match = re.search(r'REASON:\s*(.+?)$', content, re.DOTALL | re.IGNORECASE)
    reason = reason_match.group(1).strip() if reason_match else ""

    # Construct full feedback for writer (formatted nicely)
    feedback_parts = []
    if evaluation:
        feedback_parts.append(f"EVALUATION: {evaluation}\n")
    if strengths:
        feedback_parts.append("STRENGTHS:")
        for strength in strengths:
            feedback_parts.append(f"- {strength}")
        feedback_parts.append("")
    if improvements:
        feedback_parts.append("AREAS FOR IMPROVEMENT:")
        for i, improvement in enumerate(improvements, 1):
            feedback_parts.append(f"{i}. {improvement}")
        feedback_parts.append("")
    if length_info:
        feedback_parts.append(f"LENGTH: {length_info}")
    if reason:
        feedback_parts.append(f"\n{reason}")

    feedback = "\n".join(feedback_parts)

    return {
        "evaluation": evaluation,
        "strengths": strengths,
        "improvements": improvements,
        "length_info": length_info,
        "approved": approved,
        "reason": reason,
        "feedback": feedback  # Formatted feedback string
    }


def estimate_word_count(text: str) -> int:
    """
    Estimate word count of text.

    Args:
        text: Input text

    Returns:
        Estimated word count
    """
    # Simple word count: split on whitespace
    words = text.split()
    return len(words)
