"""
Reply generator for Mail-Agent.

Orchestrates LLM calls to generate email replies.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

from .config import Config
from .email_parser import ParsedEmail
from .llm import create_llm_provider, LLMError
from .rule_matcher import MatchedRule


@dataclass
class GeneratedReply:
    """Generated reply data."""
    
    subject: str
    body: str
    to_address: str
    from_address: str
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "to_address": self.to_address,
            "from_address": self.from_address,
            "body_preview": self.body[:200] if self.body else "",
        }


class ReplyGenerator:
    """Generate email replies using LLM."""

    def __init__(self, config: Config):
        """
        Initialize reply generator.

        Args:
            config: Configuration instance
        """
        self.config = config
        self._providers: dict = {}

    def _get_provider(self, provider_name: str):
        """
        Get or create LLM provider instance.

        Args:
            provider_name: Name of the LLM provider

        Returns:
            LLM provider instance
        """
        if provider_name not in self._providers:
            provider_config = self.config.get_llm_provider_config(provider_name)
            self._providers[provider_name] = create_llm_provider(
                provider_name,
                provider_config,
            )
        
        return self._providers[provider_name]

    async def generate(
        self,
        email: ParsedEmail,
        rule: MatchedRule,
    ) -> GeneratedReply:
        """
        Generate a reply to an email.

        Args:
            email: Parsed incoming email
            rule: Matched rule with LLM provider and prompt

        Returns:
            GeneratedReply instance
        """
        # Get LLM provider
        provider = self._get_provider(rule.llm_provider)

        # Generate reply content
        reply_body = await provider.generate_reply(
            email_content=email.body,
            system_prompt=rule.system_prompt,
            subject=email.subject,
        )

        # Build reply subject
        reply_subject = self._build_reply_subject(email.subject)

        # Get from address from config
        from_address = self.config.mail_config.get("from_address", "")
        
        # Build references for threading
        references = self._build_references(email)

        return GeneratedReply(
            subject=reply_subject,
            body=reply_body,
            to_address=email.reply_address,
            from_address=from_address,
            in_reply_to=email.message_id,
            references=references,
        )

    def _build_reply_subject(self, original_subject: str) -> str:
        """
        Build reply subject line.

        Args:
            original_subject: Original email subject

        Returns:
            Reply subject
        """
        # Check if already has Re: prefix
        subject = original_subject.strip()
        
        if not subject:
            return "Re: (no subject)"
        
        # Check for existing Re: prefix (case insensitive)
        if subject.lower().startswith("re:"):
            return subject
        
        return f"Re: {subject}"

    def _build_references(self, email: ParsedEmail) -> Optional[str]:
        """
        Build References header for email threading.

        Args:
            email: Original email

        Returns:
            References header value
        """
        references_parts = []
        
        # Add existing References
        existing_refs = email.headers.get("References", "")
        if existing_refs:
            references_parts.append(existing_refs)
        
        # Add Message-ID of the email we're replying to
        if email.message_id:
            references_parts.append(email.message_id)
        
        if references_parts:
            return " ".join(references_parts)
        
        return None


def generate_reply(
    email: ParsedEmail,
    rule: MatchedRule,
    config: Config,
) -> GeneratedReply:
    """
    Convenience function to generate a reply.

    Args:
        email: Parsed email
        rule: Matched rule
        config: Configuration

    Returns:
        GeneratedReply instance
    """
    generator = ReplyGenerator(config)
    return asyncio.run(generator.generate(email, rule))

