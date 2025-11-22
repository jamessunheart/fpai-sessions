# Architect Intent - Coordinator Droplet #11

**Droplet ID:** 11
**Droplet Name:** Coordinator
**Date:** November 14, 2025
**Step in Sacred Loop:** Step 3 Automation

---

## Vision

Automate Sacred Loop Step 3 (Coordinator) by creating a droplet that accepts a SPEC + Foundation Files and returns a fully-packaged, git-initialized, GitHub-ready repository for Apprentice to build.

**Current State:** Step 3 runs manual bash scripts (droplet-init.sh) that create folders, copy files, init git, create GitHub repos
**Desired State:** HTTP API that coordinates packaging in seconds, eliminating 10-15 minutes of manual setup per droplet

---

## Purpose

The Coordinator Droplet removes manual repository setup work by exposing a simple API that:
- Creates standardized droplet repository structure
- Copies SPEC + Foundation Files to docs/
- Initializes git with proper .gitignore
- Creates GitHub repository (optional)
- Returns package metadata for Apprentice

---

## Core Requirements

### API Endpoints

1. **POST /coordinator/package-droplet**
   - Input: `{ droplet_id, droplet_name, spec_content, foundation_files: {...}, create_github: bool }`
   - Creates repository structure at `/tmp/droplet-{id}-{name}` or configured path
   - Copies SPEC to `docs/SPEC.md`
   - Copies Foundation Files to `docs/foundation-files/`
   - Initializes git with .gitignore
   - Optionally creates GitHub repository
   - Returns: `{ repo_path, repo_url, files_created: [...] }`

2. **GET /coordinator/health** (UDC compliance)
   - Returns service health

3. **GET /coordinator/capabilities** (UDC compliance)
   - Returns: `{ can_create_repos, can_init_git, can_create_github, github_configured }`

4. **GET /coordinator/templates**
   - Lists available droplet templates
   - Returns: `{ templates: ["fastapi-basic", "fastapi-with-db", "nginx-proxy", ...] }`

### Features

- ✅ Standardized droplet repository structure
- ✅ Automatic SPEC + Foundation Files placement
- ✅ Git initialization with .gitignore (Python, __pycache__, .env, etc.)
- ✅ Optional GitHub repository creation
- ✅ Template support (future: different droplet types)
- ✅ UDC compliant (health, capabilities endpoints)
- ✅ Idempotent operations (can re-run safely)

---

## Technical Specification

### Stack
- **Framework:** FastAPI + Pydantic
- **Port:** 8300
- **Storage:** Local filesystem (configurable base path)
- **Git:** GitPython library for git operations
- **GitHub:** PyGithub library for GitHub API
- **Testing:** pytest with fixtures

### Repository Structure Created
```
droplet-{id}-{name}/
├── app/
│   ├── __init__.py
│   ├── main.py (empty template)
│   ├── models.py (empty template)
│   └── config.py (empty template)
├── tests/
│   ├── __init__.py
│   └── test_api.py (empty template)
├── docs/
│   ├── SPEC.md (from input)
│   └── foundation-files/
│       ├── 1-UDC_COMPLIANCE.md
│       ├── 2-TECH_STACK.md
│       ├── 3-INTEGRATION_GUIDE.md
│       ├── 4-CODE_STANDARDS.md
│       ├── 5-SECURITY_REQUIREMENTS.md
│       └── 6-Spec_Generator_Template.txt
├── Dockerfile (empty template)
├── requirements.txt (empty template)
├── README.md (auto-generated from SPEC)
├── .gitignore (Python standard)
└── .env.example (template)
```

### Configuration (.env)
```bash
COORDINATOR_PORT=8300
DROPLET_BASE_PATH=/Users/jamessunheart/Development
GITHUB_TOKEN=ghp_xxxxx (optional)
GITHUB_ORG=fullpotential-ai (optional)
FOUNDATION_FILES_PATH=/Users/jamessunheart/Development/AI FILES
```

---

## Integration Points

### With Sacred Loop
- Sacred Loop Step 2 generates SPEC → Coordinator packages it → Apprentice builds it
- Replaces manual bash script with HTTP API call

### With Registry
- After droplet is built, it gets registered in Registry
- No direct integration during packaging

### With GitHub
- Uses GitHub API to create repository
- Sets proper description, README, .gitignore
- Returns clone URL for Apprentice

---

## Success Criteria

1. **Functionality**
   - Can create droplet repository structure in < 5 seconds
   - Can initialize git successfully
   - Can create GitHub repository (if token configured)
   - All Foundation Files copied correctly

2. **UDC Compliance**
   - Has /coordinator/health endpoint
   - Has /coordinator/capabilities endpoint
   - Follows error response format
   - Has proper logging

3. **Testing**
   - Unit tests for all endpoints
   - Integration test for full packaging flow
   - Test coverage > 80%

4. **Documentation**
   - README with setup instructions
   - API documentation with examples
   - SPEC included

---

## Example Usage

### Package a New Droplet

```bash
curl -X POST http://localhost:8300/coordinator/package-droplet \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_id": 20,
    "droplet_name": "analytics-engine",
    "spec_content": "# SPEC for Analytics Engine\n...",
    "foundation_files": {
      "udc_compliance": "...",
      "tech_stack": "...",
      "integration_guide": "...",
      "code_standards": "...",
      "security_requirements": "..."
    },
    "create_github": true
  }'
```

**Response:**
```json
{
  "droplet_id": 20,
  "droplet_name": "analytics-engine",
  "repo_path": "/Users/jamessunheart/Development/droplet-20-analytics-engine",
  "repo_url": "https://github.com/fullpotential-ai/droplet-20-analytics-engine",
  "files_created": [
    "app/__init__.py",
    "app/main.py",
    "docs/SPEC.md",
    "docs/foundation-files/1-UDC_COMPLIANCE.md",
    "README.md",
    ".gitignore"
  ],
  "git_initialized": true,
  "github_created": true
}
```

---

## Time Savings

**Current (Manual):** 10-15 minutes per droplet
- Create folders manually
- Copy files manually
- Init git manually
- Create GitHub repo manually
- Create initial commit manually

**With Coordinator:** 10-30 seconds per droplet
- Single API call
- Everything automated
- Idempotent (can retry safely)

**Estimated Savings:** 10-14 minutes per droplet build

---

## Future Enhancements (v2)

- Multiple repository templates (FastAPI, React, Go, etc.)
- Custom folder structures via template config
- Automatic initial commit with proper message
- Branch protection setup
- CI/CD workflow file generation (.github/workflows)
- Slack/Discord notification on package creation

---

## Notes

- This droplet itself was built using the Sacred Loop process
- Acts as a force multiplier for future droplet creation
- Reduces Sacred Loop Step 3 from 10-15 minutes to < 1 minute
- Makes droplet creation more consistent and less error-prone

---

**Status:** Ready for SPEC Generation (Step 2)
**Next Step:** Run `fp-tools spec --droplet-id 11 --intent INTENT_Coordinator_Droplet_11.md`

🌐⚡💎 Building the Future
