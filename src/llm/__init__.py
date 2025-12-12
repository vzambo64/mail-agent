"""
LLM providers for Mail-Agent.

Supports multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Ollama (Local models)
"""

from .base import BaseLLMProvider, LLMError
from .factory import create_llm_provider, get_available_providers

__all__ = [
    "BaseLLMProvider",
    "LLMError",
    "create_llm_provider",
    "get_available_providers",
]

