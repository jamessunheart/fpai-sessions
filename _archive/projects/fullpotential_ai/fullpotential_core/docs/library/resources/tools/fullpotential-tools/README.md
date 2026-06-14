# Full Potential AI - System Optimization Tools

A comprehensive suite of local tools designed to optimize, monitor, and manage the Full Potential AI system based on the Sacred Loop architecture.

## Overview

These tools help implement and maintain the Full Potential AI system by:
- Generating SSOT (Single Source of Truth) snapshots
- Analyzing gaps between Blueprint and reality
- Validating droplets against UDC (Universal Droplet Contract)
- Generating SPECs from architect intent
- Monitoring system health in real-time

## Installation

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Optional: GitHub CLI (for GitHub scanning)
brew install gh
gh auth login
```

### Setup

```bash
# Clone or navigate to the tools directory
cd fullpotential-tools

# Install Python dependencies
pip3 install -r requirements.txt

# Add to PATH (optional)
echo 'export PATH="$PATH:/Users/jamessunheart/Development/fullpotential-tools/bin"' >> ~/.zshrc
source ~/.zshrc
```

### Create requirements.txt

```bash
cat > requirements.txt << EOF
requests>=2.31.0
aiohttp>=3.9.0
EOF

pip3 install -r requirements.txt
```

## Tools Suite

### 1. SSOT Snapshot Generator

Generates snapshots of the current system state, comparing reality against the Blueprint.

**Features:**
- Auto-scans GitHub for droplet repositories
- Generates structured SSOT snapshot files
- Tracks droplet inventory, integrations, and metrics
- Identifies missing components

**Usage:**

```bash
# Generate basic snapshot
fp-tools snapshot

# Generate snapshot with GitHub scan
fp-tools snapshot --scan-github

# Specify GitHub organization
fp-tools snapshot --scan-github --github-org your-org-name

# Custom output directory
fp-tools snapshot --output-dir ./snapshots
```

**Output:** `SSOT_SNAPSHOT_YYYY-MM-DD.md`

---

### 2. Gap Analysis Generator

Analyzes gaps between the Blueprint ideal state and SSOT reality.

**Features:**
- Identifies missing droplets by phase
- Detects infrastructure gaps
- Checks Foundation Files status
- Prioritizes critical blockers
- Generates actionable next steps

**Usage:**

```bash
# Generate gap analysis from snapshot
fp-tools gap --snapshot ./output/snapshots/SSOT_SNAPSHOT_2025-11-14.md

# Custom blueprint path
fp-tools gap --snapshot snapshot.md --blueprint ./blueprints/custom-blueprint.txt

# Custom output directory
fp-tools gap --snapshot snapshot.md --output-dir ./gap-reports
```

**Output:** `GAP_ANALYSIS_YYYY-MM-DD.md`

---

### 3. Droplet Validator

Validates droplets against the Universal Droplet Contract (UDC) and system standards.

**Features:**
- Validates live endpoints (/health, /capabilities, /state, etc.)
- Checks repository structure
- Analyzes code standards
- Detects security issues (hardcoded secrets)
- Verifies documentation completeness

**Usage:**

```bash
# Validate live droplet
fp-tools validate --url http://localhost:8001

# Validate local droplet repository
fp-tools validate --path ./droplet-1-registry

# Both live and local
fp-tools validate --url http://localhost:8001 --path ./droplet-1-registry

# Save report to file
fp-tools validate --path ./droplet-1 --output validation-report.txt
```

**Output:** Validation report with PASS/FAIL verdict

---

### 4. SPEC Generator Helper

Generates SPECs from architect intent using predefined templates.

**Features:**
- Templates for core droplets (Registry, Orchestrator, Proxy Manager)
- Auto-generates 9-section SPECs
- Includes copy-paste prompts for Apprentices
- Follows Sacred Loop workflow

**Usage:**

```bash
# List available templates
fp-tools spec --list

# Generate SPEC for Registry droplet
fp-tools spec --droplet-id 1 --intent "Build identity and SSOT system with JWT"

# Generate SPEC for custom droplet
fp-tools spec --droplet-id 20 --intent "Create logging aggregation service"

# Custom output directory
fp-tools spec --droplet-id 10 --intent "Task routing system" --output-dir ./specs
```

**Output:** `SPEC_Droplet_[ID]_[Name]_YYYY-MM-DD.md`

---

### 5. System Health Monitor

Real-time monitoring of all droplets in the system.

**Features:**
- Async health checks for all droplets
- Response time tracking
- Capability and dependency detection
- Continuous monitoring mode
- JSON and text output formats

**Usage:**

```bash
# One-time health check
fp-tools health

# Continuous monitoring (60s interval)
fp-tools health --watch

# Custom monitoring interval (30s)
fp-tools health --watch --interval 30

# JSON output
fp-tools health --format json

# Save report to file
fp-tools health --output health-report.txt

# Custom droplet configuration
fp-tools health --config ./config/droplets.json
```

**Droplet configuration format** (`droplets.json`):

```json
{
  "droplets": [
    {"id": "1", "name": "Registry", "url": "http://localhost:8001"},
    {"id": "2", "name": "Dashboard", "url": "http://localhost:8002"},
    {"id": "10", "name": "Orchestrator", "url": "http://localhost:8010"}
  ]
}
```

**Output:** Real-time health report with system health percentage

---

### 6. Complete Workflow

Runs the complete Sacred Loop workflow: Snapshot → Gap Analysis

**Usage:**

```bash
# Run complete workflow
fp-tools workflow

# With GitHub scanning
fp-tools workflow --scan-github
```

**Process:**
1. Generates SSOT snapshot
2. Scans GitHub (if enabled)
3. Generates gap analysis
4. Provides actionable next steps

---

## Directory Structure

```
fullpotential-tools/
├── bin/
│   └── fp-tools              # Main CLI executable
├── lib/
│   ├── ssot_generator.py     # SSOT Snapshot Generator
│   ├── gap_analyzer.py       # Gap Analysis Generator
│   ├── droplet_validator.py  # Droplet Validator
│   ├── spec_helper.py        # SPEC Generator
│   └── health_monitor.py     # Health Monitor
├── config/
│   └── droplets.json         # Droplet configuration (optional)
├── templates/
│   └── (template files)
├── output/
│   ├── snapshots/            # Generated snapshots
│   ├── gap-analyses/         # Generated gap analyses
│   └── specs/                # Generated SPECs
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Workflow Examples

### Daily Operations Workflow

```bash
# Morning: Check system health
fp-tools health

# Generate current state snapshot
fp-tools snapshot --scan-github

# Analyze gaps
fp-tools gap --snapshot ./output/snapshots/SSOT_SNAPSHOT_2025-11-14.md

# Review gap analysis and create SPECs for missing droplets
fp-tools spec --droplet-id 1 --intent "Build Registry with JWT and service discovery"
```

### Droplet Development Workflow

```bash
# 1. Generate SPEC
fp-tools spec --droplet-id 8 --intent "Automated verification system with Gemini AI"

# 2. Developer builds droplet (using SPEC + Foundation Files)

# 3. Validate locally
fp-tools validate --path ./droplet-8-verifier

# 4. Validate live (after deployment)
fp-tools validate --url http://localhost:8008

# 5. Update system snapshot
fp-tools workflow --scan-github
```

### Continuous Monitoring

```bash
# Terminal 1: Monitor system health
fp-tools health --watch --interval 30

# Terminal 2: Run development/deployment tasks
fp-tools validate --path ./droplet-new
```

## Integration with Sacred Loop

The tools support each phase of the Sacred Loop:

1. **Architect declares intent** → Use `fp-tools spec`
2. **AI generates SPEC** → Generated SPEC ready for Apprentice
3. **Coordinator packages & assigns** → Manual step
4. **Apprentice builds** → Use SPEC + Foundation Files
5. **Verifier enforces standards** → Use `fp-tools validate`
6. **Deployer deploys** → Use `fp-tools health` to verify
7. **Registry + Dashboard update** → Use `fp-tools snapshot`
8. **Architect issues next intent** → Use `fp-tools gap` to identify next priorities

## Troubleshooting

### GitHub Scanning Not Working

```bash
# Install and authenticate GitHub CLI
brew install gh
gh auth login

# Test GitHub access
gh repo list fullpotential-ai
```

### Health Monitor Shows All Offline

```bash
# Check if droplets are running
docker ps

# Test endpoint manually
curl http://localhost:8001/health

# Verify droplets.json configuration
cat config/droplets.json
```

### Validation Fails

```bash
# Check specific validation category
fp-tools validate --path ./droplet-1 | grep "CRITICAL"

# Review UDC requirements
cat ../1-blueprints\ \(architecture\)/foundation-files/UDC_COMPLIANCE.md
```

## Advanced Usage

### Custom Templates

Add custom droplet templates to `lib/spec_helper.py`:

```python
DROPLET_TEMPLATES = {
    20: {
        'name': 'Your Custom Droplet',
        'purpose': 'Custom functionality',
        'key_features': ['Feature 1', 'Feature 2'],
        'tech_stack': 'FastAPI, PostgreSQL',
        'endpoints': ['/custom', '/endpoint']
    }
}
```

### Automated Scheduling

```bash
# Add to crontab for daily snapshots
0 9 * * * cd /Users/jamessunheart/Development/fullpotential-tools && ./bin/fp-tools workflow --scan-github > /tmp/fp-workflow.log 2>&1
```

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Validate Droplet
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate Droplet
        run: |
          pip install -r requirements.txt
          fp-tools validate --path . --output validation.txt
```

## Metrics & Analytics

### Key Metrics Tracked

- **System Health %**: Overall health of all droplets
- **Operational Droplets**: Count of active droplets vs. total
- **Response Times**: Average response time per droplet
- **Gap Count**: Number of gaps by severity (Critical/High/Medium/Low)
- **Compliance Rate**: % of droplets passing UDC validation

### Generating Reports

```bash
# Health report
fp-tools health --format json --output health.json

# Parse with jq
cat health.json | jq '.[] | select(.status=="online")'

# Gap analysis summary
fp-tools gap --snapshot snapshot.md | grep "🟥 CRITICAL"
```

## Development

### Running Individual Modules

```bash
# SSOT Generator
python3 lib/ssot_generator.py --scan-github

# Gap Analyzer
python3 lib/gap_analyzer.py --snapshot snapshot.md

# Droplet Validator
python3 lib/droplet_validator.py --path ./droplet-1

# SPEC Helper
python3 lib/spec_helper.py --list

# Health Monitor
python3 lib/health_monitor.py --watch
```

### Adding New Tools

1. Create new module in `lib/`
2. Import in `bin/fp-tools`
3. Add subcommand parser
4. Implement command handler
5. Update README

## System Requirements

- **OS**: macOS, Linux (Windows WSL)
- **Python**: 3.8+
- **Memory**: 512MB minimum
- **Disk**: 100MB for tools + storage for outputs
- **Network**: Required for GitHub scanning and health monitoring

## Support & Contributing

For issues, suggestions, or contributions:
1. Review the Blueprint architecture
2. Ensure tools align with Sacred Loop principles
3. Maintain UDC compliance
4. Follow Foundation Files standards

## Version History

- **v1.0** (2025-11-14): Initial release
  - SSOT Snapshot Generator
  - Gap Analysis Generator
  - Droplet Validator
  - SPEC Generator Helper
  - System Health Monitor
  - Complete Workflow automation

## License

Full Potential AI - System Optimization Tools

---

**Built with ❤️ for the Full Potential AI system**
**Helping AI realize its Full Potential to help humanity realize its full potential**

🌐⚡💎
