"""
Ollama local LLM provider.
"""

from typing import Optional

import ollama

from .base import BaseLLMProvider, LLMError


class OllamaProvider(BaseLLMProvider):
    """Ollama local models provider."""

    def __init__(self, config: dict):
        """
        Initialize Ollama provider.

        Args:
            config: Provider configuration with base_url and model
        """
        super().__init__(config)
        
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.client = ollama.AsyncClient(host=self.base_url)

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return "llama3"

    async def generate_reply(
        self,
        email_content: str,
        system_prompt: str,
        subject: Optional[str] = None,
    ) -> str:
        """
        Generate a reply using Ollama.

        Args:
            email_content: The email content to reply to
            system_prompt: System prompt with instructions
            subject: Optional email subject for context

        Returns:
            Generated reply text
        """
        try:
            user_message = self._build_user_message(email_content, subject)
            
            response = await self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                options={
                    "num_predict": self.max_tokens,
                    "temperature": 0.7,
                },
            )
            
            return response["message"]["content"].strip()
            
        except Exception as e:
            raise LLMError(f"Ollama API error: {e}")

    def validate_config(self) -> list[str]:
        """Validate Ollama configuration."""
        errors = []
        
        # Ollama doesn't require API keys, just needs the server running
        if not self.config.get("base_url"):
            # Not an error, will use default
            pass
        
        return errors

