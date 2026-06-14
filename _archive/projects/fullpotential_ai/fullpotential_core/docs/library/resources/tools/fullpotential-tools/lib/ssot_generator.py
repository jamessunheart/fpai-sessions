#!/usr/bin/env python3
"""
SSOT Snapshot Generator
Generates SSOT snapshots based on template and current system state
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import subprocess


class SSOTGenerator:
    """Generate SSOT snapshots for the Full Potential AI system"""

    def __init__(self, blueprints_dir: str, output_dir: str):
        self.blueprints_dir = blueprints_dir
        self.output_dir = output_dir
        self.snapshot_date = datetime.utcnow()

    def generate_snapshot(self, droplet_data: Optional[Dict] = None) -> str:
        """Generate a complete SSOT snapshot"""

        snapshot_filename = f"SSOT_SNAPSHOT_{self.snapshot_date.strftime('%Y-%m-%d')}.md"
        snapshot_path = os.path.join(self.output_dir, snapshot_filename)

        snapshot_content = self._build_snapshot_content(droplet_data or {})

        with open(snapshot_path, 'w') as f:
            f.write(snapshot_content)

        return snapshot_path

    def _build_snapshot_content(self, droplet_data: Dict) -> str:
        """Build the snapshot content"""

        timestamp = self.snapshot_date.strftime('%Y-%m-%d %H:%M UTC')
        version = self.snapshot_date.strftime('%Y-%m-%d-v1')

        content = f"""🟦 SSOT SNAPSHOT
Generated: {timestamp}

⸻

🔹 Snapshot Metadata
• Snapshot Date: {timestamp}
• Version: {version}
• Captured By: SSOT Generator (Automated)
• Previous Snapshot: [To be filled]
• Major Changes Since Last: [To be filled]

⸻

1️⃣ DROPLET INVENTORY

"""

        # Add droplet table header
        content += "| Name | ID | Steward | Status | Health | Last Seen | Version | Server/URL | Repo | Notes |\n"
        content += "|------|----|---------| -------|--------|-----------|---------|------------|------|-------|\n"

        # Add droplets if available
        droplets = droplet_data.get('droplets', [])
        if droplets:
            for droplet in droplets:
                content += f"| {droplet.get('name', 'N/A')} "
                content += f"| {droplet.get('id', 'N/A')} "
                content += f"| {droplet.get('steward', 'N/A')} "
                content += f"| {droplet.get('status', '⚫')} "
                content += f"| {droplet.get('health', 'N/A')} "
                content += f"| {droplet.get('last_seen', 'N/A')} "
                content += f"| {droplet.get('version', 'N/A')} "
                content += f"| {droplet.get('server', 'N/A')} "
                content += f"| {droplet.get('repo', 'N/A')} "
                content += f"| {droplet.get('notes', '')} |\n"
        else:
            content += "| No droplets discovered | - | - | ⚫ | N/A | N/A | N/A | N/A | N/A | Auto-scan required |\n"

        content += """
Status Legend:
• 🟢 Running — Healthy
• 🟡 Waiting — Built but not active
• 🔵 Building — In development
• 🔴 Down — Was active, now offline
• ⚫ Missing — Expected per Blueprint but absent

Health: Uptime % over last 7 days (or "N/A")

⸻

2️⃣ INTEGRATION STATUS

| Integration | Status | Last Verified | Issue/Notes |
|-------------|--------|---------------|-------------|
| Registry ← Droplets | ⚠️ | {timestamp} | Auto-verify needed |
| Orchestrator ← Heartbeats | ⚠️ | {timestamp} | Auto-verify needed |
| Proxy → Droplets | ⚠️ | {timestamp} | Auto-verify needed |
| Dashboard ← Registry | ⚠️ | {timestamp} | Auto-verify needed |

Legend: ✅ Working | ⚠️ Partial | ❌ Broken

⸻

3️⃣ FUNCTIONAL TRUTH (Reality of Each Droplet)

"""

        # Add droplet details
        if droplets:
            for droplet in droplets:
                content += f"""Droplet: {droplet.get('name', 'Unknown')} (#{droplet.get('id', 'N/A')})
• Current Function: {droplet.get('function', '[To be analyzed]')}
• Endpoints Found: {droplet.get('endpoints', '[Auto-scan needed]')}
• Dependencies: {droplet.get('dependencies', '[To be analyzed]')}
• Deviations from Blueprint: {droplet.get('deviations', '[Compliance check needed]')}
• Notes: {droplet.get('notes', '')}

"""
        else:
            content += "[No droplets to analyze - system scan needed]\n\n"

        content += f"""⸻

4️⃣ ACTIVE WORK (Right Now)

| Item | Type | Assignee | Started | Est. Complete | Status |
|------|------|----------|---------|---------------|--------|
| [Auto-populated from work tracking] | - | - | - | - | - |

Types: Build / Deploy / Fix / Optimize

⸻

5️⃣ WORK QUEUE (Blocked or Waiting)

| Item | Type | Blocked By | Priority | Assignee |
|------|------|------------|----------|----------|
| [To be filled] | - | - | - | - |

Priority: CRITICAL / HIGH / MEDIUM / LOW

⸻

6️⃣ CONFLICTS & MISMATCHES

Droplet ID Conflicts
• [Auto-scan needed]

Repo vs Server Mismatches
• [Auto-scan needed]

Endpoint Mismatches
• [Auto-scan needed]

Steward Mismatches
• [Auto-scan needed]

Missing Repos
• [Auto-scan needed]

Missing Documentation
• [Auto-scan needed]

Unknown Servers
• [Auto-scan needed]

⸻

7️⃣ INFRASTRUCTURE STATE

Servers
• Production: [To be configured]
• Staging: [To be configured]
• Development: Local

Domains
• fullpotential.ai: [Status unknown]
• *.fullpotential.ai: [Status unknown]

Databases
• Registry DB: [Not deployed]
• Orchestrator DB: [Not deployed]

Proxy / Routing
• Current: None
• Target: Automated via Proxy Manager (#3)

⸻

8️⃣ FOUNDATION FILES STATUS

| File | Version | Last Updated | Status | Notes |
|------|---------|--------------|--------|-------|
| UDC_COMPLIANCE.md | - | - | ⚠️ | Needs creation |
| TECH_STACK.md | - | - | ⚠️ | Needs creation |
| SECURITY_REQUIREMENTS.md | - | - | ⚠️ | Needs creation |
| CODE_STANDARDS.md | - | - | ⚠️ | Needs creation |
| INTEGRATION_GUIDE.md | - | - | ⚠️ | Needs creation |

Status: ✅ Current | ⚠️ Needs update | ❌ Outdated

⸻

9️⃣ METRICS SNAPSHOT

System Health
• Operational Droplets: 0/11
• System Autonomy: 0%
• Active Developers: [To be counted]

Velocity
• Sprints Completed This Week: 0
• Sprints In Progress: 0
• Avg Build Time: N/A
• First-Pass Approval Rate: N/A

Blockers
• Critical Blockers: [To be analyzed]
• High Priority Blockers: [To be analyzed]
• Total Items Blocked: [To be analyzed]

⸻

🔟 ARCHITECT CONFIRMATION
• Snapshot complete? [Pending Review]
• Architect Notes:

[To be filled]

• Approved for GAP ANALYSIS? [Pending]
• Next Snapshot Date: {(datetime.utcnow().replace(day=datetime.utcnow().day + 7)).strftime('%Y-%m-%d')}

⸻

END OF SSOT SNAPSHOT

Generated by: Full Potential AI - SSOT Generator v1.0
"""

        return content

    def scan_github_repos(self, org_name: str = "fullpotential-ai") -> List[Dict]:
        """Scan GitHub organization for droplet repositories"""

        droplets = []

        try:
            # Use gh CLI to list repos
            result = subprocess.run(
                ['gh', 'repo', 'list', org_name, '--json', 'name,description,url,updatedAt', '--limit', '100'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                repos = json.loads(result.stdout)

                for repo in repos:
                    if repo['name'].startswith('droplet-'):
                        # Extract droplet number and name
                        parts = repo['name'].replace('droplet-', '').split('-', 1)
                        droplet_id = parts[0] if parts else 'unknown'
                        droplet_name = parts[1] if len(parts) > 1 else 'unnamed'

                        droplets.append({
                            'name': droplet_name.replace('-', ' ').title(),
                            'id': droplet_id,
                            'repo': repo['url'],
                            'last_seen': repo.get('updatedAt', 'N/A'),
                            'status': '🔵',  # Assume building
                            'steward': 'TBD',
                            'health': 'N/A',
                            'version': 'N/A',
                            'server': 'Not deployed',
                            'notes': repo.get('description', '')
                        })
        except FileNotFoundError:
            print("⚠️  gh CLI not found. Install with: brew install gh")
        except subprocess.TimeoutExpired:
            print("⚠️  GitHub API timeout")
        except Exception as e:
            print(f"⚠️  Error scanning GitHub: {e}")

        return droplets


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate SSOT Snapshot')
    parser.add_argument('--blueprints-dir', default='../1-blueprints (architecture)',
                       help='Path to blueprints directory')
    parser.add_argument('--output-dir', default='../output/snapshots',
                       help='Output directory for snapshots')
    parser.add_argument('--scan-github', action='store_true',
                       help='Scan GitHub for droplet repositories')
    parser.add_argument('--github-org', default='fullpotential-ai',
                       help='GitHub organization name')

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    generator = SSOTGenerator(args.blueprints_dir, args.output_dir)

    droplet_data = {}

    if args.scan_github:
        print("🔍 Scanning GitHub for droplet repositories...")
        droplets = generator.scan_github_repos(args.github_org)
        droplet_data['droplets'] = droplets
        print(f"✅ Found {len(droplets)} droplet repositories")

    print("📝 Generating SSOT snapshot...")
    snapshot_path = generator.generate_snapshot(droplet_data)
    print(f"✅ Snapshot generated: {snapshot_path}")


if __name__ == '__main__':
    main()
