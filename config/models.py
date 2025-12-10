"""
Model provider abstraction for multi-provider LLM support.

Supports OpenAI, Anthropic, and Google models with unified interface.
"""

import os
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


# Unified model registry for per-agent model selection
# Each entry contains display name and provider/model mapping
AVAILABLE_MODELS = [
    # OpenAI Models
    {"id": "gpt-5-nano", "display": "GPT-5 Nano (OpenAI)", "provider": "openai", "name": "gpt-5-nano"}, # $0.05/MTok
    {"id": "gpt-4o-mini", "display": "GPT-4o Mini (OpenAI)", "provider": "openai", "name": "gpt-4o-mini"},# $0.15/MTok
    {"id": "gpt-5-mini", "display": "GPT-5 Mini (OpenAI)", "provider": "openai", "name": "gpt-5-mini"},  # $0.25/MTok
    {"id": "gpt-5.1", "display": "GPT-5.1 (OpenAI)", "provider": "openai", "name": "gpt-4o-mini"},  # $1.25/MTok

    # Anthropic Models
    {"id": "claude-haiku-4.5", "display": "Claude 4.5 Haiku (Anthropic)", "provider": "anthropic", "name": "claude-haiku-4-5-20251001"}, # $1.00/MTok
    {"id": "claude-sonnet-4.5", "display": "Claude 4.5 Sonnet (Anthropic)", "provider": "anthropic", "name": "claude-sonnet-4-5-20250929"}, # $3.00/MTok
    {"id": "claude-opus-4.5", "display": "Claude 4.5 Opus (Anthropic)", "provider": "anthropic", "name": "claude-opus-4-5-20251101"},  # $15.00/MTok

    # Google Models
    {"id": "gemini-flash-2.5-lite", "display": "Gemini 2.5 Flash Lite (Google)", "provider": "google", "name": "gemini-2.5-flash-lite"}, # $0.10/MTok
    {"id": "gemini-flash-2.5", "display": "Gemini 2.5 Flash (Google)", "provider": "google", "name": "gemini-2.5-flash"}, # $0.30/MTok
    {"id": "gemini-pro-2.5", "display": "Gemini 2.5 Pro (Google)", "provider": "google", "name": "gemini-2.5-pro"}, # $1.25/MTok
]


def get_model_by_id(model_id: str) -> dict:
    """
    Get model configuration by its ID.

    Args:
        model_id: The model ID (e.g., "gpt-4o-mini")

    Returns:
        Model config dict with provider and name

    Raises:
        ValueError: If model_id not found
    """
    for model in AVAILABLE_MODELS:
        if model["id"] == model_id:
            return {"provider": model["provider"], "name": model["name"]}

    raise ValueError(f"Model ID '{model_id}' not found in AVAILABLE_MODELS")


def get_llm(provider: str, model: str):
    """
    Get LLM instance based on provider and model.

    Args:
        provider: One of "openai", "anthropic", "google"
        model: Model name from MODEL_CONFIGS

    Returns:
        Configured LLM instance (ChatOpenAI, ChatAnthropic, or ChatGoogleGenerativeAI)

    Raises:
        ValueError: If provider unknown or API key missing

    Example:
        >>> llm = get_llm("openai", "gpt-4o")
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
            google_api_key=api_key
        )

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported providers: openai, anthropic, google"
        )
