#!/bin/bash

# 🏗️ Create Droplet - Assembly Line Standard
# Creates a new droplet following the standardized structure

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if droplet name provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: ./create-droplet.sh [droplet-name]${NC}"
    echo ""
    echo "Examples:"
    echo "  ./create-droplet.sh church-guidance-ministry"
    echo "  ./create-droplet.sh email-automation"
    echo "  ./create-droplet.sh payment-processor"
    exit 1
fi

DROPLET_NAME=$1
DROPLET_DIR="$HOME/Development/agents/services/$DROPLET_NAME"

# Check if droplet already exists
if [ -d "$DROPLET_DIR" ]; then
    echo -e "${YELLOW}⚠️  Droplet '$DROPLET_NAME' already exists at:${NC}"
    echo "   $DROPLET_DIR"
    echo ""
    read -p "Do you want to standardize it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${BLUE}🏗️  Creating new droplet: $DROPLET_NAME${NC}"
    mkdir -p "$DROPLET_DIR"
fi

# Create directory structure
echo -e "${BLUE}📁 Creating directory structure...${NC}"
mkdir -p "$DROPLET_DIR/BUILD/src"
mkdir -p "$DROPLET_DIR/BUILD/tests"
mkdir -p "$DROPLET_DIR/PRODUCTION"

# Create SPECS.md
if [ ! -f "$DROPLET_DIR/SPECS.md" ]; then
    echo -e "${BLUE}📝 Creating SPECS.md...${NC}"
    cat > "$DROPLET_DIR/SPECS.md" << 'EOF'
# [DROPLET_NAME] - SPECS

**Created:** [DATE]
**Status:** Planning

---

## Purpose

[1-2 sentence description of what this droplet does and why it exists]

---

## Requirements

### Functional Requirements
- [ ] Requirement 1 - Description
- [ ] Requirement 2 - Description
- [ ] Requirement 3 - Description

### Non-Functional Requirements
- [ ] Performance: [Specify metrics]
- [ ] Security: [Specify requirements]
- [ ] Compliance: [Legal/regulatory considerations]

---

## API Specs

### Endpoints

**[HTTP Method] /endpoint-path**
- **Purpose:** What it does
- **Input:** Request format
- **Output:** Response format
- **Success:** Status code + response
- **Errors:** Error codes + messages

### Data Models

```python
# Example model
class EntityName:
    field1: str
    field2: int
    field3: Optional[bool]
```

---

## Dependencies

### External Services
- Service 1: Purpose/reason
- Service 2: Purpose/reason

### APIs Required
- API 1: What for
- API 2: What for

### Data Sources
- Source 1: Description
- Source 2: Description

---

## Success Criteria

How do we know this droplet works?

- [ ] Criterion 1 (must be testable)
- [ ] Criterion 2 (must be testable)
- [ ] Criterion 3 (must be testable)
- [ ] All tests pass
- [ ] Deployed and accessible

---

## Compliance Notes

### Legal Considerations
[Any legal/regulatory requirements]

### Liability Boundaries
[Clear statement of what this service does/doesn't provide]

### AI Compliance Support
[How AI assists without replacing professional services]

---

## Technical Constraints

- Language/Framework: [Specify]
- Port: [If applicable]
- Resource limits: [Memory, CPU, etc.]

---

**Next Step:** Fill out this SPECS document completely before starting BUILD phase.

⚡ Assembly Line: SPECS → BUILD → README → PRODUCTION
EOF
    # Replace placeholders
    sed -i '' "s/\[DROPLET_NAME\]/$DROPLET_NAME/g" "$DROPLET_DIR/SPECS.md"
    sed -i '' "s/\[DATE\]/$(date +%Y-%m-%d)/g" "$DROPLET_DIR/SPECS.md"
fi

# Create README.md
if [ ! -f "$DROPLET_DIR/README.md" ]; then
    echo -e "${BLUE}📝 Creating README.md...${NC}"
    cat > "$DROPLET_DIR/README.md" << 'EOF'
# [DROPLET_NAME]

**Status:** Planning
**Progress:** 0%
**Last Updated:** [DATE]
**Port:** [TBD]

---

## Quick Start

```bash
# How to run locally (will be filled during BUILD phase)
cd BUILD
# Instructions here
```

---

## Testing

```bash
# How to run tests (will be filled during BUILD phase)
cd BUILD
# Test commands here
```

---

## API Documentation

[Will be filled from SPECS during BUILD phase]

---

## Deployment

```bash
# How to deploy (will be filled during PRODUCTION phase)
# Deployment commands here
```

---

## Build Status

### Phase 1: SPECS ⏳
- [ ] Purpose defined
- [ ] Requirements documented
- [ ] API specs complete
- [ ] Success criteria defined
- [ ] Compliance notes added

### Phase 2: BUILD ⏳
- [ ] Directory structure created
- [ ] Core functionality implemented
- [ ] Tests written
- [ ] Tests passing
- [ ] Local testing complete

### Phase 3: README ⏳
- [ ] Quick start instructions
- [ ] Testing guide
- [ ] API documentation
- [ ] Deployment guide

### Phase 4: PRODUCTION ⏳
- [ ] Deployed to server
- [ ] Health checks configured
- [ ] Monitoring active
- [ ] Integration tested

---

## Progress Tracking

### Complete ✅
- Directory structure created
- SPECS template ready
- README template ready

### In Progress 🚧
- Fill out SPECS.md
- Define requirements

### Pending ⏳
- Implementation
- Testing
- Deployment

---

## Notes

[Add any important notes, blockers, or decisions here]

---

**Assembly Line:** SPECS → BUILD → README → PRODUCTION

📍 Current Phase: SPECS (fill out SPECS.md first!)
EOF
    # Replace placeholders
    sed -i '' "s/\[DROPLET_NAME\]/$DROPLET_NAME/g" "$DROPLET_DIR/README.md"
    sed -i '' "s/\[DATE\]/$(date +%Y-%m-%d)/g" "$DROPLET_DIR/README.md"
fi

# Create basic requirements.txt
if [ ! -f "$DROPLET_DIR/BUILD/requirements.txt" ]; then
    echo -e "${BLUE}📝 Creating requirements.txt...${NC}"
    cat > "$DROPLET_DIR/BUILD/requirements.txt" << 'EOF'
# Python dependencies
# Add as needed during BUILD phase
EOF
fi

# Create basic Dockerfile template
if [ ! -f "$DROPLET_DIR/BUILD/Dockerfile" ]; then
    echo -e "${BLUE}📝 Creating Dockerfile template...${NC}"
    cat > "$DROPLET_DIR/BUILD/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Update port as needed
EXPOSE 8000

# Update command as needed
CMD ["python", "-m", "src.main"]
EOF
fi

# Create .env.example
if [ ! -f "$DROPLET_DIR/BUILD/.env.example" ]; then
    echo -e "${BLUE}📝 Creating .env.example...${NC}"
    cat > "$DROPLET_DIR/BUILD/.env.example" << 'EOF'
# Environment variables template
# Copy to .env and fill with actual values

# Add environment variables as needed during BUILD phase
EOF
fi

# Create basic test file
if [ ! -f "$DROPLET_DIR/BUILD/tests/test_basic.py" ]; then
    echo -e "${BLUE}📝 Creating test template...${NC}"
    mkdir -p "$DROPLET_DIR/BUILD/tests"
    cat > "$DROPLET_DIR/BUILD/tests/test_basic.py" << 'EOF'
"""
Basic tests for [DROPLET_NAME]
Add more tests as you implement functionality
"""

import pytest

def test_placeholder():
    """Placeholder test - replace with actual tests"""
    assert True

# Add more tests based on success criteria in SPECS.md
EOF
    sed -i '' "s/\[DROPLET_NAME\]/$DROPLET_NAME/g" "$DROPLET_DIR/BUILD/tests/test_basic.py"
fi

# Create basic src structure
if [ ! -f "$DROPLET_DIR/BUILD/src/__init__.py" ]; then
    echo -e "${BLUE}📝 Creating src structure...${NC}"
    touch "$DROPLET_DIR/BUILD/src/__init__.py"
fi

# Create deployment log template in PRODUCTION
if [ ! -f "$DROPLET_DIR/PRODUCTION/deployment_log.md" ]; then
    echo -e "${BLUE}📝 Creating deployment log...${NC}"
    cat > "$DROPLET_DIR/PRODUCTION/deployment_log.md" << 'EOF'
# Deployment Log - [DROPLET_NAME]

## Deployments

### [DATE] - Initial Setup
- Status: Pending
- Version: 0.0.1
- Notes: Awaiting completion of BUILD phase

---

Add deployment entries here when deploying to production.
EOF
    sed -i '' "s/\[DROPLET_NAME\]/$DROPLET_NAME/g" "$DROPLET_DIR/PRODUCTION/deployment_log.md"
    sed -i '' "s/\[DATE\]/$(date +%Y-%m-%d)/g" "$DROPLET_DIR/PRODUCTION/deployment_log.md"
fi

# Success!
echo ""
echo -e "${GREEN}✅ Droplet '$DROPLET_NAME' created successfully!${NC}"
echo ""
echo -e "${BLUE}📁 Structure:${NC}"
tree -L 2 "$DROPLET_DIR" 2>/dev/null || ls -la "$DROPLET_DIR"
echo ""
echo -e "${YELLOW}📍 Next Steps:${NC}"
echo "   1. Fill out SPECS.md completely"
echo "   2. Start BUILD phase (implement in BUILD/src/)"
echo "   3. Update README.md with progress"
echo "   4. Deploy to PRODUCTION when ready"
echo ""
echo -e "${BLUE}📝 Edit SPECS:${NC}"
echo "   cat $DROPLET_DIR/SPECS.md"
echo ""
echo -e "${BLUE}📊 Check Progress:${NC}"
echo "   cat $DROPLET_DIR/README.md"
echo ""
echo -e "${GREEN}🏗️ Assembly Line: SPECS → BUILD → README → PRODUCTION${NC}"
