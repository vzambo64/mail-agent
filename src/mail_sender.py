"""
Mail sender for Mail-Agent.

Sends email replies via SMTP.
"""

import asyncio
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Optional

import aiosmtplib

from .config import Config
from .reply_generator import GeneratedReply


class MailSenderError(Exception):
    """Mail sending error."""
    pass


class MailSender:
    """Send emails via SMTP."""

    def __init__(self, config: Config):
        """
        Initialize mail sender.

        Args:
            config: Configuration instance
        """
        self.config = config
        mail_config = config.mail_config
        
        self.smtp_host = mail_config.get("smtp_host", "localhost")
        self.smtp_port = mail_config.get("smtp_port", 25)
        self.smtp_user = mail_config.get("smtp_user")
        self.smtp_password = mail_config.get("smtp_password")
        self.use_tls = mail_config.get("use_tls", False)
        self.use_starttls = mail_config.get("use_starttls", False)

    async def send(self, reply: GeneratedReply) -> str:
        """
        Send an email reply.

        Args:
            reply: Generated reply to send

        Returns:
            Message ID of sent email
        """
        # Build email message
        msg = self._build_message(reply)
        
        try:
            # Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=self.use_tls,
                start_tls=self.use_starttls,
            )
            
            return msg["Message-ID"]
            
        except aiosmtplib.SMTPException as e:
            raise MailSenderError(f"SMTP error: {e}")
        except Exception as e:
            raise MailSenderError(f"Failed to send email: {e}")

    def _build_message(self, reply: GeneratedReply) -> EmailMessage:
        """
        Build EmailMessage from GeneratedReply.

        Args:
            reply: Generated reply

        Returns:
            EmailMessage ready to send
        """
        msg = EmailMessage()
        
        # Set headers
        msg["From"] = reply.from_address
        msg["To"] = reply.to_address
        msg["Subject"] = reply.subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=self._get_domain(reply.from_address))
        
        # Threading headers
        if reply.in_reply_to:
            msg["In-Reply-To"] = reply.in_reply_to
        
        if reply.references:
            msg["References"] = reply.references
        
        # Mark as auto-generated
        msg["Auto-Submitted"] = "auto-replied"
        msg["X-Auto-Response-Suppress"] = "All"
        msg["X-Mailer"] = "Mail-Agent/1.0.0"
        
        # Set body
        msg.set_content(reply.body)
        
        return msg

    def _get_domain(self, email_address: str) -> str:
        """
        Extract domain from email address.

        Args:
            email_address: Email address

        Returns:
            Domain part of the address
        """
        if "@" in email_address:
            return email_address.split("@")[1]
        return "localhost"


def send_reply(reply: GeneratedReply, config: Config) -> str:
    """
    Convenience function to send a reply.

    Args:
        reply: Generated reply
        config: Configuration

    Returns:
        Message ID of sent email
    """
    sender = MailSender(config)
    return asyncio.run(sender.send(reply))

