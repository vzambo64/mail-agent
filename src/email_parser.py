"""
Email parser for Mail-Agent.

Parses incoming emails from stdin or file.
"""

import email
import email.policy
import sys
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Optional


@dataclass
class ParsedEmail:
    """Parsed email data structure."""

    message_id: str
    from_address: str
    from_name: str
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str
    body_text: str
    body_html: str
    headers: dict[str, str]
    raw_message: EmailMessage
    reply_to: Optional[str] = None
    date: Optional[str] = None
    attachments: list[dict] = field(default_factory=list)

    @property
    def reply_address(self) -> str:
        """Get the address to reply to."""
        return self.reply_to or self.from_address

    @property
    def body(self) -> str:
        """Get the best available body (prefer text over HTML)."""
        return self.body_text or self.body_html

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "message_id": self.message_id,
            "from_address": self.from_address,
            "from_name": self.from_name,
            "to_addresses": self.to_addresses,
            "subject": self.subject,
            "body_preview": self.body[:200] if self.body else "",
            "has_attachments": len(self.attachments) > 0,
        }


class EmailParser:
    """Parse email messages."""

    def __init__(self):
        """Initialize email parser."""
        self.policy = email.policy.default

    def parse_from_stdin(self) -> ParsedEmail:
        """
        Parse email from standard input.

        Returns:
            ParsedEmail instance
        """
        raw_email = sys.stdin.read()
        return self.parse_from_string(raw_email)

    def parse_from_file(self, path: str) -> ParsedEmail:
        """
        Parse email from file.

        Args:
            path: Path to email file

        Returns:
            ParsedEmail instance
        """
        with open(path, "r") as f:
            raw_email = f.read()
        return self.parse_from_string(raw_email)

    def parse_from_string(self, raw_email: str) -> ParsedEmail:
        """
        Parse email from string.

        Args:
            raw_email: Raw email string

        Returns:
            ParsedEmail instance
        """
        msg = email.message_from_string(raw_email, policy=self.policy)
        return self._parse_message(msg)

    def parse_from_bytes(self, raw_email: bytes) -> ParsedEmail:
        """
        Parse email from bytes.

        Args:
            raw_email: Raw email bytes

        Returns:
            ParsedEmail instance
        """
        msg = email.message_from_bytes(raw_email, policy=self.policy)
        return self._parse_message(msg)

    def _parse_message(self, msg: EmailMessage) -> ParsedEmail:
        """
        Parse EmailMessage into ParsedEmail.

        Args:
            msg: EmailMessage instance

        Returns:
            ParsedEmail instance
        """
        # Extract from address and name
        from_header = msg.get("From", "")
        from_address, from_name = self._parse_address(from_header)

        # Extract to addresses
        to_header = msg.get("To", "")
        to_addresses = self._parse_address_list(to_header)

        # Extract CC addresses
        cc_header = msg.get("Cc", "")
        cc_addresses = self._parse_address_list(cc_header)

        # Extract reply-to
        reply_to_header = msg.get("Reply-To", "")
        reply_to = self._parse_address(reply_to_header)[0] if reply_to_header else None

        # Extract body
        body_text, body_html = self._extract_body(msg)

        # Extract attachments info
        attachments = self._extract_attachments(msg)

        # Extract all headers
        headers = {key: str(value) for key, value in msg.items()}

        return ParsedEmail(
            message_id=msg.get("Message-ID", ""),
            from_address=from_address,
            from_name=from_name,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            subject=msg.get("Subject", ""),
            body_text=body_text,
            body_html=body_html,
            headers=headers,
            raw_message=msg,
            reply_to=reply_to,
            date=msg.get("Date", ""),
            attachments=attachments,
        )

    def _parse_address(self, address_str: str) -> tuple[str, str]:
        """
        Parse email address string into (address, name).

        Args:
            address_str: Email address string (e.g., "John Doe <john@example.com>")

        Returns:
            Tuple of (email_address, display_name)
        """
        if not address_str:
            return ("", "")

        # Try to parse structured address
        try:
            from email.utils import parseaddr
            name, addr = parseaddr(address_str)
            return (addr.strip(), name.strip())
        except Exception:
            # Fallback: just return the string as address
            return (address_str.strip(), "")

    def _parse_address_list(self, addresses_str: str) -> list[str]:
        """
        Parse comma-separated email addresses.

        Args:
            addresses_str: Comma-separated email addresses

        Returns:
            List of email addresses
        """
        if not addresses_str:
            return []

        from email.utils import getaddresses
        parsed = getaddresses([addresses_str])
        return [addr for name, addr in parsed if addr]

    def _extract_body(self, msg: EmailMessage) -> tuple[str, str]:
        """
        Extract text and HTML body from message.

        Args:
            msg: EmailMessage instance

        Returns:
            Tuple of (text_body, html_body)
        """
        text_body = ""
        html_body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain" and not text_body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text_body = payload.decode(charset, errors="replace")

                elif content_type == "text/html" and not html_body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_body = payload.decode(charset, errors="replace")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)

            if payload:
                charset = msg.get_content_charset() or "utf-8"
                content = payload.decode(charset, errors="replace")

                if content_type == "text/html":
                    html_body = content
                else:
                    text_body = content

        return (text_body.strip(), html_body.strip())

    def _extract_attachments(self, msg: EmailMessage) -> list[dict]:
        """
        Extract attachment information.

        Args:
            msg: EmailMessage instance

        Returns:
            List of attachment info dicts
        """
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    filename = part.get_filename() or "unnamed"
                    content_type = part.get_content_type()
                    size = len(part.get_payload(decode=True) or b"")

                    attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": size,
                    })

        return attachments


def parse_email_from_stdin() -> ParsedEmail:
    """
    Convenience function to parse email from stdin.

    Returns:
        ParsedEmail instance
    """
    parser = EmailParser()
    return parser.parse_from_stdin()

