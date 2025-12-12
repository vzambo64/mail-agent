# Mail-Agent

**AI-powered automatic email reply agent for Postfix**

Mail-Agent is a Postfix mail filter that intercepts incoming emails, matches them against configurable sender-based rules, and generates intelligent automatic replies using various LLM providers.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Ubuntu](https://img.shields.io/badge/ubuntu-18.04%2B-orange.svg)

## Features

- **Multiple LLM Providers**: OpenAI (GPT-4), Anthropic (Claude), Google (Gemini), Ollama (local)
- **Flexible Rule Matching**: Regex patterns for sender, recipient, and header matching
- **Delivery Modes**: Send immediately or save to IMAP Drafts for review
- **Custom Prompts**: Per-rule system prompts for different response styles
- **Ubuntu 18.04+**: Compatible with Ubuntu 18.04, 20.04, 22.04, and 24.04
- **Debian Package**: Easy installation with automatic dependency management

## Quick Start

### Installation via .deb Package (Recommended)

```bash
# Download the package
wget https://github.com/vzambo64/mail-agent/releases/latest/download/mail-agent_1.0.0_all.deb

# Install with apt (handles all dependencies automatically)
sudo apt install ./mail-agent_1.0.0_all.deb
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/vzambo64/mail-agent.git
cd mail-agent

# Run the install script
sudo ./scripts/install.sh
```

## Configuration

### Main Settings (`/etc/mail-agent/settings.yaml`)

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

delivery:
  default_mode: "send"  # or "draft"

mail:
  smtp_host: "localhost"
  smtp_port: 25
  from_address: "auto-reply@yourdomain.com"

imap:
  host: "localhost"
  port: 993
  use_ssl: true
  username: "${IMAP_USERNAME}"
  password: "${IMAP_PASSWORD}"
  drafts_folder: "Drafts"
```

### Auto-Reply Rules (`/etc/mail-agent/rules.yaml`)

```yaml
rules:
  - name: "Customer Support"
    sender_pattern: ".*"
    recipient_filter: "support@yourdomain.com"
    llm_provider: "anthropic"
    delivery_mode: "send"
    system_prompt: |
      You are a helpful customer support assistant.
      Be friendly, professional, and concise.
    enabled: true

  - name: "Sales Inquiries"
    sender_pattern: ".*"
    recipient_filter: "sales@yourdomain.com"
    llm_provider: "openai"
    delivery_mode: "draft"  # Review before sending
    system_prompt: |
      You are a sales assistant.
      Focus on understanding customer needs.
    enabled: true
```

### API Keys (`/etc/mail-agent/.env`)

```bash
OPENAI_API_KEY=sk-your-api-key
ANTHROPIC_API_KEY=sk-ant-your-api-key
GOOGLE_API_KEY=your-google-api-key
IMAP_USERNAME=auto-reply@yourdomain.com
IMAP_PASSWORD=your-imap-password
```

## Postfix Integration

### Add Recipients to Filter

Edit `/etc/postfix/transport_mail_agent`:

```
support@yourdomain.com    mail-agent:
sales@yourdomain.com      mail-agent:
```

Apply changes:

```bash
sudo postmap /etc/postfix/transport_mail_agent
sudo systemctl reload postfix
```

## Usage

### Test Configuration

```bash
mail-agent --validate
```

### Test with Sample Email

```bash
echo "From: test@example.com
To: support@yourdomain.com
Subject: Test inquiry

Hello, I need help with your product." | mail-agent --test
```

### View Logs

```bash
tail -f /var/log/mail-agent/mail-agent.log
```

## LLM Providers

| Provider | Models | API Key Required |
|----------|--------|------------------|
| **OpenAI** | GPT-4, GPT-3.5-turbo | Yes (`OPENAI_API_KEY`) |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 | Yes (`ANTHROPIC_API_KEY`) |
| **Google** | Gemini Pro | Yes (`GOOGLE_API_KEY`) |
| **Ollama** | Llama 3, Mistral, etc. | No (local) |

### Using Ollama (Local LLM)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3

# Update settings.yaml
llm:
  default_provider: "ollama"
  providers:
    ollama:
      base_url: "http://localhost:11434"
      model: "llama3"
```

## Delivery Modes

| Mode | Behavior |
|------|----------|
| `send` | Reply is sent immediately via SMTP |
| `draft` | Reply is saved to IMAP Drafts folder for review |

## Ubuntu Compatibility

| Ubuntu Version | Python | Notes |
|----------------|--------|-------|
| 18.04 (Bionic) | 3.10 via deadsnakes | Automatic installation |
| 20.04 (Focal) | 3.10 via deadsnakes | Automatic installation |
| 22.04 (Jammy) | 3.10 (system) | Native support |
| 24.04 (Noble) | 3.12 (system) | Native support |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Postfix rejects mail | Check `postfix check` output |
| Filter not invoked | Verify transport_maps in main.cf |
| LLM errors | Check API keys in .env |
| Permission denied | Ensure mail-agent user owns files |
| IMAP connection failed | Verify credentials and port 993 |

## Uninstallation

```bash
# Remove (keep config)
sudo apt remove mail-agent

# Purge (remove everything)
sudo apt purge mail-agent
```

## Documentation

```bash
# View man page
man mail-agent

# Validate configuration
mail-agent --validate

# Test mode
mail-agent --test --dry-run
```

## Support

- **Email**: mail-agent@zamboviktor.hu
- **Issues**: https://github.com/vzambo64/mail-agent/issues

## License

MIT License - Copyright (C) 2024 Viktor Zambo

See [LICENSE](LICENSE) for details.

