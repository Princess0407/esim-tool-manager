#!/usr/bin/env bash
# Usage: curl -sSL https://raw.githubusercontent.com/Princess0407/esim-tool-manager/main/install.sh | bash

set -e

REPO="https://github.com/Princess0407/esim-tool-manager"
INSTALL_DIR="$HOME/.esim-tool-manager"
BIN_DIR="$HOME/.local/bin"

echo ""
echo "  eSim Tool Manager:  Installer
echo "  
echo ""

if ! command -v python3 &>/dev/null; then
    echo "  [✗] Python 3 is required but not found."
    echo "      Install it with: sudo apt install python3"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  [✓] Python $PY_VER found"


if ! command -v pip3 &>/dev/null; then
    echo "  [!] pip3 not found — installing..."
    sudo apt install -y python3-pip 2>/dev/null || true
fi
echo "  [✓] pip3 found"

if ! command -v git &>/dev/null; then
    echo "  [!] git not found — installing..."
    sudo apt install -y git 2>/dev/null || true
fi

if [ -d "$INSTALL_DIR" ]; then
    echo "  [↺] Updating existing installation..."
    git -C "$INSTALL_DIR" pull --quiet
else
    echo "  [↓] Cloning repository..."
    git clone --quiet "$REPO" "$INSTALL_DIR"
fi

echo "  [⚙] Installing Python dependencies..."
pip3 install --quiet --break-system-packages -r "$INSTALL_DIR/requirements.txt" 2>/dev/null \
    || pip3 install --quiet -r "$INSTALL_DIR/requirements.txt"

# to create launcher scrrpt
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/esim-tm" <<EOF
#!/usr/bin/env bash
python3 $INSTALL_DIR/main.py "\$@"
EOF
chmod +x "$BIN_DIR/esim-tm"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "  [!] Add this to your ~/.bashrc or ~/.zshrc:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "  [✓] Installation complete!"
echo ""
echo "  Run the terminal UI:  esim-tm"
echo "  Run the GUI:          esim-tm --gui"
echo "  Scan tools:           esim-tm --scan"
echo "  Check dependencies:   esim-tm --check"
echo ""
