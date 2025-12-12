#!/bin/bash
# Build Debian Package for Mail-Agent
#
# Usage:
#   ./build-deb.sh
#
# Output:
#   build/mail-agent_1.0.0.deb
#
# Copyright (C) 2024 Viktor Zambo <mail-agent@zamboviktor.hu>
# License: MIT

set -e

VERSION="1.0.0"
PACKAGE="mail-agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/${PACKAGE}_${VERSION}"

echo "Building $PACKAGE version $VERSION..."

# Clean previous build
rm -rf "$SCRIPT_DIR/build/"

# Create directory structure
echo "Creating directory structure..."
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/opt/mail-agent/src/llm"
mkdir -p "${BUILD_DIR}/opt/mail-agent/scripts"
mkdir -p "${BUILD_DIR}/etc/mail-agent"
mkdir -p "${BUILD_DIR}/usr/share/man/man1"
mkdir -p "${BUILD_DIR}/usr/share/doc/mail-agent"

# Copy application files
echo "Copying application files..."
cp -r "$SCRIPT_DIR/src/"* "${BUILD_DIR}/opt/mail-agent/src/"
cp "$SCRIPT_DIR/requirements.txt" "${BUILD_DIR}/opt/mail-agent/"
cp "$SCRIPT_DIR/scripts/install.sh" "${BUILD_DIR}/opt/mail-agent/scripts/"
cp "$SCRIPT_DIR/scripts/uninstall.sh" "${BUILD_DIR}/opt/mail-agent/scripts/"

# Copy config samples
echo "Copying configuration samples..."
cp "$SCRIPT_DIR/config/settings.yaml.sample" "${BUILD_DIR}/etc/mail-agent/settings.yaml"
cp "$SCRIPT_DIR/config/rules.yaml.sample" "${BUILD_DIR}/etc/mail-agent/rules.yaml"
cp "$SCRIPT_DIR/config/env.sample" "${BUILD_DIR}/etc/mail-agent/.env"

# Copy documentation
if [ -f "$SCRIPT_DIR/README.md" ]; then
    cp "$SCRIPT_DIR/README.md" "${BUILD_DIR}/usr/share/doc/mail-agent/"
fi

# Copy and compress man page
if [ -f "$SCRIPT_DIR/man/mail-agent.1" ]; then
    gzip -c "$SCRIPT_DIR/man/mail-agent.1" > "${BUILD_DIR}/usr/share/man/man1/mail-agent.1.gz"
fi

# Copy debian control files
echo "Copying Debian control files..."
cp "$SCRIPT_DIR/debian/control" "${BUILD_DIR}/DEBIAN/"
cp "$SCRIPT_DIR/debian/postinst" "${BUILD_DIR}/DEBIAN/"
cp "$SCRIPT_DIR/debian/prerm" "${BUILD_DIR}/DEBIAN/"
cp "$SCRIPT_DIR/debian/postrm" "${BUILD_DIR}/DEBIAN/"
cp "$SCRIPT_DIR/debian/conffiles" "${BUILD_DIR}/DEBIAN/"

# Set permissions
echo "Setting permissions..."
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"
chmod 755 "${BUILD_DIR}/DEBIAN/prerm"
chmod 755 "${BUILD_DIR}/DEBIAN/postrm"
chmod 755 "${BUILD_DIR}/opt/mail-agent/scripts/"*.sh
chmod 600 "${BUILD_DIR}/etc/mail-agent/.env"

# Calculate installed size
INSTALLED_SIZE=$(du -sk "${BUILD_DIR}" | cut -f1)
echo "Installed-Size: $INSTALLED_SIZE" >> "${BUILD_DIR}/DEBIAN/control"

# Build package
echo "Building Debian package..."
dpkg-deb --build "${BUILD_DIR}"

# Move to more friendly name
mv "$SCRIPT_DIR/build/${PACKAGE}_${VERSION}.deb" "$SCRIPT_DIR/build/${PACKAGE}_${VERSION}_all.deb"

echo ""
echo "=========================================="
echo "Package built successfully!"
echo "=========================================="
echo ""
echo "Output: $SCRIPT_DIR/build/${PACKAGE}_${VERSION}_all.deb"
echo ""
echo "Install with:"
echo "  sudo apt install ./build/${PACKAGE}_${VERSION}_all.deb"
echo ""
echo "Or:"
echo "  sudo dpkg -i ./build/${PACKAGE}_${VERSION}_all.deb"
echo "  sudo apt-get install -f  # Install dependencies"
echo ""

