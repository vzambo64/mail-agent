#!/bin/bash
# Mail-Agent Uninstallation Script
#
# Usage:
#   sudo ./uninstall.sh                # Remove application (keep config)
#   sudo ./uninstall.sh --purge        # Remove everything including config
#   sudo ./uninstall.sh --keep-logs    # Keep log files
#
# Copyright (C) 2024 Viktor Zambo <mail-agent@zamboviktor.hu>
# License: MIT

set -euo pipefail

# Configuration
INSTALL_DIR="/opt/mail-agent"
CONFIG_DIR="/etc/mail-agent"
LOG_DIR="/var/log/mail-agent"
SERVICE_USER="mail-agent"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Parse arguments
PURGE=false
KEEP_LOGS=false
KEEP_CONFIG=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge)
            PURGE=true
            shift
            ;;
        --keep-logs)
            KEEP_LOGS=true
            shift
            ;;
        --keep-config)
            KEEP_CONFIG=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --purge        Remove everything including configuration"
            echo "  --keep-logs    Keep log files"
            echo "  --keep-config  Keep configuration files"
            echo "  --help         Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "Mail-Agent Uninstallation"
echo "========================="
echo ""

# Remove Postfix configuration
log_info "Removing Postfix configuration..."

MASTER_CF="/etc/postfix/master.cf"
TRANSPORT_MAP="/etc/postfix/transport_mail_agent"
MAIN_CF="/etc/postfix/main.cf"

# Remove from master.cf
if [[ -f "$MASTER_CF" ]]; then
    # Remove mail-agent transport block
    sed -i '/^# Mail-Agent/,/^[^ ]/{ /^[^ ]/!d; /^# Mail-Agent/d }' "$MASTER_CF" 2>/dev/null || true
    sed -i '/^mail-agent unix/d' "$MASTER_CF" 2>/dev/null || true
    log_info "Removed mail-agent from master.cf"
fi

# Remove transport map
if [[ -f "$TRANSPORT_MAP" ]]; then
    rm -f "$TRANSPORT_MAP"
    rm -f "$TRANSPORT_MAP.db"
    log_info "Removed transport map"
fi

# Update main.cf
if [[ -f "$MAIN_CF" ]]; then
    sed -i 's/hash:\/etc\/postfix\/transport_mail_agent, //g' "$MAIN_CF" 2>/dev/null || true
    sed -i 's/, hash:\/etc\/postfix\/transport_mail_agent//g' "$MAIN_CF" 2>/dev/null || true
    sed -i '/^transport_maps = $/d' "$MAIN_CF" 2>/dev/null || true
    log_info "Updated main.cf"
fi

# Reload Postfix
if systemctl is-active --quiet postfix; then
    systemctl reload postfix 2>/dev/null || true
    log_info "Reloaded Postfix"
fi

# Remove application directory
if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    log_info "Removed $INSTALL_DIR"
fi

# Handle configuration
if [[ "$PURGE" == "true" ]] && [[ "$KEEP_CONFIG" != "true" ]]; then
    if [[ -d "$CONFIG_DIR" ]]; then
        rm -rf "$CONFIG_DIR"
        log_info "Removed $CONFIG_DIR"
    fi
else
    if [[ -d "$CONFIG_DIR" ]]; then
        log_warn "Configuration preserved in $CONFIG_DIR"
    fi
fi

# Handle logs
if [[ "$PURGE" == "true" ]] && [[ "$KEEP_LOGS" != "true" ]]; then
    if [[ -d "$LOG_DIR" ]]; then
        rm -rf "$LOG_DIR"
        log_info "Removed $LOG_DIR"
    fi
    
    # Remove logrotate config
    rm -f /etc/logrotate.d/mail-agent
else
    if [[ -d "$LOG_DIR" ]]; then
        log_warn "Logs preserved in $LOG_DIR"
    fi
fi

# Remove user
if [[ "$PURGE" == "true" ]]; then
    if getent passwd "$SERVICE_USER" > /dev/null; then
        userdel "$SERVICE_USER" 2>/dev/null || true
        log_info "Removed user: $SERVICE_USER"
    fi
fi

echo ""
log_info "Mail-Agent uninstallation complete!"

if [[ "$PURGE" != "true" ]]; then
    echo ""
    log_warn "Configuration and logs were preserved."
    log_warn "Run with --purge to remove everything."
fi

echo ""

