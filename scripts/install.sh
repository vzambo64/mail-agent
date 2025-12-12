#!/bin/bash
# Mail-Agent Installation Script
# Installs mail-agent on Ubuntu 18.04+ with Postfix and Dovecot
#
# Usage:
#   sudo ./install.sh                    # Interactive installation
#   sudo ./install.sh --unattended       # Non-interactive (uses env vars)
#   sudo ./install.sh --dry-run          # Show what would be done
#
# Copyright (C) 2024 Viktor Zambo <mail-agent@zamboviktor.hu>
# License: MIT

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

INSTALL_DIR="/opt/mail-agent"
CONFIG_DIR="/etc/mail-agent"
LOG_DIR="/var/log/mail-agent"
SERVICE_USER="mail-agent"
PYTHON_MIN_VERSION="3.10"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Utility Functions
# =============================================================================

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

die() {
    log_error "$1"
    exit 1
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        die "This script must be run as root (use sudo)"
    fi
}

detect_ubuntu_version() {
    if [[ ! -f /etc/os-release ]]; then
        die "Cannot detect OS version"
    fi
    
    source /etc/os-release
    
    if [[ "$ID" != "ubuntu" ]]; then
        log_warn "This script is designed for Ubuntu. Detected: $ID"
    fi
    
    UBUNTU_VERSION="${VERSION_ID:-unknown}"
    log_info "Detected Ubuntu version: $UBUNTU_VERSION"
    
    # Check minimum version
    if [[ "$UBUNTU_VERSION" < "18.04" ]]; then
        die "Ubuntu 18.04 or later is required"
    fi
}

check_postfix() {
    if ! command -v postfix &> /dev/null; then
        die "Postfix is not installed. Install with: sudo apt install postfix"
    fi
    
    if ! systemctl is-active --quiet postfix; then
        log_warn "Postfix is not running. Will be started after configuration."
    else
        log_info "Postfix is running"
    fi
}

check_dovecot() {
    if command -v dovecot &> /dev/null; then
        log_info "Dovecot is installed"
        if systemctl is-active --quiet dovecot; then
            log_info "Dovecot is running"
        fi
    else
        log_warn "Dovecot not found. IMAP draft mode may not work without it."
    fi
}

# =============================================================================
# Python Installation
# =============================================================================

PYTHON_CMD=""

install_python() {
    log_step "Checking Python version..."
    
    # Check if Python 3.10+ is available
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" &> /dev/null; then
            local version
            version=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            if [[ "$(printf '%s\n' "$PYTHON_MIN_VERSION" "$version" | sort -V | head -n1)" == "$PYTHON_MIN_VERSION" ]]; then
                PYTHON_CMD="$cmd"
                log_info "Found compatible Python: $cmd ($version)"
                return 0
            fi
        fi
    done
    
    # Python 3.10+ not found - install from deadsnakes PPA
    log_info "Python 3.10+ not found. Installing from deadsnakes PPA..."
    
    apt-get update
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.10 python3.10-venv python3.10-distutils
    
    # Install pip for Python 3.10
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
    
    PYTHON_CMD="python3.10"
    log_info "Installed Python 3.10 from deadsnakes PPA"
}

# =============================================================================
# Installation
# =============================================================================

install_dependencies() {
    log_step "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        curl \
        ca-certificates \
        gnupg \
        lsb-release \
        git
}

create_user() {
    log_step "Creating mail-agent user..."
    
    if ! getent passwd "$SERVICE_USER" > /dev/null; then
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
        log_info "Created user: $SERVICE_USER"
    else
        log_info "User already exists: $SERVICE_USER"
    fi
}

install_application() {
    log_step "Installing mail-agent application..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    
    # Copy application files
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    APP_DIR="$(dirname "$SCRIPT_DIR")"
    
    cp -r "$APP_DIR/src" "$INSTALL_DIR/"
    cp "$APP_DIR/requirements.txt" "$INSTALL_DIR/"
    
    # Copy sample configs if config doesn't exist
    if [[ ! -f "$CONFIG_DIR/settings.yaml" ]]; then
        cp "$APP_DIR/config/settings.yaml.sample" "$CONFIG_DIR/settings.yaml"
    fi
    
    if [[ ! -f "$CONFIG_DIR/rules.yaml" ]]; then
        cp "$APP_DIR/config/rules.yaml.sample" "$CONFIG_DIR/rules.yaml"
    fi
    
    if [[ ! -f "$CONFIG_DIR/.env" ]]; then
        cp "$APP_DIR/config/env.sample" "$CONFIG_DIR/.env"
        chmod 600 "$CONFIG_DIR/.env"
    fi
    
    # Create virtual environment
    log_info "Creating Python virtual environment..."
    rm -rf "$INSTALL_DIR/venv"
    $PYTHON_CMD -m venv "$INSTALL_DIR/venv"
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    
    log_info "Application installed to $INSTALL_DIR"
}

# =============================================================================
# Postfix Configuration
# =============================================================================

configure_postfix() {
    log_step "Configuring Postfix..."
    
    local MASTER_CF="/etc/postfix/master.cf"
    local TRANSPORT_MAP="/etc/postfix/transport_mail_agent"
    local MAIN_CF="/etc/postfix/main.cf"
    
    # Backup existing config
    if [[ -f "$MASTER_CF" ]]; then
        cp "$MASTER_CF" "$MASTER_CF.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    # Add mail-agent transport if not present
    if ! grep -q "mail-agent" "$MASTER_CF"; then
        cat >> "$MASTER_CF" << 'EOF'

# Mail-Agent AI Auto-Reply Filter
mail-agent unix - n n - 10 pipe
  flags=Rq user=mail-agent null_sender=
  argv=/opt/mail-agent/venv/bin/python -m src.main
EOF
        log_info "Added mail-agent transport to master.cf"
    else
        log_info "mail-agent transport already in master.cf"
    fi
    
    # Create transport map if not exists
    if [[ ! -f "$TRANSPORT_MAP" ]]; then
        cat > "$TRANSPORT_MAP" << 'EOF'
# Mail-Agent Transport Map
# Add recipients that should receive auto-replies
# Format: email@domain.com    mail-agent:
#
# Example:
# support@yourdomain.com    mail-agent:
# sales@yourdomain.com      mail-agent:
EOF
        log_info "Created transport map: $TRANSPORT_MAP"
    fi
    
    # Update main.cf if needed
    if ! grep -q "transport_mail_agent" "$MAIN_CF"; then
        if grep -q "^transport_maps" "$MAIN_CF"; then
            # Add to existing transport_maps
            sed -i 's/^transport_maps = /transport_maps = hash:\/etc\/postfix\/transport_mail_agent, /' "$MAIN_CF"
        else
            # Add new transport_maps line
            echo "transport_maps = hash:/etc/postfix/transport_mail_agent" >> "$MAIN_CF"
        fi
        log_info "Updated main.cf with transport_maps"
    fi
    
    # Generate transport map database
    postmap "$TRANSPORT_MAP"
    
    # Check configuration
    if postfix check; then
        log_info "Postfix configuration is valid"
    else
        log_error "Postfix configuration check failed"
        return 1
    fi
    
    # Reload Postfix
    systemctl reload postfix || true
    log_info "Postfix reloaded"
}

# =============================================================================
# Logging Setup
# =============================================================================

setup_logging() {
    log_step "Setting up logging..."
    
    # Create logrotate configuration
    cat > /etc/logrotate.d/mail-agent << 'EOF'
/var/log/mail-agent/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 640 mail-agent mail-agent
}
EOF
    
    log_info "Configured log rotation"
}

# =============================================================================
# Interactive Configuration
# =============================================================================

interactive_config() {
    if [[ "${UNATTENDED:-}" == "true" ]]; then
        log_info "Skipping interactive configuration (unattended mode)"
        return 0
    fi
    
    log_step "Interactive Configuration"
    echo ""
    echo "Please configure mail-agent settings:"
    echo ""
    
    # LLM Provider
    echo "Select default LLM provider:"
    echo "  1) OpenAI (GPT-4)"
    echo "  2) Anthropic (Claude)"
    echo "  3) Google (Gemini)"
    echo "  4) Ollama (Local)"
    read -p "Choice [1-4, default=1]: " llm_choice
    
    case "${llm_choice:-1}" in
        2) LLM_PROVIDER="anthropic" ;;
        3) LLM_PROVIDER="google" ;;
        4) LLM_PROVIDER="ollama" ;;
        *) LLM_PROVIDER="openai" ;;
    esac
    
    # API Key (if not Ollama)
    if [[ "$LLM_PROVIDER" != "ollama" ]]; then
        read -p "Enter API key for $LLM_PROVIDER: " API_KEY
        
        case "$LLM_PROVIDER" in
            openai) echo "OPENAI_API_KEY=$API_KEY" >> "$CONFIG_DIR/.env" ;;
            anthropic) echo "ANTHROPIC_API_KEY=$API_KEY" >> "$CONFIG_DIR/.env" ;;
            google) echo "GOOGLE_API_KEY=$API_KEY" >> "$CONFIG_DIR/.env" ;;
        esac
    fi
    
    # From address
    read -p "Reply-from email address [auto-reply@localhost]: " FROM_ADDR
    FROM_ADDR="${FROM_ADDR:-auto-reply@localhost}"
    
    # Update settings.yaml
    sed -i "s/default_provider:.*/default_provider: \"$LLM_PROVIDER\"/" "$CONFIG_DIR/settings.yaml"
    sed -i "s/from_address:.*/from_address: \"$FROM_ADDR\"/" "$CONFIG_DIR/settings.yaml"
    
    # Recipient addresses
    read -p "Email addresses to filter (comma-separated): " RECIPIENTS
    
    if [[ -n "$RECIPIENTS" ]]; then
        IFS=',' read -ra ADDR_ARRAY <<< "$RECIPIENTS"
        for addr in "${ADDR_ARRAY[@]}"; do
            addr=$(echo "$addr" | xargs)  # Trim whitespace
            echo "$addr    mail-agent:" >> /etc/postfix/transport_mail_agent
        done
        postmap /etc/postfix/transport_mail_agent
    fi
    
    chmod 600 "$CONFIG_DIR/.env"
    log_info "Configuration saved"
}

# =============================================================================
# Main
# =============================================================================

print_banner() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}          ${GREEN}Mail-Agent Installation Script${NC}                   ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}          AI-powered email auto-reply for Postfix          ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Mail-Agent installed successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Configuration files:"
    echo "    - Settings: $CONFIG_DIR/settings.yaml"
    echo "    - Rules:    $CONFIG_DIR/rules.yaml"
    echo "    - Secrets:  $CONFIG_DIR/.env"
    echo ""
    echo "  Logs: $LOG_DIR/mail-agent.log"
    echo ""
    echo "  Next steps:"
    echo "    1. Edit $CONFIG_DIR/settings.yaml"
    echo "    2. Edit $CONFIG_DIR/rules.yaml"
    echo "    3. Add recipients to /etc/postfix/transport_mail_agent"
    echo "    4. Run: sudo postmap /etc/postfix/transport_mail_agent"
    echo "    5. Run: sudo systemctl reload postfix"
    echo ""
    echo "  Documentation: man mail-agent"
    echo "  Support: mail-agent@zamboviktor.hu"
    echo ""
}

main() {
    # Parse arguments
    DRY_RUN=false
    UNATTENDED=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --unattended)
                UNATTENDED=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --dry-run      Show what would be done without making changes"
                echo "  --unattended   Non-interactive installation"
                echo "  --help         Show this help"
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac
    done
    
    print_banner
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN MODE - No changes will be made"
        echo ""
    fi
    
    # Pre-flight checks
    check_root
    detect_ubuntu_version
    check_postfix
    check_dovecot
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run complete. Would install mail-agent."
        exit 0
    fi
    
    # Installation
    install_dependencies
    install_python
    create_user
    install_application
    configure_postfix
    setup_logging
    interactive_config
    
    print_success
}

main "$@"

