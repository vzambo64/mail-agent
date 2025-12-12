"""
Google Gemini LLM provider.
"""

from typing import Optional

import google.generativeai as genai

from .base import BaseLLMProvider, LLMError


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider."""

    def __init__(self, config: dict):
        """
        Initialize Google Gemini provider.

        Args:
            config: Provider configuration with api_key and model
        """
        super().__init__(config)
        
        api_key = config.get("api_key")
        if not api_key:
            raise LLMError("Google API key is required")
        
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model)

    @property
    def name(self) -> str:
        return "google"

    @property
    def default_model(self) -> str:
        return "gemini-pro"

    async def generate_reply(
        self,
        email_content: str,
        system_prompt: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Generate a reply using Google Gemini.

        Args:
            email_content: The email content to reply to
            system_prompt: System prompt with instructions
            subject: Optional email subject for context

        Returns:
            Generated reply text
        """
        try:
            user_message = self._build_user_message(email_content, subject)
            
            # Combine system prompt and user message for Gemini
            full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"
            
            # Use generate_content_async for async operation
            response = await self.client.generate_content_async(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=0.7,
                ),
            )
            
            return response.text.strip()
            
        except Exception as e:
            raise LLMError(f"Google Gemini API error: {e}")

    def validate_config(self) -> list[str]:
        """Validate Google configuration."""
        errors = []
        
        if not self.config.get("api_key"):
            errors.append("Google API key is required")
        
        return errors

