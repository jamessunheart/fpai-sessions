# Full Potential AI Tools - Quick Start Guide

## Installation (5 minutes)

```bash
cd fullpotential-tools
./setup.sh
```

## Essential Commands

### 1. Check System Health
```bash
fp-tools health
```

### 2. Generate Complete Workflow (Snapshot + Gap Analysis)
```bash
fp-tools workflow --scan-github
```

### 3. Validate a Droplet
```bash
# Local validation
fp-tools validate --path ./my-droplet

# Live validation
fp-tools validate --url http://localhost:8001
```

### 4. Generate SPEC for New Droplet
```bash
# List available templates
fp-tools spec --list

# Generate SPEC
fp-tools spec --droplet-id 1 --intent "Build identity system with JWT tokens"
```

## Common Workflows

### Morning Routine
```bash
# 1. Check system health
fp-tools health

# 2. Generate daily snapshot
fp-tools workflow --scan-github

# 3. Review gap analysis
cat output/gap-analyses/GAP_ANALYSIS_*.md
```

### Building New Droplet
```bash
# 1. Generate SPEC
fp-tools spec --droplet-id 8 --intent "Automated verification with Gemini"

# 2. Build droplet (manual - follow SPEC)

# 3. Validate locally
fp-tools validate --path ./droplet-8-verifier

# 4. Deploy (manual)

# 5. Validate live
fp-tools validate --url http://localhost:8008

# 6. Update system snapshot
fp-tools snapshot --scan-github
```

### Continuous Monitoring
```bash
# Watch mode (updates every 60s)
fp-tools health --watch
```

## Output Files

All generated files are in `output/`:

```
output/
├── snapshots/SSOT_SNAPSHOT_2025-11-14.md
├── gap-analyses/GAP_ANALYSIS_2025-11-14.md
└── specs/SPEC_Droplet_1_Registry_2025-11-14.md
```

## Troubleshooting

### "fp-tools: command not found"
```bash
# Use full path
./bin/fp-tools --help

# Or add to PATH
export PATH="$PATH:$(pwd)/bin"
```

### GitHub Scanning Fails
```bash
# Install GitHub CLI
brew install gh

# Authenticate
gh auth login
```

### Health Monitor Shows All Offline
```bash
# Check if droplets are running
docker ps

# Update config with correct URLs
nano config/droplets.json
```

## Next Steps

1. Read the full [README.md](README.md)
2. Review the [Blueprint](../1-blueprints%20(architecture)/1-SYSTEM-BLUEPRINT.txt)
3. Generate your first SPEC
4. Build your first droplet

## Support

For more information, see:
- README.md - Complete documentation
- 1-SYSTEM-BLUEPRINT.txt - System architecture
- Foundation Files - Standards and requirements

🌐⚡💎
