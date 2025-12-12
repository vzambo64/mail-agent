"""
Configuration loader for Mail-Agent.

Loads settings from YAML files and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    """Configuration error."""
    pass


class Config:
    """Configuration manager for Mail-Agent."""

    DEFAULT_SETTINGS_PATH = "/etc/mail-agent/settings.yaml"
    DEFAULT_RULES_PATH = "/etc/mail-agent/rules.yaml"
    DEFAULT_ENV_PATH = "/etc/mail-agent/.env"

    def __init__(
        self,
        settings_path: Optional[str] = None,
        rules_path: Optional[str] = None,
        env_path: Optional[str] = None,
    ):
        """
        Initialize configuration.

        Args:
            settings_path: Path to settings.yaml
            rules_path: Path to rules.yaml
            env_path: Path to .env file
        """
        self.settings_path = Path(settings_path or self.DEFAULT_SETTINGS_PATH)
        self.rules_path = Path(rules_path or self.DEFAULT_RULES_PATH)
        self.env_path = Path(env_path or self.DEFAULT_ENV_PATH)

        # Load environment variables
        if self.env_path.exists():
            load_dotenv(self.env_path)

        # Load configuration files
        self.settings = self._load_yaml(self.settings_path)
        self.rules = self._load_yaml(self.rules_path)

        # Expand environment variables in settings
        self.settings = self._expand_env_vars(self.settings)

    def _load_yaml(self, path: Path) -> dict:
        """Load YAML file."""
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {path}: {e}")

    def _expand_env_vars(self, obj: Any) -> Any:
        """Recursively expand environment variables in configuration."""
        if isinstance(obj, str):
            # Match ${VAR_NAME} pattern
            pattern = r"\$\{([^}]+)\}"
            matches = re.findall(pattern, obj)
            for var_name in matches:
                env_value = os.environ.get(var_name, "")
                obj = obj.replace(f"${{{var_name}}}", env_value)
            return obj
        elif isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        return obj

    @property
    def llm_config(self) -> dict:
        """Get LLM configuration."""
        return self.settings.get("llm", {})

    @property
    def default_llm_provider(self) -> str:
        """Get default LLM provider name."""
        return self.llm_config.get("default_provider", "openai")

    def get_llm_provider_config(self, provider: str) -> dict:
        """Get configuration for a specific LLM provider."""
        providers = self.llm_config.get("providers", {})
        if provider not in providers:
            raise ConfigError(f"LLM provider not configured: {provider}")
        return providers[provider]

    @property
    def mail_config(self) -> dict:
        """Get mail (SMTP) configuration."""
        return self.settings.get("mail", {})

    @property
    def imap_config(self) -> dict:
        """Get IMAP configuration."""
        return self.settings.get("imap", {})

    @property
    def delivery_config(self) -> dict:
        """Get delivery configuration."""
        return self.settings.get("delivery", {})

    @property
    def default_delivery_mode(self) -> str:
        """Get default delivery mode (send or draft)."""
        return self.delivery_config.get("default_mode", "send")

    @property
    def rate_limiting_config(self) -> dict:
        """Get rate limiting configuration."""
        return self.settings.get("rate_limiting", {})

    @property
    def logging_config(self) -> dict:
        """Get logging configuration."""
        return self.settings.get("logging", {})

    def get_rules(self) -> list:
        """Get list of auto-reply rules."""
        rules = self.rules.get("rules", [])
        # Filter enabled rules and sort by priority
        enabled_rules = [r for r in rules if r.get("enabled", True)]
        return sorted(enabled_rules, key=lambda r: r.get("priority", 0), reverse=True)

    def validate(self) -> list[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check LLM configuration
        if not self.llm_config:
            errors.append("No LLM configuration found")
        else:
            default_provider = self.default_llm_provider
            providers = self.llm_config.get("providers", {})
            if default_provider not in providers:
                errors.append(f"Default LLM provider '{default_provider}' not configured")

        # Check mail configuration
        if not self.mail_config:
            errors.append("No mail (SMTP) configuration found")
        elif not self.mail_config.get("from_address"):
            errors.append("mail.from_address is required")

        # Check IMAP configuration if draft mode is used
        if self.default_delivery_mode == "draft":
            if not self.imap_config:
                errors.append("IMAP configuration required for draft delivery mode")

        # Check rules
        rules = self.rules.get("rules", [])
        if not rules:
            errors.append("No auto-reply rules defined")

        for i, rule in enumerate(rules):
            if not rule.get("name"):
                errors.append(f"Rule {i}: name is required")
            if not rule.get("sender_pattern"):
                errors.append(f"Rule {i}: sender_pattern is required")
            if not rule.get("system_prompt"):
                errors.append(f"Rule {i}: system_prompt is required")

        return errors


def load_config(
    settings_path: Optional[str] = None,
    rules_path: Optional[str] = None,
    env_path: Optional[str] = None,
) -> Config:
    """
    Load and return configuration.

    Args:
        settings_path: Path to settings.yaml
        rules_path: Path to rules.yaml
        env_path: Path to .env file

    Returns:
        Config instance
    """
    return Config(settings_path, rules_path, env_path)

