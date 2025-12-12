"""
Base LLM provider interface.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMError(Exception):
    """LLM provider error."""
    pass


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: dict):
        """
        Initialize LLM provider.

        Args:
            config: Provider configuration dict
        """
        self.config = config
        self.model = config.get("model", self.default_model)
        self.timeout = config.get("timeout", 60)
        self.max_tokens = config.get("max_tokens", 1024)

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model name."""
        pass

    @abstractmethod
    async def generate_reply(
        self,
        email_content: str,
        system_prompt: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Generate a reply to an email.

        Args:
            email_content: The email content to reply to
            system_prompt: System prompt with instructions
            subject: Optional email subject for context

        Returns:
            Generated reply text
        """
        pass

    def _build_user_message(
        self,
        email_content: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Build the user message for the LLM.

        Args:
            email_content: The email content
            subject: Optional email subject

        Returns:
            Formatted user message
        """
        parts = []

        if subject:
            parts.append(f"Subject: {subject}")
            parts.append("")

        parts.append("Email content:")
        parts.append(email_content)
        parts.append("")
        parts.append("Please write a reply to this email.")

        return "\n".join(parts)

    def validate_config(self) -> list[str]:
        """
        Validate provider configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        return []

