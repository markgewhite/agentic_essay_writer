"""
Tavily search integration and research formatting utilities.

Provides tools for web research and formatting search results for LLM consumption.
"""

import os
from typing import List, Dict
from datetime import datetime
from langchain_community.tools.tavily_search import TavilySearchResults


def create_tavily_tool(max_results: int = 3):
    """
    Create Tavily search tool with appropriate configuration.

    Args:
        max_results: Number of results to retrieve per query (default: 3)

    Configuration:
    - max_results: Configurable results per query (balanced quality vs. volume)
    - search_depth: "advanced" for higher quality, more relevant results
    - include_answer: True to get AI-generated summary
    - include_raw_content: True to get full content for in-depth research
    - include_images: False (not needed for text essays)

    Returns:
        Configured TavilySearchResults instance

    Raises:
        ValueError: If TAVILY_API_KEY not found in environment

    Example:
        >>> tool = create_tavily_tool(max_results=5)
        >>> results = tool.invoke({"query": "impact of AI on education"})
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY not found in environment. "
            "Please set it in your .env file."
        )

    return TavilySearchResults(
        max_results=max_results,    # Configurable results per query
        search_depth="advanced",    # Deep search for quality
        include_answer=True,        # Get AI-generated answer
        include_raw_content=True,   # Get full content for in-depth research
        include_images=False        # Not needed for text essays
    )


def format_research_results(results: List[Dict]) -> str:
    """
    Format research results for inclusion in planner prompts.

    Structures the research data in a readable format that the planner
    can easily parse and evaluate.

    Args:
        results: List of research result dictionaries, each containing:
                 - query (str): The search query
                 - results (list): Search results from Tavily
                 - timestamp (str): ISO format timestamp
                 - error (str, optional): Error message if search failed

    Returns:
        Formatted string ready for prompt inclusion

    Example format:
        RESEARCH RESULTS:

        Query 1: "impact of AI on education"
        Findings:
          - [Title]
            [Content excerpt...]
            Source: [URL]
          - [Title]
            [Content excerpt...]
            Source: [URL]
    """
    if not results:
        return "No research conducted yet."

    formatted = "RESEARCH RESULTS:\n\n"

    for i, result in enumerate(results, 1):
        formatted += f"Query {i}: \"{result['query']}\"\n"

        if "error" in result:
            formatted += f"  Error: {result['error']}\n"
            # Add separator between queries even for errors
            if i < len(results):
                formatted += "\n" + ("*" * 80) + "\n\n"
            continue

        # Use LLM-generated summary if available, otherwise fall back to raw content
        if "summary" in result:
            formatted += "Summary:\n"
            formatted += f"{result['summary']}\n"
        else:
            # Fallback to raw content (legacy support)
            formatted += "Findings:\n"
            for j, item in enumerate(result.get('results', []), 1):
                title = item.get('title', 'N/A')
                content = item.get('raw_content', item.get('content', 'N/A'))
                url = item.get('url', 'N/A')

                #if len(content) > 2000:
                #    content = content[:2000] + "..."

                formatted += f"  Source {j}: {title}\n"
                formatted += f"  URL: {url}\n"
                formatted += f"  {content}\n"
                # Separator between sources within the same query
                formatted += "  " + ("-" * 76) + "\n"

        # Add clear separator between queries (asterisks)
        if i < len(results):
            formatted += "\n" + ("*" * 80) + "\n\n"

    return formatted


def summarize_research(results: List[Dict]) -> str:
    """
    Create concise research summary for writer agent.

    Condenses research findings into key points that the writer
    can reference while drafting.

    Args:
        results: List of research result dictionaries

    Returns:
        Condensed summary highlighting key findings

    Example format:
        KEY RESEARCH FINDINGS:

        On 'impact of AI on education':
        - [Key finding 1 excerpt...]
        - [Key finding 2 excerpt...]
    """
    if not results:
        return "No research available."

    summary = "KEY RESEARCH FINDINGS:\n\n"

    for idx, result in enumerate(results, 1):
        if "error" not in result:
            summary += f"Query {idx}: '{result['query']}'\n"

            # Use LLM-generated summary if available
            if "summary" in result:
                summary += f"{result['summary']}\n"
            else:
                # Fallback to raw content (legacy support)
                for item in result.get('results', [])[:3]:
                    content = item.get('raw_content', item.get('content', 'N/A'))

                    #if len(content) > 1500:
                    #    content = content[:1500] + "..."

                    summary += f"- {content}\n"

            # Add clear separator between queries (asterisks)
            if idx < len(results):
                summary += "\n" + ("*" * 80) + "\n\n"

    return summary


def execute_research(queries: List[str], max_results: int = 3) -> List[Dict]:
    """
    Execute multiple research queries using Tavily.

    This is a convenience function that handles tool creation,
    query execution, and error handling.

    Args:
        queries: List of search query strings
        max_results: Number of results to retrieve per query (default: 3)

    Returns:
        List of research result dictionaries with structure:
        - query (str): The search query
        - results (list): Search results from Tavily
        - timestamp (str): ISO format timestamp
        - error (str, optional): Error message if search failed

    Example:
        >>> queries = ["AI in education", "machine learning applications"]
        >>> results = execute_research(queries, max_results=5)
    """
    search_tool = create_tavily_tool(max_results=max_results)
    results = []

    for query in queries:
        try:
            search_results = search_tool.invoke({"query": query})
            results.append({
                "query": query,
                "results": search_results,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            # Capture errors but continue with other queries
            results.append({
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    return results
