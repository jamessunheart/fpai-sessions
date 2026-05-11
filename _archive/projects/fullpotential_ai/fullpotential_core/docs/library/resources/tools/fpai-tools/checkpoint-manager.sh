#!/bin/bash

# CHECKPOINT MANAGER
# Purpose: Track Sacred Loop progress, detect build completion, enable resume
# Usage: ./checkpoint-manager.sh <command> <droplet-dir> [checkpoint-name]
# Never lose progress - resume from any point

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Commands: init, mark, check, resume, status, clear

COMMAND="$1"
DROPLET_DIR="$2"
CHECKPOINT="$3"

if [ -z "$COMMAND" ] || [ -z "$DROPLET_DIR" ]; then
    print_error "Usage: $0 <command> <droplet-dir> [checkpoint-name]"
    echo ""
    echo "Commands:"
    echo "  init <dir>              Initialize checkpoint tracking"
    echo "  mark <dir> <checkpoint> Mark checkpoint complete"
    echo "  check <dir> <checkpoint> Check if checkpoint exists"
    echo "  detect <dir>            Auto-detect build progress"
    echo "  status <dir>            Show current progress"
    echo "  resume <dir>            Get resume step"
    echo "  clear <dir>             Clear all checkpoints"
    exit 1
fi

CHECKPOINT_FILE="${DROPLET_DIR}/.sacred-loop-checkpoints"

# Initialize checkpoint tracking
cmd_init() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        print_warning "Checkpoints already exist - use 'clear' to reset"
        return 1
    fi

    cat > "$CHECKPOINT_FILE" << 'EOF'
{
  "droplet_id": "",
  "droplet_name": "",
  "started_at": "",
  "checkpoints": {
    "step1_intent": false,
    "step2_spec": false,
    "step3_coordinator": false,
    "step4_build_started": false,
    "step4_models_created": false,
    "step4_endpoints_created": false,
    "step4_tests_created": false,
    "step4_docker_created": false,
    "step4_build_complete": false,
    "step5_verification": false,
    "step6_deployment": false,
    "step7_registry": false,
    "step8_complete": false
  },
  "files": {},
  "last_updated": ""
}
EOF

    # Update with current timestamp
    if command -v python3 &> /dev/null; then
        python3 -c "
import json
from datetime import datetime

with open('$CHECKPOINT_FILE', 'r') as f:
    data = json.load(f)

data['started_at'] = datetime.utcnow().isoformat() + 'Z'
data['last_updated'] = datetime.utcnow().isoformat() + 'Z'

with open('$CHECKPOINT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null || true
    fi

    print_success "Checkpoint tracking initialized: $CHECKPOINT_FILE"
}

# Mark checkpoint complete
cmd_mark() {
    if [ -z "$CHECKPOINT" ]; then
        print_error "Checkpoint name required"
        return 1
    fi

    if [ ! -f "$CHECKPOINT_FILE" ]; then
        cmd_init
    fi

    # Update checkpoint
    if command -v python3 &> /dev/null; then
        python3 -c "
import json
from datetime import datetime

with open('$CHECKPOINT_FILE', 'r') as f:
    data = json.load(f)

if '$CHECKPOINT' in data['checkpoints']:
    data['checkpoints']['$CHECKPOINT'] = True
    data['last_updated'] = datetime.utcnow().isoformat() + 'Z'

    with open('$CHECKPOINT_FILE', 'w') as f:
        json.dump(data, f, indent=2)
    print('✅')
else:
    print('❌')
" 2>/dev/null
    else
        # Fallback: Simple text append
        echo "$CHECKPOINT:$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$CHECKPOINT_FILE"
    fi

    print_success "Checkpoint marked: $CHECKPOINT"
}

# Check if checkpoint exists
cmd_check() {
    if [ -z "$CHECKPOINT" ]; then
        print_error "Checkpoint name required"
        return 1
    fi

    if [ ! -f "$CHECKPOINT_FILE" ]; then
        return 1
    fi

    if command -v python3 &> /dev/null; then
        python3 -c "
import json
import sys

try:
    with open('$CHECKPOINT_FILE', 'r') as f:
        data = json.load(f)

    if '$CHECKPOINT' in data['checkpoints'] and data['checkpoints']['$CHECKPOINT']:
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
" 2>/dev/null
        return $?
    else
        grep -q "^$CHECKPOINT:" "$CHECKPOINT_FILE" 2>/dev/null
        return $?
    fi
}

# Auto-detect build progress by checking files
cmd_detect() {
    print_info "Auto-detecting build progress..."

    # Check for expected files
    local files_found=()
    local files_missing=()

    check_file() {
        local file="$1"
        local checkpoint="$2"

        if [ -f "${DROPLET_DIR}/${file}" ]; then
            files_found+=("$file")
            cmd_mark "$DROPLET_DIR" "$checkpoint" 2>/dev/null || true
            echo "  ✅ $file"
        else
            files_missing+=("$file")
            echo "  ❌ $file (not found)"
        fi
    }

    echo ""
    print_info "Checking build files..."

    check_file "app/__init__.py" "step4_models_created"
    check_file "app/main.py" "step4_endpoints_created"
    check_file "app/models.py" "step4_models_created"
    check_file "app/config.py" "step4_models_created"
    check_file "tests/test_endpoints.py" "step4_tests_created"
    check_file "Dockerfile" "step4_docker_created"
    check_file "requirements.txt" "step4_docker_created"
    check_file ".env.example" "step4_docker_created"
    check_file "README.md" "step4_docker_created"

    echo ""
    local found_count=${#files_found[@]}
    local total_count=$((found_count + ${#files_missing[@]}))

    if [ $found_count -eq $total_count ]; then
        print_success "Build appears complete! All files found ($found_count/$total_count)"
        cmd_mark "$DROPLET_DIR" "step4_build_complete" 2>/dev/null || true
        return 0
    elif [ $found_count -gt 0 ]; then
        print_warning "Build in progress: $found_count/$total_count files found"
        return 2
    else
        print_warning "Build not started: 0/$total_count files found"
        return 1
    fi
}

# Show current status
cmd_status() {
    if [ ! -f "$CHECKPOINT_FILE" ]; then
        print_warning "No checkpoints found - run 'init' first"
        return 1
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Sacred Loop Progress"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if command -v python3 &> /dev/null; then
        python3 -c "
import json

with open('$CHECKPOINT_FILE', 'r') as f:
    data = json.load(f)

checkpoints = [
    ('step1_intent', 'Step 1: Architect Intent'),
    ('step2_spec', 'Step 2: AI SPEC Generation'),
    ('step3_coordinator', 'Step 3: Coordinator Package'),
    ('step4_build_started', 'Step 4: Build Started'),
    ('step4_models_created', '  → Models Created'),
    ('step4_endpoints_created', '  → Endpoints Created'),
    ('step4_tests_created', '  → Tests Created'),
    ('step4_docker_created', '  → Docker Created'),
    ('step4_build_complete', 'Step 4: Build Complete'),
    ('step5_verification', 'Step 5: Verification'),
    ('step6_deployment', 'Step 6: Deployment'),
    ('step7_registry', 'Step 7: Registry Update'),
    ('step8_complete', 'Step 8: Complete'),
]

for checkpoint, label in checkpoints:
    status = '✅' if data['checkpoints'].get(checkpoint) else '⏳'
    print(f'{status} {label}')

print()
print(f\"Started: {data.get('started_at', 'Unknown')}\")
print(f\"Last Updated: {data.get('last_updated', 'Unknown')}\")
" 2>/dev/null
    else
        print_warning "Python not available - showing raw checkpoints"
        cat "$CHECKPOINT_FILE"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Get resume step
cmd_resume() {
    if [ ! -f "$CHECKPOINT_FILE" ]; then
        echo "1"
        return 0
    fi

    if command -v python3 &> /dev/null; then
        python3 -c "
import json

with open('$CHECKPOINT_FILE', 'r') as f:
    data = json.load(f)

checkpoints_order = [
    'step1_intent',
    'step2_spec',
    'step3_coordinator',
    'step4_build_started',
    'step4_build_complete',
    'step5_verification',
    'step6_deployment',
    'step7_registry',
    'step8_complete',
]

# Find first incomplete checkpoint
for i, checkpoint in enumerate(checkpoints_order):
    if not data['checkpoints'].get(checkpoint):
        # Map checkpoint to step number
        step_map = {
            'step1_intent': 1,
            'step2_spec': 2,
            'step3_coordinator': 3,
            'step4_build_started': 4,
            'step4_build_complete': 5,
            'step5_verification': 5,
            'step6_deployment': 6,
            'step7_registry': 7,
            'step8_complete': 8,
        }
        print(step_map.get(checkpoint, 1))
        exit(0)

# All complete
print(8)
" 2>/dev/null
    else
        echo "1"
    fi
}

# Clear all checkpoints
cmd_clear() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        rm -f "$CHECKPOINT_FILE"
        print_success "Checkpoints cleared"
    else
        print_warning "No checkpoints to clear"
    fi
}

# Execute command
case "$COMMAND" in
    init)
        cmd_init
        ;;
    mark)
        cmd_mark
        ;;
    check)
        cmd_check
        ;;
    detect)
        cmd_detect
        ;;
    status)
        cmd_status
        ;;
    resume)
        cmd_resume
        ;;
    clear)
        cmd_clear
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo "Use: init, mark, check, detect, status, resume, or clear"
        exit 1
        ;;
esac
