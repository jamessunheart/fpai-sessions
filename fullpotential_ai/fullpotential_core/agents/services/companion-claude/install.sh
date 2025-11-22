#!/bin/bash

# Companion Claude - Installation Script

echo "🤖 Installing Companion Claude - Your Proactive AI Director"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

echo "✅ Virtual environment created"

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"

# Create templates directory
echo ""
echo "Setting up directories..."
mkdir -p templates
mkdir -p static

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env configuration..."
    cat > .env << 'EOF'
# Companion Claude Configuration

# Notification preferences
NOTIFY_DESKTOP=true
NOTIFY_TERMINAL=true
NOTIFY_SMS=false

# Proactive behavior
PROACTIVE_SUGGESTIONS=true
AUTO_START_SESSIONS=false
MORNING_BRIEFING=true
EOD_SUMMARY=true

# Context monitoring
MONITOR_FILES=true
MONITOR_GIT=true
MONITOR_TERMINAL=true
MONITOR_BROWSER=false

# Work hours
WORK_START=09:00
WORK_END=18:00
TIMEZONE=America/Los_Angeles

# Focus mode
FOCUS_MODE=false

# Service ports
PORT=8900
WS_PORT=8902
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Create start script
echo ""
echo "Creating start script..."
cat > start.sh << 'EOF'
#!/bin/bash

# Start Companion Claude

echo "🤖 Starting Companion Claude..."

# Activate virtual environment
source venv/bin/activate

# Start the service
python3 main.py
EOF

chmod +x start.sh
echo "✅ Start script created"

# Create CLI wrapper
echo ""
echo "Creating CLI wrapper..."
cat > companion << 'EOF'
#!/bin/bash

# Companion Claude CLI

API_URL="http://localhost:8900"

if [ $# -eq 0 ]; then
    echo "Usage: companion <command> [args]"
    echo ""
    echo "Commands:"
    echo "  status       - Get current status"
    echo "  briefing     - Get daily briefing"
    echo "  priorities   - Show priority stack"
    echo "  delegate     - Delegate a task"
    echo "  encode       - Encode an intent"
    echo "  help         - Show help"
    exit 0
fi

COMMAND=$1
shift

case $COMMAND in
    status)
        curl -s "$API_URL/context" | jq '.'
        ;;
    briefing)
        curl -s -X POST "$API_URL/cli?command=briefing" | jq '.'
        ;;
    priorities)
        curl -s "$API_URL/priorities" | jq '.'
        ;;
    delegate)
        if [ -z "$1" ]; then
            echo "Usage: companion delegate <task>"
            exit 1
        fi
        TASK=$@
        curl -s -X POST "$API_URL/delegate" \
            -H "Content-Type: application/json" \
            -d "{\"task\": \"$TASK\"}" | jq '.'
        ;;
    encode)
        if [ -z "$1" ]; then
            echo "Usage: companion encode <intent>"
            exit 1
        fi
        INTENT=$@
        curl -s -X POST "$API_URL/encode-prompt" \
            -H "Content-Type: application/json" \
            -d "{\"intent\": \"$INTENT\"}" | jq '.'
        ;;
    help)
        curl -s -X POST "$API_URL/cli?command=help" | jq '.'
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run 'companion' for usage"
        exit 1
        ;;
esac
EOF

chmod +x companion
echo "✅ CLI wrapper created"

# Create shell integration
echo ""
echo "Creating shell integration..."
cat > shell-integration.sh << 'EOF'
# Companion Claude Shell Integration
# Source this in your ~/.zshrc or ~/.bashrc

# Check for Companion Claude notifications on prompt
precmd() {
    if [ -f "/Users/jamessunheart/Development/docs/coordination/sessions/ACTIVE/companion_notifications.txt" ]; then
        # Read new notifications
        tail -n 5 "/Users/jamessunheart/Development/docs/coordination/sessions/ACTIVE/companion_notifications.txt" 2>/dev/null
    fi
}

# Add companion CLI to PATH
export PATH="/Users/jamessunheart/Development/agents/services/companion-claude:$PATH"

# Quick aliases
alias cs='companion status'
alias cb='companion briefing'
alias cp='companion priorities'
EOF

echo "✅ Shell integration created"

# Test the installation
echo ""
echo "Testing installation..."
python3 -c "from context_engine import ContextEngine; from prompt_encoder import PromptEncoder; print('✅ All modules importable')"

if [ $? -ne 0 ]; then
    echo "❌ Module test failed"
    exit 1
fi

# Final instructions
echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Companion Claude:"
echo "   ./start.sh"
echo ""
echo "2. (Optional) Add shell integration to ~/.zshrc:"
echo "   echo 'source /Users/jamessunheart/Development/agents/services/companion-claude/shell-integration.sh' >> ~/.zshrc"
echo ""
echo "3. Open the Director Dashboard:"
echo "   http://localhost:8900/director"
echo ""
echo "4. Use the CLI:"
echo "   ./companion status"
echo "   ./companion briefing"
echo "   ./companion delegate 'Your task here'"
echo ""
echo "🚀 Companion Claude is ready to assist you proactively!"
