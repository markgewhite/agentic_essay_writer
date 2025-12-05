"""
Model provider abstraction for multi-provider LLM support.

Supports OpenAI, Anthropic, and Google models with unified interface.
"""

import os
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


# Model configurations for each provider
MODEL_CONFIGS = {
    "openai": {
        "models": ["gpt-4o", "gpt-4o-mini"],
        "default_index": 0
    },
    "anthropic": {
        "models": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
        "default_index": 0
    },
    "google": {
        "models": ["gemini-1.5-pro", "gemini-1.5-flash"],
        "default_index": 0
    }
}


def get_llm(provider: str, model: str, temperature: float = 0.7):
    """
    Get LLM instance based on provider and model.

    Args:
        provider: One of "openai", "anthropic", "google"
        model: Model name from MODEL_CONFIGS
        temperature: Temperature setting (0.0 to 1.0)

    Returns:
        Configured LLM instance (ChatOpenAI, ChatAnthropic, or ChatGoogleGenerativeAI)

    Raises:
        ValueError: If provider unknown or API key missing

    Example:
        >>> llm = get_llm("openai", "gpt-4o", temperature=0.7)
        >>> response = llm.invoke([{"role": "user", "content": "Hello"}])
    """
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please set it in your .env file."
            )
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Please set it in your .env file."
            )
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=api_key
        )

    elif provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment. "
                "Please set it in your .env file."
            )
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key
        )

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported providers: {list(MODEL_CONFIGS.keys())}"
        )
