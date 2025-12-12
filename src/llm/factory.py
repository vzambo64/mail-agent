"""
LLM provider factory.
"""

from typing import Type

from .base import BaseLLMProvider, LLMError


# Provider registry
_PROVIDERS: dict[str, Type[BaseLLMProvider]] = {}


def _register_providers():
    """Register all available providers."""
    global _PROVIDERS
    
    # Import providers lazily to avoid import errors if dependencies missing
    try:
        from .openai_provider import OpenAIProvider
        _PROVIDERS["openai"] = OpenAIProvider
    except ImportError:
        pass
    
    try:
        from .anthropic_provider import AnthropicProvider
        _PROVIDERS["anthropic"] = AnthropicProvider
    except ImportError:
        pass
    
    try:
        from .google_provider import GoogleProvider
        _PROVIDERS["google"] = GoogleProvider
    except ImportError:
        pass
    
    try:
        from .ollama_provider import OllamaProvider
        _PROVIDERS["ollama"] = OllamaProvider
    except ImportError:
        pass


def get_available_providers() -> list[str]:
    """
    Get list of available LLM providers.

    Returns:
        List of provider names
    """
    if not _PROVIDERS:
        _register_providers()
    
    return list(_PROVIDERS.keys())


def create_llm_provider(name: str, config: dict) -> BaseLLMProvider:
    """
    Create an LLM provider instance.

    Args:
        name: Provider name (openai, anthropic, google, ollama)
        config: Provider configuration

    Returns:
        LLM provider instance

    Raises:
        LLMError: If provider is not available or configuration is invalid
    """
    if not _PROVIDERS:
        _register_providers()
    
    name = name.lower()
    
    if name not in _PROVIDERS:
        available = ", ".join(get_available_providers())
        raise LLMError(
            f"Unknown LLM provider: {name}. "
            f"Available providers: {available}"
        )
    
    provider_class = _PROVIDERS[name]
    
    try:
        return provider_class(config)
    except Exception as e:
        raise LLMError(f"Failed to initialize {name} provider: {e}")

