"""
Delivery router for Mail-Agent.

Routes replies to either SMTP sender or IMAP drafts based on configuration.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import Config
from .drafts_handler import DraftsHandler
from .mail_sender import MailSender
from .reply_generator import GeneratedReply


class DeliveryMode(Enum):
    """Delivery mode options."""
    SEND = "send"
    DRAFT = "draft"


@dataclass
class DeliveryResult:
    """Result of delivery operation."""
    
    success: bool
    mode: DeliveryMode
    message_id: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "mode": self.mode.value,
            "message_id": self.message_id,
            "error": self.error,
        }


class DeliveryRouter:
    """Route replies to appropriate delivery method."""

    def __init__(self, config: Config):
        """
        Initialize delivery router.

        Args:
            config: Configuration instance
        """
        self.config = config
        self._sender: Optional[MailSender] = None
        self._drafts_handler: Optional[DraftsHandler] = None

    @property
    def sender(self) -> MailSender:
        """Get or create mail sender."""
        if self._sender is None:
            self._sender = MailSender(self.config)
        return self._sender

    @property
    def drafts_handler(self) -> DraftsHandler:
        """Get or create drafts handler."""
        if self._drafts_handler is None:
            self._drafts_handler = DraftsHandler(self.config)
        return self._drafts_handler

    async def deliver(
        self,
        reply: GeneratedReply,
        mode: str,
    ) -> DeliveryResult:
        """
        Deliver a reply using the specified mode.

        Args:
            reply: Generated reply to deliver
            mode: Delivery mode ("send" or "draft")

        Returns:
            DeliveryResult
        """
        delivery_mode = DeliveryMode(mode.lower())
        
        try:
            if delivery_mode == DeliveryMode.SEND:
                message_id = await self.sender.send(reply)
            else:
                message_id = await self.drafts_handler.save_to_drafts(reply)
            
            return DeliveryResult(
                success=True,
                mode=delivery_mode,
                message_id=message_id,
            )
            
        except Exception as e:
            return DeliveryResult(
                success=False,
                mode=delivery_mode,
                error=str(e),
            )

    async def deliver_send(self, reply: GeneratedReply) -> DeliveryResult:
        """
        Deliver a reply via SMTP.

        Args:
            reply: Generated reply

        Returns:
            DeliveryResult
        """
        return await self.deliver(reply, "send")

    async def deliver_draft(self, reply: GeneratedReply) -> DeliveryResult:
        """
        Save a reply to drafts.

        Args:
            reply: Generated reply

        Returns:
            DeliveryResult
        """
        return await self.deliver(reply, "draft")


def deliver_reply(
    reply: GeneratedReply,
    mode: str,
    config: Config,
) -> DeliveryResult:
    """
    Convenience function to deliver a reply.

    Args:
        reply: Generated reply
        mode: Delivery mode
        config: Configuration

    Returns:
        DeliveryResult
    """
    router = DeliveryRouter(config)
    return asyncio.run(router.deliver(reply, mode))

