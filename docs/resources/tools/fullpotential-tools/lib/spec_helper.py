#!/usr/bin/env python3
"""
SPEC Generator Helper
Assists with generating SPECs from architect intent
"""

import os
from datetime import datetime
from typing import Dict, List


class SpecHelper:
    """Helper for generating droplet SPECs"""

    DROPLET_TEMPLATES = {
        1: {
            'name': 'Registry',
            'purpose': 'Identity, SSOT, JWT issuer',
            'key_features': [
                'Service registration and discovery',
                'JWT token generation and validation',
                'Endpoint directory management',
                'Status tracking for all droplets'
            ],
            'tech_stack': 'FastAPI, PostgreSQL, JWT (RS256)',
            'endpoints': ['/register', '/token', '/services', '/health']
        },
        10: {
            'name': 'Orchestrator',
            'purpose': 'Task routing, messaging',
            'key_features': [
                'Inter-droplet task routing',
                'Message queue management',
                'Heartbeat collection',
                'State coordination'
            ],
            'tech_stack': 'FastAPI, Redis, PostgreSQL',
            'endpoints': ['/route', '/message', '/heartbeat', '/health']
        },
        3: {
            'name': 'Proxy Manager',
            'purpose': 'Routing, SSL, domains',
            'key_features': [
                'Automatic reverse proxy configuration',
                'SSL certificate management (Let\'s Encrypt)',
                'Dynamic port allocation',
                'Domain routing'
            ],
            'tech_stack': 'FastAPI, Nginx, Certbot, Docker',
            'endpoints': ['/configure', '/ssl', '/routes', '/health']
        }
    }

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate_spec_from_intent(self, droplet_id: int, architect_intent: str) -> str:
        """Generate SPEC from architect's intent"""

        template = self.DROPLET_TEMPLATES.get(droplet_id)

        if not template:
            return self._generate_custom_spec(droplet_id, architect_intent)

        return self._generate_templated_spec(droplet_id, template, architect_intent)

    def _generate_templated_spec(self, droplet_id: int, template: Dict, architect_intent: str) -> str:
        """Generate SPEC using predefined template"""

        timestamp = datetime.utcnow().strftime('%Y-%m-%d')
        filename = f"SPEC_Droplet_{droplet_id}_{template['name'].replace(' ', '_')}_{timestamp}.md"
        spec_path = os.path.join(self.output_dir, filename)

        content = f"""# SPEC: Droplet #{droplet_id} - {template['name']}

**Version:** 1.0
**Date:** {timestamp}
**Status:** Draft

---

## 0. ARCHITECT INTENT

{architect_intent}

---

## 1. OVERVIEW

**Droplet Name:** {template['name']}
**Droplet ID:** #{droplet_id}
**Purpose:** {template['purpose']}

This droplet is a core component of the Full Potential AI system following the Sacred Loop architecture.

---

## 2. KEY FEATURES

"""

        for feature in template['key_features']:
            content += f"- {feature}\n"

        content += f"""
---

## 3. TECHNICAL STACK

**Primary Stack:** {template['tech_stack']}

**Compliance:**
- Universal Droplet Contract (UDC)
- Foundation Files standards
- Security Requirements

---

## 4. API ENDPOINTS

### Required UDC Endpoints

All droplets must implement:

```
GET  /health         - Health check
GET  /capabilities   - List droplet capabilities
GET  /state          - Current droplet state
GET  /dependencies   - List dependencies
POST /message        - Receive messages from Orchestrator
```

### Droplet-Specific Endpoints

"""

        for endpoint in template['endpoints']:
            if endpoint not in ['/health', '/capabilities', '/state', '/dependencies', '/message']:
                content += f"```\n{endpoint}\n```\n\n"

        content += """---

## 5. DATA MODEL

**Database:** PostgreSQL

**Core Entities:**

[Define your data models here based on the purpose]

---

## 6. INTEGRATION REQUIREMENTS

### Registry Integration
- Register on startup
- Obtain JWT token
- Report status updates

### Orchestrator Integration
- Send heartbeat every 60 seconds
- Listen for messages on /message endpoint
- Report task completion

### Security
- Use RS256 JWT from Registry
- Validate all incoming requests
- Use parameterized queries (SQL injection prevention)
- Environment variables for secrets (never hardcode)

---

## 7. DEPLOYMENT

**Container:** Docker
**Domain:** [droplet-name].fullpotential.ai
**Port:** Auto-assigned by Proxy Manager
**SSL:** Automated via Proxy Manager

**Environment Variables:**
```
REGISTRY_URL=
DATABASE_URL=
JWT_PUBLIC_KEY=
```

---

## 8. VERIFICATION CRITERIA

This droplet passes verification when:

- [ ] All UDC endpoints respond correctly
- [ ] All droplet-specific endpoints function
- [ ] Integrates with Registry successfully
- [ ] Sends heartbeats to Orchestrator
- [ ] Database migrations run successfully
- [ ] Docker container builds and runs
- [ ] Tests pass with >80% coverage
- [ ] Security scan shows no critical issues
- [ ] Code follows standards (black, ruff, type hints)
- [ ] README is complete with all sections

---

## 9. COPY-PASTE PROMPTS FOR APPRENTICE

### Setup Prompt

```
I'm building Droplet #{droplet_id} - {template['name']} for the Full Potential AI system.

I have uploaded 5 Foundation Files:
1. UDC_COMPLIANCE.md
2. TECH_STACK.md
3. SECURITY_REQUIREMENTS.md
4. CODE_STANDARDS.md
5. INTEGRATION_GUIDE.md

Please help me build this droplet following these files exactly.

Purpose: {template['purpose']}

Start by creating the project structure with FastAPI, following the tech stack in TECH_STACK.md.
```

### Feature Implementation Prompt

```
Now implement the core features:

"""

        for i, feature in enumerate(template['key_features'], 1):
            content += f"{i}. {feature}\n"

        content += f"""
Follow UDC_COMPLIANCE.md for all endpoints.
Follow SECURITY_REQUIREMENTS.md for authentication and data handling.
Follow CODE_STANDARDS.md for code quality.
```

### Testing Prompt

```
Now create comprehensive tests for all functionality:
- Test all UDC endpoints
- Test all droplet-specific endpoints
- Test Registry integration
- Test error handling
- Ensure >80% coverage

Follow CODE_STANDARDS.md for testing requirements.
```

### Documentation Prompt

```
Create a complete README.md with these sections:
- Overview
- Installation
- Configuration
- API Endpoints
- Development
- Testing
- Deployment

Ensure it's clear and complete for any developer to understand and deploy this droplet.
```

---

## 10. DEFINITION OF DONE

- All code committed to GitHub
- All tests passing
- README complete
- Dockerfile working
- HANDOFF.md created
- Ready for Verifier review

---

END OF SPEC
"""

        with open(spec_path, 'w') as f:
            f.write(content)

        return spec_path

    def _generate_custom_spec(self, droplet_id: int, architect_intent: str) -> str:
        """Generate SPEC for custom droplet"""

        timestamp = datetime.utcnow().strftime('%Y-%m-%d')
        filename = f"SPEC_Droplet_{droplet_id}_Custom_{timestamp}.md"
        spec_path = os.path.join(self.output_dir, filename)

        content = f"""# SPEC: Droplet #{droplet_id} - Custom Droplet

**Version:** 1.0
**Date:** {timestamp}
**Status:** Draft

---

## 0. ARCHITECT INTENT

{architect_intent}

---

## 1. OVERVIEW

**Droplet ID:** #{droplet_id}
**Purpose:** [To be defined based on intent]

---

## 2. KEY FEATURES

[Analyze the architect intent above and list key features]

---

## 3. TECHNICAL STACK

**Recommended Stack:** FastAPI, PostgreSQL, Docker

Follow:
- TECH_STACK.md for technology choices
- UDC_COMPLIANCE.md for required endpoints
- SECURITY_REQUIREMENTS.md for security
- CODE_STANDARDS.md for code quality
- INTEGRATION_GUIDE.md for system integration

---

## 4. API ENDPOINTS

### Required UDC Endpoints

All droplets must implement:

```
GET  /health         - Health check
GET  /capabilities   - List droplet capabilities
GET  /state          - Current droplet state
GET  /dependencies   - List dependencies
POST /message        - Receive messages from Orchestrator
```

### Custom Endpoints

[Define based on the architect intent]

---

## 5. INTEGRATION REQUIREMENTS

- Register with Registry on startup
- Send heartbeats to Orchestrator (60s interval)
- Use JWT authentication from Registry
- Follow integration patterns in INTEGRATION_GUIDE.md

---

## 6. VERIFICATION CRITERIA

- [ ] All UDC endpoints implemented
- [ ] Custom functionality complete
- [ ] Tests pass with >80% coverage
- [ ] Security compliant
- [ ] Code standards followed
- [ ] Documentation complete

---

## 7. COPY-PASTE PROMPTS

See templated droplets for example prompts.

---

END OF SPEC

NOTE: This is a custom droplet. The Architect should review and expand this SPEC before
assigning to an Apprentice.
"""

        with open(spec_path, 'w') as f:
            f.write(content)

        return spec_path

    def list_available_templates(self) -> List[Dict]:
        """List available droplet templates"""

        templates = []

        for droplet_id, template in self.DROPLET_TEMPLATES.items():
            templates.append({
                'id': droplet_id,
                'name': template['name'],
                'purpose': template['purpose']
            })

        return templates


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='SPEC Generator Helper')
    parser.add_argument('--list', action='store_true',
                       help='List available droplet templates')
    parser.add_argument('--droplet-id', type=int,
                       help='Droplet ID to generate SPEC for')
    parser.add_argument('--intent', type=str,
                       help='Architect intent (1-3 sentences)')
    parser.add_argument('--output-dir', default='../output/specs',
                       help='Output directory for SPECs')

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    helper = SpecHelper(args.output_dir)

    if args.list:
        print("📋 Available Droplet Templates:\n")
        templates = helper.list_available_templates()
        for template in templates:
            print(f"#{template['id']} - {template['name']}")
            print(f"   Purpose: {template['purpose']}\n")
        return

    if args.droplet_id and args.intent:
        print(f"📝 Generating SPEC for Droplet #{args.droplet_id}...")
        spec_path = helper.generate_spec_from_intent(args.droplet_id, args.intent)
        print(f"✅ SPEC generated: {spec_path}")
    else:
        print("❌ Error: Provide --droplet-id and --intent to generate SPEC")
        print("   Or use --list to see available templates")


if __name__ == '__main__':
    main()
