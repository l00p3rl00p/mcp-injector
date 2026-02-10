#!/bin/bash
set -e

echo "🔧 MCP JSON Injector - Installation"
echo "===================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found."
    echo "   Install Python 3.6+ to continue."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
echo "✅ Python $PYTHON_VERSION detected"
echo ""

# Make executable
chmod +x mcp_injector.py
echo "✅ Made mcp_injector.py executable"

# Installation options
echo ""
echo "Installation Options:"
echo "  1. Install to PATH (/usr/local/bin/mcp-inject)"
echo "  2. Use in current directory (./mcp_injector.py)"
echo ""
read -p "Choose [1/2]: " -n 1 -r
echo ""

if [[ $REPLY == "1" ]]; then
    # Check write permissions
    if [ -w /usr/local/bin ]; then
        cp mcp_injector.py /usr/local/bin/mcp-inject
        echo "✅ Installed to /usr/local/bin/mcp-inject"
        echo ""
        echo "🎉 Installation complete!"
        echo "   Try: mcp-inject --list-clients"
    else
        echo "⚠️  Need sudo for /usr/local/bin"
        sudo cp mcp_injector.py /usr/local/bin/mcp-inject
        echo "✅ Installed to /usr/local/bin/mcp-inject"
        echo ""
        echo "🎉 Installation complete!"
        echo "   Try: mcp-inject --list-clients"
    fi
else
    echo "✅ Ready to use in current directory"
    echo ""
    echo "🎉 Installation complete!"
    echo "   Try: ./mcp_injector.py --list-clients"
fi

echo ""
echo "📖 Quick Start:"
echo "   mcp-inject --client claude --add    # Add server to Claude"
echo "   mcp-inject --client xcode --list     # List Xcode servers"
echo "   mcp-inject --list-clients            # Show all IDE locations"
