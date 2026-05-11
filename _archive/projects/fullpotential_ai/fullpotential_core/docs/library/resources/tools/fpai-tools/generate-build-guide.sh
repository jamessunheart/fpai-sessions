#!/bin/bash

# BUILD GUIDE GENERATOR
# Purpose: Auto-generate consolidated build instructions from SPEC + Foundation Files
# Usage: ./generate-build-guide.sh <droplet-directory>
# Eliminates copy-paste work for Apprentice developers

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# Check arguments
if [ -z "$1" ]; then
    print_error "Usage: $0 <droplet-directory>"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/droplet-10-orchestrator"
    echo "  $0 ../droplet-15-recruiter"
    exit 1
fi

DROPLET_DIR="$1"

# Validate directory
if [ ! -d "$DROPLET_DIR" ]; then
    print_error "Directory not found: $DROPLET_DIR"
    exit 1
fi

DROPLET_DIR="$(cd "$DROPLET_DIR" && pwd)"
DROPLET_NAME="$(basename "$DROPLET_DIR")"

print_header "Build Guide Generator"
echo ""
print_info "Droplet: $DROPLET_NAME"
print_info "Directory: $DROPLET_DIR"
echo ""

# Check for required files
SPEC_FILE="${DROPLET_DIR}/docs/SPEC.md"
FOUNDATION_DIR="${DROPLET_DIR}/docs/foundation-files"

if [ ! -f "$SPEC_FILE" ]; then
    print_error "SPEC.md not found at: $SPEC_FILE"
    exit 1
fi

if [ ! -d "$FOUNDATION_DIR" ]; then
    print_warning "Foundation files directory not found - some sections will be missing"
fi

# Generate BUILD_GUIDE.md
OUTPUT_FILE="${DROPLET_DIR}/BUILD_GUIDE.md"

print_info "Generating build guide..."

cat > "$OUTPUT_FILE" << 'HEADER'
# 🛠️ BUILD GUIDE - Zero Copy-Paste Required

**Purpose:** All build instructions in one place - no more hunting for context!

**How to Use:**
1. Upload this entire `docs/` folder to Claude Project (one upload, all context)
2. Or: Copy each prompt section below sequentially
3. Follow the step-by-step prompts
4. Verify with test commands
5. Deploy when tests pass

---

## 📋 Quick Start

```bash
# 1. Upload to Claude Project
# Just drag the docs/ folder into Claude Projects

# 2. Or start with this prompt:
# "I need to build this service. I have the SPEC and Foundation Files.
#  Let's start with the project structure and core models."
```

---

HEADER

# Add SPEC content
cat >> "$OUTPUT_FILE" << 'SPEC_HEADER'
## 📄 SPEC (Specification)

**Location:** `docs/SPEC.md`

SPEC_HEADER

cat "$SPEC_FILE" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << 'SPEC_FOOTER'

---

SPEC_FOOTER

# Add Foundation Files references
cat >> "$OUTPUT_FILE" << 'FOUNDATION_HEADER'
## 📚 Foundation Files

**Location:** `docs/foundation-files/`

These files provide critical context for building the service:

FOUNDATION_HEADER

# List Foundation Files with brief descriptions
if [ -d "$FOUNDATION_DIR" ]; then
    for file in "$FOUNDATION_DIR"/*.md "$FOUNDATION_DIR"/*.txt; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            cat >> "$OUTPUT_FILE" << FOUND_FILE
### $(basename "$file" | sed 's/[0-9]-//g' | sed 's/_/ /g' | sed 's/.md//g' | sed 's/.txt//g')

**File:** \`docs/foundation-files/$filename\`

FOUND_FILE
            # Add first 10 lines as preview
            echo '```' >> "$OUTPUT_FILE"
            head -10 "$file" >> "$OUTPUT_FILE"
            echo '...' >> "$OUTPUT_FILE"
            echo '```' >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
        fi
    done
fi

# Add implementation prompts
cat >> "$OUTPUT_FILE" << 'PROMPTS'
---

## 🎯 STEP-BY-STEP BUILD PROMPTS

Copy these prompts sequentially to Claude Code. Each builds on the previous.

### Prompt 1: Project Setup & Models

```
I'm building a new Full Potential AI service. Here's what I need:

Context:
- SPEC: See docs/SPEC.md above
- Foundation Files: See docs/foundation-files/ for UDC compliance, tech stack, standards

Task 1 - Project Structure:
Create the following structure:
app/
  __init__.py
  main.py          # FastAPI app with UDC endpoints
  models.py        # Pydantic models
  config.py        # Configuration
tests/
  __init__.py
  test_endpoints.py
requirements.txt
Dockerfile
.env.example
README.md

Task 2 - Models:
Based on the SPEC, create all Pydantic models in app/models.py:
- Request/Response models
- UDC-compliant models (HealthResponse, CapabilitiesResponse, etc.)
- Any domain-specific models

Task 3 - Configuration:
Create app/config.py with:
- Environment variable loading
- Service configuration
- Logging setup

Follow Foundation Files for:
- UDC compliance (5 required endpoints)
- Tech stack (FastAPI, Pydantic, Python 3.11+)
- Code standards (type hints, docstrings)
```

---

### Prompt 2: UDC Compliance Endpoints

```
Now implement the 5 required UDC endpoints in app/main.py:

Required Endpoints:
1. GET /health - Service health status
2. GET /capabilities - What this service provides
3. GET /state - Resource usage and metrics
4. GET /dependencies - Service dependencies
5. POST /message - Inter-service messaging

Requirements:
- Return proper UDC-compliant response models
- Include service name, version, timestamp
- Add proper error handling
- Follow docs/foundation-files/1-UDC_COMPLIANCE.md

Start the FastAPI app and ensure all endpoints return valid responses.
```

---

### Prompt 3: Core Business Logic

```
Based on the SPEC, implement the core business logic:

Reference: docs/SPEC.md for exact requirements

For each feature in the SPEC:
1. Create the endpoint route
2. Implement request validation
3. Add business logic
4. Return proper response model
5. Add error handling
6. Include logging

Follow:
- docs/foundation-files/2-TECH_STACK.md for tech choices
- docs/foundation-files/4-CODE_STANDARDS.md for quality
- docs/foundation-files/5-SECURITY_REQUIREMENTS.md for security

Implement incrementally - one feature at a time, test each.
```

---

### Prompt 4: Testing

```
Create comprehensive tests in tests/test_endpoints.py:

Test Coverage Required:
1. All UDC endpoints (health, capabilities, state, dependencies, message)
2. All business logic endpoints
3. Error cases (400, 404, 500 responses)
4. Edge cases from SPEC

Use pytest with FastAPI TestClient.

Target: 80%+ code coverage

Run tests:
pytest tests/ --cov=app --cov-report=term
```

---

### Prompt 5: Docker & Deployment

```
Create production-ready deployment files:

1. Dockerfile:
   - Python 3.11+ base
   - Copy requirements.txt and install
   - Copy app/
   - Expose correct port (check SPEC)
   - CMD to run uvicorn

2. .env.example:
   - All configuration variables
   - Sensible defaults
   - Comments explaining each

3. README.md:
   - Service description
   - Quick start
   - API endpoints
   - Development setup
   - Deployment instructions

Reference: docs/foundation-files/3-INTEGRATION_GUIDE.md
```

---

### Prompt 6: Code Quality & Standards

```
Run final quality checks:

1. Format code:
   black app/ tests/
   isort app/ tests/

2. Lint:
   ruff check app/ tests/

3. Type check:
   mypy app/

4. Security scan:
   bandit -r app/

5. Run full test suite:
   pytest tests/ --cov=app --cov-report=html

Fix any issues found. Aim for:
- 100% passing tests
- 80%+ code coverage
- Zero security vulnerabilities
- Clean linting (or justified exceptions)
```

---

## ✅ VERIFICATION CHECKLIST

Before marking as complete, verify:

### UDC Compliance
- [ ] GET /health returns valid HealthResponse
- [ ] GET /capabilities returns features and dependencies
- [ ] GET /state returns resource usage
- [ ] GET /dependencies returns required/optional deps
- [ ] POST /message handles inter-service messages

### Business Logic
- [ ] All features from SPEC implemented
- [ ] Request validation works
- [ ] Responses match SPEC models
- [ ] Error handling is comprehensive

### Testing
- [ ] All endpoints tested
- [ ] 80%+ code coverage
- [ ] Tests pass: `pytest tests/`
- [ ] No test failures

### Code Quality
- [ ] Black formatting: `black --check app/ tests/`
- [ ] Ruff linting: `ruff check app/ tests/`
- [ ] Type hints: `mypy app/`
- [ ] Security: `bandit -r app/`

### Deployment
- [ ] Dockerfile builds: `docker build -t service .`
- [ ] Container runs: `docker run -p 8000:8000 service`
- [ ] Health check works: `curl http://localhost:8000/health`
- [ ] .env.example has all variables

### Documentation
- [ ] README.md complete
- [ ] API endpoints documented
- [ ] Setup instructions clear

---

## 🚀 LOCAL TESTING

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m app.main

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/capabilities

# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 📦 READY FOR DEPLOYMENT

Once all checks pass:

```bash
# Commit changes
git add .
git commit -m "Implement [service-name] - SPEC complete

All features implemented per SPEC
UDC compliant (5 endpoints)
Tests: 80%+ coverage
Quality: All checks pass

🌐⚡💎 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to GitHub
git push origin main

# Deploy
cd ../agents/services/ops
./deploy-to-server.sh [service-name]
```

---

## 💡 TIPS

**For Claude Projects:**
1. Upload entire `docs/` folder at once
2. Reference files by path: "See docs/SPEC.md section X"
3. Build incrementally - test each feature

**For Copy-Paste:**
1. Copy Prompt 1 → implement → test
2. Copy Prompt 2 → implement → test
3. Repeat for each prompt
4. Run verification checklist

**Common Issues:**
- Port conflicts: Check PORTS.md for assigned port
- Import errors: Verify __init__.py files exist
- Type errors: Add proper type hints
- Test failures: Check SPEC requirements match implementation

---

**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Droplet:** $DROPLET_NAME
**SPEC:** docs/SPEC.md
**Foundation Files:** docs/foundation-files/

🌐⚡💎
PROMPTS

print_success "Build guide generated: $OUTPUT_FILE"

# Also create a CLAUDE_PROJECT_README.md for uploading to Claude Projects
CLAUDE_README="${DROPLET_DIR}/docs/CLAUDE_PROJECT_README.md"

cat > "$CLAUDE_README" << README
# 📁 Claude Project Setup

## Quick Upload

Drag this entire \`docs/\` folder into Claude Projects.

## What's Included

- **SPEC.md** - Complete service specification
- **foundation-files/** - UDC compliance, tech stack, standards, security
- **CLAUDE_PROJECT_README.md** - This file

## First Prompt

After uploading, start with:

\`\`\`
I need to build this service based on the SPEC in docs/SPEC.md.

Context files in docs/foundation-files/:
- UDC compliance requirements
- Tech stack specifications
- Integration guidelines
- Code standards
- Security requirements

Let's start by creating the project structure with:
- FastAPI app with UDC endpoints
- Pydantic models
- Tests
- Docker deployment

Follow the SPEC exactly and maintain UDC compliance.
\`\`\`

## Alternative

See \`../BUILD_GUIDE.md\` for step-by-step prompts if you prefer sequential copy-paste.

---

**Build Time Estimate:** 2-3 hours with AI assistance
**Manual Build Time:** 6-8 hours

🌐⚡💎
README

print_success "Claude Project readme created: $CLAUDE_README"

echo ""
print_header "✅ BUILD GUIDE COMPLETE"
echo ""
print_info "Files created:"
echo "  1. $OUTPUT_FILE"
echo "  2. $CLAUDE_README"
echo ""
print_info "Usage Options:"
echo ""
echo "  Option A - Claude Projects (Recommended):"
echo "    1. Open Claude Projects"
echo "    2. Create new project"
echo "    3. Upload: ${DROPLET_DIR}/docs/ folder"
echo "    4. Start with prompt from CLAUDE_PROJECT_README.md"
echo ""
echo "  Option B - Sequential Copy-Paste:"
echo "    1. Open: $OUTPUT_FILE"
echo "    2. Copy Prompt 1 → implement → test"
echo "    3. Copy Prompt 2 → implement → test"
echo "    4. Repeat for all prompts"
echo ""
echo "  Option C - AI-Assisted Command Line:"
echo "    claude --project ${DROPLET_DIR}/docs/"
echo ""
print_success "Ready to build with ZERO copy-paste friction! 🚀"
echo ""
