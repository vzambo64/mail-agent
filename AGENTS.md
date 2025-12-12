# AGENTS.md - Mail-Agent Development Guide

This document provides comprehensive information for AI agents and developers working on the Mail-Agent project.

## Project Overview

**Mail-Agent** is a Python-based Postfix mail filter that intercepts incoming emails, matches them against sender-based rules, generates AI-powered replies using configurable LLM providers (OpenAI, Anthropic, Google, Ollama), and either sends automatic responses or saves them to IMAP drafts folder for review.

- **Author**: Viktor Zambo
- **Contact**: mail-agent@zamboviktor.hu
- **Repository**: https://github.com/vzambo64/mail-agent
- **License**: MIT
- **Python Version**: 3.10+
- **Target OS**: Ubuntu 18.04+

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Postfix MTA                                     │
│  ┌─────────────┐                                        ┌─────────────────┐ │
│  │  Incoming   │                                        │    Outgoing     │ │
│  │    Mail     │                                        │      Mail       │ │
│  └──────┬──────┘                                        └────────▲────────┘ │
└─────────┼────────────────────────────────────────────────────────┼──────────┘
          │ pipe transport                                         │
          ▼                                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Mail-Agent Filter Service                          │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ Email Parser │───▶│ Rule Matcher │───▶│  AI Agent    │                  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                  │                          │
│                                                  ▼                          │
│                                          ┌──────────────┐                  │
│                                          │Delivery Mode │                  │
│                                          └──────┬───────┘                  │
│                                    ┌────────────┴────────────┐             │
│                                    ▼                         ▼             │
│                            ┌─────────────┐           ┌─────────────┐       │
│                            │ SMTP Sender │           │ IMAP Drafts │       │
│                            └──────┬──────┘           └──────┬──────┘       │
│                                   │                         │              │
└───────────────────────────────────┼─────────────────────────┼──────────────┘
                                    │                         │
                                    ▼                         ▼
                              ┌──────────┐             ┌──────────────┐
                              │ Postfix  │             │ Dovecot IMAP │
                              │  Queue   │             │   Drafts     │
                              └──────────┘             └──────────────┘
```

---

## Project Structure

```
mail-agent/
├── src/                          # Python source code
│   ├── __init__.py              # Package metadata
│   ├── main.py                  # Entry point (Postfix pipe)
│   ├── config.py                # Configuration loader
│   ├── email_parser.py          # Email parsing
│   ├── rule_matcher.py          # Rule matching engine
│   ├── reply_generator.py       # LLM orchestration
│   ├── delivery.py              # Delivery router
│   ├── mail_sender.py           # SMTP sending
│   ├── drafts_handler.py        # IMAP drafts
│   └── llm/                     # LLM providers
│       ├── __init__.py
│       ├── base.py              # Abstract base class
│       ├── factory.py           # Provider factory
│       ├── openai_provider.py   # OpenAI GPT
│       ├── anthropic_provider.py # Anthropic Claude
│       ├── google_provider.py   # Google Gemini
│       └── ollama_provider.py   # Ollama local
├── config/                      # Sample configurations
│   ├── settings.yaml.sample
│   ├── rules.yaml.sample
│   └── env.sample
├── scripts/                     # Installation scripts
│   ├── install.sh
│   └── uninstall.sh
├── debian/                      # Debian packaging
│   ├── control
│   ├── postinst
│   ├── prerm
│   ├── postrm
│   └── conffiles
├── postfix/                     # Postfix config samples
│   └── master.cf.sample
├── man/                         # Man pages
│   └── mail-agent.1
├── build-deb.sh                 # Build Debian package
├── requirements.txt             # Python dependencies
├── setup.py                     # Python setup
├── README.md                    # User documentation
├── AGENTS.md                    # This file
└── LICENSE                      # MIT License
```

---

## Core Components

### 1. Email Parser (`src/email_parser.py`)

Parses incoming emails from stdin (Postfix pipe).

**Key Classes:**

- `ParsedEmail` - Dataclass with parsed email fields
- `EmailParser` - Parser implementation

**Key Methods:**

- `parse_from_stdin()` - Read and parse from stdin
- `parse_from_string()` - Parse from raw string

### 2. Rule Matcher (`src/rule_matcher.py`)

Matches emails against configured rules.

**Key Classes:**

- `MatchedRule` - Matched rule data
- `RuleMatcher` - Matching engine

**Key Methods:**

- `match(email)` - Find first matching rule
- `match_all(email)` - Find all matching rules
- `should_skip(email)` - Check skip conditions

### 3. LLM Providers (`src/llm/`)

Abstract LLM interface with multiple implementations.

**Base Class:** `BaseLLMProvider`

- `generate_reply(email_content, system_prompt, subject)` - Generate reply

**Implementations:**

- `OpenAIProvider` - GPT-4, GPT-3.5
- `AnthropicProvider` - Claude models
- `GoogleProvider` - Gemini
- `OllamaProvider` - Local models

**Factory:** `create_llm_provider(name, config)`

### 4. Reply Generator (`src/reply_generator.py`)

Orchestrates LLM calls.

**Key Classes:**

- `GeneratedReply` - Generated reply data
- `ReplyGenerator` - Generation orchestration

### 5. Delivery Router (`src/delivery.py`)

Routes replies to SMTP or IMAP.

**Key Classes:**

- `DeliveryMode` - Enum (SEND, DRAFT)
- `DeliveryResult` - Delivery result data
- `DeliveryRouter` - Routing logic

### 6. Mail Sender (`src/mail_sender.py`)

Sends replies via SMTP.

**Key Classes:**

- `MailSender` - SMTP client wrapper

### 7. Drafts Handler (`src/drafts_handler.py`)

Saves replies to IMAP Drafts.

**Key Classes:**

- `DraftsHandler` - IMAP client wrapper

---

## Configuration

### Settings (`/etc/mail-agent/settings.yaml`)

```yaml
llm:
  default_provider: "openai"
  providers:
    openai:
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4-turbo"
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-sonnet-4-20250514"
    google:
      api_key: "${GOOGLE_API_KEY}"
      model: "gemini-pro"
    ollama:
      base_url: "http://localhost:11434"
      model: "llama3"

delivery:
  default_mode: "send" # or "draft"

mail:
  smtp_host: "localhost"
  smtp_port: 25
  from_address: "auto-reply@domain.com"

imap:
  host: "localhost"
  port: 993
  use_ssl: true
  username: "${IMAP_USERNAME}"
  password: "${IMAP_PASSWORD}"
  drafts_folder: "Drafts"
```

### Rules (`/etc/mail-agent/rules.yaml`)

```yaml
rules:
  - name: "Rule Name"
    sender_pattern: ".*@domain\\.com$" # Regex
    recipient_filter: "support@domain.com"
    llm_provider: "openai"
    delivery_mode: "send"
    priority: 100
    system_prompt: |
      Your system prompt here.
    enabled: true
```

---

## Development Guidelines

### Code Style

- **Python**: PEP 8 compliant
- **Type Hints**: Use type annotations
- **Docstrings**: Google style
- **Async**: Use async/await for I/O operations

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style
- `refactor` - Refactoring
- `test` - Tests
- `chore` - Maintenance

**Scopes:**

- `llm` - LLM providers
- `rules` - Rule matching
- `delivery` - Delivery routing
- `smtp` - SMTP sending
- `imap` - IMAP handling
- `config` - Configuration
- `install` - Installation
- `package` - Debian packaging
- `docs` - Documentation

**Examples:**

```
feat(llm): add support for Mistral AI provider
fix(imap): handle connection timeout gracefully
docs(readme): add troubleshooting section
```

### Testing

```bash
# Validate configuration
mail-agent --validate

# Test with sample email
echo "From: test@example.com..." | mail-agent --test

# Dry run (no sending)
cat email.eml | mail-agent --dry-run
```

### Building

```bash
# Build Debian package
./build-deb.sh

# Output: build/mail-agent_1.0.0_all.deb
```

---

## Future Development Roadmap

### v1.1.0 - Enhanced Features

- [ ] **feat(llm)**: Add Mistral AI provider
- [ ] **feat(llm)**: Add Azure OpenAI provider
- [ ] **feat(llm)**: Add AWS Bedrock provider
- [ ] **feat(rules)**: Content-based rule matching (analyze email body)
- [ ] **feat(rules)**: Subject pattern matching
- [ ] **feat(rules)**: Time-based rules (business hours only)
- [ ] **feat(rate-limit)**: Implement rate limiting per sender
- [ ] **feat(templates)**: Email template support with variables

### v1.2.0 - Advanced Features

- [ ] **feat(context)**: Knowledge base integration (RAG)
- [ ] **feat(context)**: Conversation history tracking
- [ ] **feat(context)**: Customer data lookup (CRM integration)
- [ ] **feat(queue)**: Approval queue with web UI
- [ ] **feat(metrics)**: Prometheus metrics endpoint
- [ ] **feat(webhooks)**: Webhook notifications

### v1.3.0 - Enterprise Features

- [ ] **feat(multi-tenant)**: Multi-tenant support
- [ ] **feat(auth)**: LDAP/AD integration for admin access
- [ ] **feat(audit)**: Audit logging
- [ ] **feat(compliance)**: GDPR compliance features
- [ ] **feat(backup)**: Configuration backup/restore

### v2.0.0 - Platform

- [ ] **feat(api)**: REST API for management
- [ ] **feat(ui)**: Web-based admin dashboard
- [ ] **feat(plugins)**: Plugin architecture
- [ ] **feat(cluster)**: Multi-node clustering

---

## Known Issues

1. **Google Gemini async**: The google-generativeai SDK has limited async support
2. **Rate limiting**: Not yet implemented in v1.0.0
3. **IMAP namespace**: Manual configuration needed for non-standard Dovecot namespaces

---

## Dependencies

| Package             | Version  | Purpose               |
| ------------------- | -------- | --------------------- |
| openai              | >=1.12.0 | OpenAI API client     |
| anthropic           | >=0.18.0 | Anthropic API client  |
| google-generativeai | >=0.4.0  | Google Gemini client  |
| ollama              | >=0.1.6  | Ollama client         |
| aiosmtplib          | >=3.0.0  | Async SMTP            |
| imapclient          | >=3.0.0  | IMAP client           |
| pyyaml              | >=6.0.1  | YAML parsing          |
| python-dotenv       | >=1.0.0  | Environment variables |
| structlog           | >=24.1.0 | Structured logging    |
| email-validator     | >=2.1.0  | Email validation      |
| tenacity            | >=8.2.3  | Retry logic           |
| aiofiles            | >=23.2.1 | Async file operations |

---

## Support

- **Email**: mail-agent@zamboviktor.hu
- **Issues**: https://github.com/vzambo64/mail-agent/issues
- **Documentation**: `man mail-agent`

---

## License

MIT License - Copyright (C) 2024 Viktor Zambo
