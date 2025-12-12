"""
Anthropic Claude LLM provider.
"""

from typing import Optional

from anthropic import AsyncAnthropic

from .base import BaseLLMProvider, LLMError


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: dict):
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration with api_key and model
        """
        super().__init__(config)
        
        api_key = config.get("api_key")
        if not api_key:
            raise LLMError("Anthropic API key is required")
        
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=self.timeout,
        )

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    async def generate_reply(
        self,
        email_content: str,
        system_prompt: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Generate a reply using Anthropic Claude.

        Args:
            email_content: The email content to reply to
            system_prompt: System prompt with instructions
            subject: Optional email subject for context

        Returns:
            Generated reply text
        """
        try:
            user_message = self._build_user_message(email_content, subject)
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message},
                ],
            )
            
            # Extract text from response
            text_blocks = [
                block.text for block in response.content
                if hasattr(block, 'text')
            ]
            
            return "\n".join(text_blocks).strip()
            
        except Exception as e:
            raise LLMError(f"Anthropic API error: {e}")

    def validate_config(self) -> list[str]:
        """Validate Anthropic configuration."""
        errors = []
        
        if not self.config.get("api_key"):
            errors.append("Anthropic API key is required")
        
        return errors

