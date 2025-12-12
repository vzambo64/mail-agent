"""
Drafts handler for Mail-Agent.

Saves email replies to IMAP Drafts folder for review.
"""

import asyncio
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Optional

from imapclient import IMAPClient

from .config import Config
from .reply_generator import GeneratedReply


class DraftsHandlerError(Exception):
    """Drafts handler error."""
    pass


class DraftsHandler:
    """Save emails to IMAP Drafts folder."""

    def __init__(self, config: Config):
        """
        Initialize drafts handler.

        Args:
            config: Configuration instance
        """
        self.config = config
        imap_config = config.imap_config
        
        self.host = imap_config.get("host", "localhost")
        self.port = imap_config.get("port", 993)
        self.use_ssl = imap_config.get("use_ssl", True)
        self.username = imap_config.get("username", "")
        self.password = imap_config.get("password", "")
        self.drafts_folder = imap_config.get("drafts_folder", "Drafts")

    async def save_to_drafts(self, reply: GeneratedReply) -> str:
        """
        Save a reply to the Drafts folder.

        Args:
            reply: Generated reply to save

        Returns:
            Message ID of saved draft
        """
        # Build email message
        msg = self._build_message(reply)
        
        # Run IMAP operations in thread pool (imapclient is synchronous)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._save_message_sync,
            msg,
        )
        
        return result

    def _save_message_sync(self, msg: EmailMessage) -> str:
        """
        Synchronous IMAP save operation.

        Args:
            msg: Email message to save

        Returns:
            Message ID
        """
        try:
            # Connect to IMAP server
            client = IMAPClient(
                self.host,
                port=self.port,
                ssl=self.use_ssl,
            )
            
            try:
                # Login
                client.login(self.username, self.password)
                
                # Ensure Drafts folder exists
                self._ensure_folder_exists(client, self.drafts_folder)
                
                # Append message to Drafts with \Draft flag
                msg_bytes = msg.as_bytes()
                client.append(
                    self.drafts_folder,
                    msg_bytes,
                    flags=["\\Draft", "\\Seen"],
                )
                
                return msg["Message-ID"]
                
            finally:
                client.logout()
                
        except Exception as e:
            raise DraftsHandlerError(f"IMAP error: {e}")

    def _ensure_folder_exists(self, client: IMAPClient, folder: str) -> None:
        """
        Ensure IMAP folder exists, create if needed.

        Args:
            client: IMAP client
            folder: Folder name
        """
        folders = client.list_folders()
        folder_names = [f[2] for f in folders]  # f[2] is the folder name
        
        if folder not in folder_names:
            try:
                client.create_folder(folder)
            except Exception:
                # Folder might already exist or we don't have permission
                pass

    def _build_message(self, reply: GeneratedReply) -> EmailMessage:
        """
        Build EmailMessage from GeneratedReply.

        Args:
            reply: Generated reply

        Returns:
            EmailMessage ready to save
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
        
        # Mark as auto-generated draft
        msg["X-Mailer"] = "Mail-Agent/1.0.0"
        msg["X-Mail-Agent-Draft"] = "pending-review"
        
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

    def verify_connection(self) -> tuple[bool, Optional[str]]:
        """
        Verify IMAP connection and credentials.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            client = IMAPClient(
                self.host,
                port=self.port,
                ssl=self.use_ssl,
            )
            
            try:
                client.login(self.username, self.password)
                
                # Check if Drafts folder exists
                folders = client.list_folders()
                folder_names = [f[2] for f in folders]
                
                if self.drafts_folder not in folder_names:
                    return (True, f"Warning: Drafts folder '{self.drafts_folder}' not found")
                
                return (True, None)
                
            finally:
                client.logout()
                
        except Exception as e:
            return (False, str(e))


def save_to_drafts(reply: GeneratedReply, config: Config) -> str:
    """
    Convenience function to save a reply to drafts.

    Args:
        reply: Generated reply
        config: Configuration

    Returns:
        Message ID of saved draft
    """
    handler = DraftsHandler(config)
    return asyncio.run(handler.save_to_drafts(reply))

