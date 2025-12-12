"""
Rule matcher for Mail-Agent.

Matches incoming emails against configured rules.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .config import Config
from .email_parser import ParsedEmail


@dataclass
class MatchedRule:
    """A rule that matched an email."""

    name: str
    sender_pattern: str
    llm_provider: str
    delivery_mode: str
    system_prompt: str
    priority: int
    recipient_filter: Optional[str] = None
    headers_match: Optional[dict] = None

    @classmethod
    def from_dict(cls, rule: dict, default_provider: str, default_mode: str) -> "MatchedRule":
        """Create MatchedRule from rule dictionary."""
        return cls(
            name=rule.get("name", "Unnamed Rule"),
            sender_pattern=rule.get("sender_pattern", ".*"),
            llm_provider=rule.get("llm_provider", default_provider),
            delivery_mode=rule.get("delivery_mode", default_mode),
            system_prompt=rule.get("system_prompt", ""),
            priority=rule.get("priority", 0),
            recipient_filter=rule.get("recipient_filter"),
            headers_match=rule.get("headers_match"),
        )


class RuleMatcher:
    """Match emails against configured rules."""

    def __init__(self, config: Config):
        """
        Initialize rule matcher.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.rules = config.get_rules()
        self.default_provider = config.default_llm_provider
        self.default_mode = config.default_delivery_mode

    def match(self, email: ParsedEmail) -> Optional[MatchedRule]:
        """
        Find the first matching rule for an email.

        Args:
            email: Parsed email

        Returns:
            MatchedRule if a rule matches, None otherwise
        """
        for rule in self.rules:
            if self._matches_rule(email, rule):
                # Check if this is a skip rule
                if rule.get("action") == "skip":
                    return None

                return MatchedRule.from_dict(
                    rule,
                    self.default_provider,
                    self.default_mode,
                )

        return None

    def match_all(self, email: ParsedEmail) -> list[MatchedRule]:
        """
        Find all matching rules for an email.

        Args:
            email: Parsed email

        Returns:
            List of MatchedRule instances
        """
        matched = []
        for rule in self.rules:
            if self._matches_rule(email, rule):
                if rule.get("action") != "skip":
                    matched.append(MatchedRule.from_dict(
                        rule,
                        self.default_provider,
                        self.default_mode,
                    ))
        return matched

    def _matches_rule(self, email: ParsedEmail, rule: dict) -> bool:
        """
        Check if an email matches a rule.

        Args:
            email: Parsed email
            rule: Rule dictionary

        Returns:
            True if email matches the rule
        """
        # Check if rule is enabled
        if not rule.get("enabled", True):
            return False

        # Check sender pattern
        sender_pattern = rule.get("sender_pattern", ".*")
        if not self._matches_pattern(email.from_address, sender_pattern):
            return False

        # Check recipient filter (if specified)
        recipient_filter = rule.get("recipient_filter")
        if recipient_filter:
            if not self._matches_any_recipient(email, recipient_filter):
                return False

        # Check header matches (if specified)
        headers_match = rule.get("headers_match")
        if headers_match:
            if not self._matches_headers(email.headers, headers_match):
                return False

        return True

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """
        Check if value matches regex pattern.

        Args:
            value: String to match
            pattern: Regex pattern

        Returns:
            True if value matches pattern
        """
        try:
            return bool(re.match(pattern, value, re.IGNORECASE))
        except re.error:
            # Invalid regex, treat as literal match
            return pattern.lower() in value.lower()

    def _matches_any_recipient(self, email: ParsedEmail, filter_pattern: str) -> bool:
        """
        Check if any recipient matches the filter.

        Args:
            email: Parsed email
            filter_pattern: Regex pattern for recipient

        Returns:
            True if any recipient matches
        """
        all_recipients = email.to_addresses + email.cc_addresses

        for recipient in all_recipients:
            if self._matches_pattern(recipient, filter_pattern):
                return True

        return False

    def _matches_headers(self, headers: dict, header_patterns: dict) -> bool:
        """
        Check if email headers match the specified patterns.

        Args:
            headers: Email headers dict
            header_patterns: Dict of header name -> pattern

        Returns:
            True if all header patterns match
        """
        for header_name, pattern in header_patterns.items():
            header_value = headers.get(header_name, "")
            if not self._matches_pattern(header_value, pattern):
                return False

        return True

    def should_skip(self, email: ParsedEmail) -> tuple[bool, Optional[str]]:
        """
        Check if email should be skipped (not replied to).

        Args:
            email: Parsed email

        Returns:
            Tuple of (should_skip, reason)
        """
        # Check for common no-reply patterns
        no_reply_patterns = [
            r"^(no-?reply|noreply|mailer-daemon|postmaster)@",
            r"^bounce[s]?@",
            r"^auto[-_]?reply@",
        ]

        for pattern in no_reply_patterns:
            if re.match(pattern, email.from_address, re.IGNORECASE):
                return (True, f"Sender matches no-reply pattern: {pattern}")

        # Check for mailing list headers
        mailing_list_headers = ["List-Unsubscribe", "List-Id", "Mailing-List"]
        for header in mailing_list_headers:
            if header in email.headers:
                return (True, f"Email has mailing list header: {header}")

        # Check for auto-submitted header
        auto_submitted = email.headers.get("Auto-Submitted", "").lower()
        if auto_submitted and auto_submitted != "no":
            return (True, f"Auto-Submitted header: {auto_submitted}")

        # Check for precedence header
        precedence = email.headers.get("Precedence", "").lower()
        if precedence in ["bulk", "junk", "list"]:
            return (True, f"Precedence header: {precedence}")

        return (False, None)


def match_email(email: ParsedEmail, config: Config) -> Optional[MatchedRule]:
    """
    Convenience function to match an email against rules.

    Args:
        email: Parsed email
        config: Configuration

    Returns:
        MatchedRule if matched, None otherwise
    """
    matcher = RuleMatcher(config)
    return matcher.match(email)

