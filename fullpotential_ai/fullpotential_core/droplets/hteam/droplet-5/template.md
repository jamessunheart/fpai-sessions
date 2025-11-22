README TEMPLATE Fill up & store in home
directly of droplet repo
Keep updated as the Single Source of Truth (SSOT) of this droplet.
UDC v1.0
Droplet #[ID]: [Droplet Name]
Repo: [droplet-X-name]
Purpose: [One-sentence TL;DR of the droplet's function, e.g., "Automates the Coordinator role by
managing the sprint pipeline."]
1. IDENTITY & STATUS
• Droplet ID: [#ID, e.g., 18]
• Function: [One-sentence description, e.g., "Manages task routing and workflow
management for the mesh."]
• Steward: [@GitHubUsername]
• Status: [OPERATIONAL | IN_DEVELOPMENT | FAILED | DEPRECATED]
• Live Endpoint: https://[droplet].fullpotential.ai
• Healthcheck: https://[droplet].fullpotential.ai/health
2. SYSTEM CONTEXT
• Upstream Dependencies: [List of droplets this one depends on, e.g., #1 Registry]
• Downstream Outputs: [List of droplets depending on this one, e.g., #2 Dashboard, #19
Verifier]
• Related Droplets: [Other interacting droplets]
3. ASSEMBLY LINE SPRINT (Current Work)
Tracks current development state aligned with the SSoT.
• Current Sprint: [Feature name, e.g., "GitHub PR Monitoring"]
• Spec: [Link to SPEC.md]
• Apprentice: [@builder]
• Verifier: [@verifier]
• PR / Branch: [Link to active PR or branch]
• Cost / Time (Reported): [e.g., "5 h (Apprentice), 1.5 h (Verifier)"]
4. TECHNICAL SSOT (How to Run)
A. Core Foundation Files
Built against and must adhere to:
• UDC_COMPLIANCE.md
• TECH_STACK.md
• SECURITY_REQUIREMENTS.md
• CODE_STANDARDS.md
• INTEGRATION_GUIDE.md
B. Repository Map
/app/
├── api/
│ └── routes/
├── models/
├── services/
├── utils/
├── config.py
└── main.py
/tests/
├── test_health.py
└── test_logic.py
.env.example
Dockerfile
HANDOFF.md
README.md
SPEC.md
requirements.txt
C. AI Context
• Primary Model: [e.g., Claude 3.5 Sonnet]
• Foundation Files Used: 5 (UDC, TECH_STACK, SECURITY, CODE_STANDARDS,
INTEGRATION_GUIDE)
• AI Prompts Stored: [Yes (in SPEC.md) / No]
D. Setup & Run
1. 1 Clone the repository
2. 2 Install dependencies
pip install -r requirements.txt
3. 3
4. 4 Copy the environment template
cp .env.example .env
5. 5
6. 6 Fill in credentials in .env
7. 7 Run locally
uvicorn app.main:app --reload
8. 8
9. 9 Run tests
pytest
10. 10
5. VERIFICATION HISTORY
Date Verifier Branch/PR Result Notes
2025-11-11 @verifier-name pr-1
PASS Deployed to production
2025-11-10 @verifier-name branch-a
FAIL UDC compliance failure
6. NOTES & IMPROVEMENTS
• [Apprentice Note 2025-11-10]: Had trouble with GitHub webhook signature verification;
fixed in auth.py.
• [Verifier Note 2025-11-11]: Missed test case for empty payloads; logic sound, approved
with minor fix.
Related Docs:
ASSEMBLY_LINE_SOP.md · COORDINATOR_HANDBOOK.md · VERIFICATION_PROTOCOL.md