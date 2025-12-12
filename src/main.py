#!/usr/bin/env python3
"""
Mail-Agent: AI-powered automatic email reply agent for Postfix

This is the main entry point invoked by Postfix as a pipe transport.
It reads an email from stdin, matches it against rules, generates
an AI-powered reply, and either sends it or saves to drafts.

Usage:
    mail-agent [OPTIONS]

Options:
    --config PATH      Path to settings.yaml
    --rules PATH       Path to rules.yaml  
    --dry-run          Process but don't send/save
    --validate         Validate configuration and exit
    --test             Test mode - show what would happen
    --version          Show version and exit
    --help             Show this help

Exit codes:
    0   Success (email processed or no matching rule)
    1   Configuration error
    2   LLM/delivery error (email still delivered)
    75  Temporary failure (Postfix will retry)

Copyright (C) 2024 Viktor Zambo <mail-agent@zamboviktor.hu>
License: MIT
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import structlog

from . import __version__
from .config import Config, ConfigError, load_config
from .delivery import DeliveryRouter
from .email_parser import EmailParser
from .reply_generator import ReplyGenerator
from .rule_matcher import RuleMatcher


# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_PROCESSING_ERROR = 2
EXIT_TEMP_FAILURE = 75


def setup_logging(config: Config) -> structlog.BoundLogger:
    """
    Setup structured logging.

    Args:
        config: Configuration instance

    Returns:
        Configured logger
    """
    log_config = config.logging_config
    log_level = getattr(logging, log_config.get("level", "INFO").upper())
    log_file = log_config.get("file", "/var/log/mail-agent/mail-agent.log")
    
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup file handler
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr),
        ],
    )
    
    return structlog.get_logger("mail-agent")


async def process_email(
    config: Config,
    logger: structlog.BoundLogger,
    dry_run: bool = False,
    test_mode: bool = False,
) -> int:
    """
    Process an email from stdin.

    Args:
        config: Configuration instance
        logger: Logger instance
        dry_run: If True, don't actually send/save
        test_mode: If True, show detailed test output

    Returns:
        Exit code
    """
    # Parse email from stdin
    parser = EmailParser()
    
    try:
        email = parser.parse_from_stdin()
    except Exception as e:
        logger.error("Failed to parse email", error=str(e))
        return EXIT_TEMP_FAILURE
    
    logger.info(
        "Email received",
        from_address=email.from_address,
        to_addresses=email.to_addresses,
        subject=email.subject,
    )
    
    # Check if we should skip this email
    matcher = RuleMatcher(config)
    should_skip, skip_reason = matcher.should_skip(email)
    
    if should_skip:
        logger.info("Skipping email", reason=skip_reason)
        if test_mode:
            print(f"SKIP: {skip_reason}")
        return EXIT_SUCCESS
    
    # Match against rules
    rule = matcher.match(email)
    
    if not rule:
        logger.info("No matching rule found")
        if test_mode:
            print("NO MATCH: No rule matched this email")
        return EXIT_SUCCESS
    
    logger.info(
        "Rule matched",
        rule_name=rule.name,
        llm_provider=rule.llm_provider,
        delivery_mode=rule.delivery_mode,
    )
    
    if test_mode:
        print(f"MATCHED: {rule.name}")
        print(f"  Provider: {rule.llm_provider}")
        print(f"  Mode: {rule.delivery_mode}")
        print(f"  Prompt preview: {rule.system_prompt[:100]}...")
    
    # Generate reply
    generator = ReplyGenerator(config)
    
    try:
        reply = await generator.generate(email, rule)
    except Exception as e:
        logger.error("Failed to generate reply", error=str(e), rule=rule.name)
        return EXIT_PROCESSING_ERROR
    
    logger.info(
        "Reply generated",
        to_address=reply.to_address,
        subject=reply.subject,
    )
    
    if test_mode:
        print(f"\n--- Generated Reply ---")
        print(f"To: {reply.to_address}")
        print(f"Subject: {reply.subject}")
        print(f"\n{reply.body}")
        print(f"--- End Reply ---")
    
    if dry_run:
        logger.info("Dry run - not delivering")
        if test_mode:
            print(f"\nDRY RUN: Would {rule.delivery_mode} reply")
        return EXIT_SUCCESS
    
    # Deliver reply
    router = DeliveryRouter(config)
    result = await router.deliver(reply, rule.delivery_mode)
    
    if result.success:
        logger.info(
            "Reply delivered",
            mode=result.mode.value,
            message_id=result.message_id,
        )
        if test_mode:
            print(f"\nDELIVERED: {result.mode.value} (ID: {result.message_id})")
    else:
        logger.error(
            "Failed to deliver reply",
            mode=result.mode.value,
            error=result.error,
        )
        if test_mode:
            print(f"\nFAILED: {result.error}")
        return EXIT_PROCESSING_ERROR
    
    return EXIT_SUCCESS


def validate_config(config: Config) -> int:
    """
    Validate configuration and print results.

    Args:
        config: Configuration instance

    Returns:
        Exit code
    """
    errors = config.validate()
    
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return EXIT_CONFIG_ERROR
    
    print("Configuration is valid!")
    print(f"  Settings: {config.settings_path}")
    print(f"  Rules: {config.rules_path}")
    print(f"  Default LLM: {config.default_llm_provider}")
    print(f"  Default delivery: {config.default_delivery_mode}")
    print(f"  Rules defined: {len(config.get_rules())}")
    
    return EXIT_SUCCESS


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Mail-Agent: AI-powered automatic email reply agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--config",
        help="Path to settings.yaml",
        default=Config.DEFAULT_SETTINGS_PATH,
    )
    
    parser.add_argument(
        "--rules",
        help="Path to rules.yaml",
        default=Config.DEFAULT_RULES_PATH,
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process but don't send/save",
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit",
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - show detailed output",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"mail-agent {__version__}",
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(
            settings_path=args.config,
            rules_path=args.rules,
        )
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    
    # Handle validate mode
    if args.validate:
        return validate_config(config)
    
    # Setup logging
    logger = setup_logging(config)
    
    # Process email
    try:
        return asyncio.run(
            process_email(
                config=config,
                logger=logger,
                dry_run=args.dry_run,
                test_mode=args.test,
            )
        )
    except KeyboardInterrupt:
        logger.info("Interrupted")
        return EXIT_SUCCESS
    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        return EXIT_TEMP_FAILURE


if __name__ == "__main__":
    sys.exit(main())

