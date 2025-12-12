"""
OpenAI LLM provider.
"""

from typing import Optional

from openai import AsyncOpenAI

from .base import BaseLLMProvider, LLMError


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: dict):
        """
        Initialize OpenAI provider.

        Args:
            config: Provider configuration with api_key and model
        """
        super().__init__(config)
        
        api_key = config.get("api_key")
        if not api_key:
            raise LLMError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=self.timeout,
        )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4-turbo"

    async def generate_reply(
        self,
        email_content: str,
        system_prompt: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Generate a reply using OpenAI.

        Args:
            email_content: The email content to reply to
            system_prompt: System prompt with instructions
            subject: Optional email subject for context

        Returns:
            Generated reply text
        """
        try:
            user_message = self._build_user_message(email_content, subject)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise LLMError(f"OpenAI API error: {e}")

    def validate_config(self) -> list[str]:
        """Validate OpenAI configuration."""
        errors = []
        
        if not self.config.get("api_key"):
            errors.append("OpenAI API key is required")
        
        return errors

