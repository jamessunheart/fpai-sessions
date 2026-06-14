#!/usr/bin/env python3
"""
Gap Analysis Generator
Analyzes gaps between Blueprint and SSOT Snapshot
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Tuple


class GapAnalyzer:
    """Analyze gaps between Blueprint ideal and SSOT reality"""

    EXPECTED_DROPLETS = {
        1: {"name": "Registry", "purpose": "Identity, SSOT, JWT issuer", "phase": 1},
        2: {"name": "Dashboard", "purpose": "Visual system truth", "phase": 2},
        3: {"name": "Proxy Manager", "purpose": "Routing, SSL, domains", "phase": 2},
        8: {"name": "Verifier", "purpose": "Automated quality gates", "phase": 2},
        10: {"name": "Orchestrator", "purpose": "Task routing, messaging", "phase": 1},
        11: {"name": "Coordinator", "purpose": "Sprint automation", "phase": 3},
        15: {"name": "Recruiter", "purpose": "Developer pipeline", "phase": 3},
        16: {"name": "Self-Optimizer", "purpose": "System improvement", "phase": 4},
        17: {"name": "Deployer", "purpose": "Deployment automation", "phase": 3},
        18: {"name": "Meta-Architect", "purpose": "Pattern recognition", "phase": 4},
        19: {"name": "Mesh Expander", "purpose": "Multi-cloud scaling", "phase": 4}
    }

    FOUNDATION_FILES = [
        "UDC_COMPLIANCE.md",
        "TECH_STACK.md",
        "SECURITY_REQUIREMENTS.md",
        "CODE_STANDARDS.md",
        "INTEGRATION_GUIDE.md"
    ]

    def __init__(self, blueprint_path: str, snapshot_path: str, output_dir: str):
        self.blueprint_path = blueprint_path
        self.snapshot_path = snapshot_path
        self.output_dir = output_dir
        self.analysis_date = datetime.utcnow()

    def analyze(self) -> str:
        """Perform gap analysis and generate report"""

        # Parse snapshot
        snapshot_data = self._parse_snapshot()

        # Analyze gaps
        droplet_gaps = self._analyze_droplet_gaps(snapshot_data)
        infrastructure_gaps = self._analyze_infrastructure_gaps(snapshot_data)
        foundation_gaps = self._analyze_foundation_gaps(snapshot_data)

        # Generate report
        report_path = self._generate_report(droplet_gaps, infrastructure_gaps, foundation_gaps)

        return report_path

    def _parse_snapshot(self) -> Dict:
        """Parse SSOT snapshot file"""

        data = {
            'droplets': [],
            'integrations': {},
            'infrastructure': {},
            'foundation_files': {},
            'metrics': {}
        }

        try:
            with open(self.snapshot_path, 'r') as f:
                content = f.read()

            # Extract droplet information
            # This is a simplified parser - would need enhancement for production
            lines = content.split('\n')
            in_droplet_section = False

            for line in lines:
                if '1️⃣ DROPLET INVENTORY' in line:
                    in_droplet_section = True
                elif in_droplet_section and line.startswith('|') and 'Name' not in line and '---' not in line:
                    parts = [p.strip() for p in line.split('|')[1:-1]]
                    if len(parts) >= 4 and parts[0]:
                        data['droplets'].append({
                            'name': parts[0],
                            'id': parts[1],
                            'status': parts[3]
                        })
                elif '2️⃣ INTEGRATION STATUS' in line:
                    in_droplet_section = False

        except FileNotFoundError:
            print(f"⚠️  Snapshot file not found: {self.snapshot_path}")

        return data

    def _analyze_droplet_gaps(self, snapshot_data: Dict) -> List[Dict]:
        """Analyze droplet gaps"""

        gaps = []
        existing_ids = {d.get('id', ''): d for d in snapshot_data.get('droplets', [])}

        for droplet_id, expected in self.EXPECTED_DROPLETS.items():
            str_id = str(droplet_id)

            if str_id not in existing_ids or existing_ids[str_id].get('status') == '⚫':
                severity = self._determine_severity(expected['phase'])

                gaps.append({
                    'area': f"Droplet #{droplet_id}",
                    'blueprint': f"{expected['name']} - {expected['purpose']}",
                    'reality': "Missing / Not deployed",
                    'gap': f"Droplet #{droplet_id} ({expected['name']}) does not exist",
                    'severity': severity,
                    'phase': expected['phase']
                })

        return gaps

    def _analyze_infrastructure_gaps(self, snapshot_data: Dict) -> List[Dict]:
        """Analyze infrastructure gaps"""

        gaps = []

        # Check for basic infrastructure
        infra_checks = [
            ("Servers", "Production + Staging + Dev", "Development only"),
            ("Domains", "fullpotential.ai configured", "Not configured"),
            ("Database", "Registry + Orchestrator DBs", "Not deployed"),
            ("Routing", "Automated via Proxy Manager", "None")
        ]

        for area, blueprint, reality in infra_checks:
            gaps.append({
                'area': area,
                'blueprint': blueprint,
                'reality': reality,
                'gap': f"{area} infrastructure incomplete",
                'severity': '🟧'
            })

        return gaps

    def _analyze_foundation_gaps(self, snapshot_data: Dict) -> List[Dict]:
        """Analyze Foundation Files gaps"""

        gaps = []

        for file_name in self.FOUNDATION_FILES:
            gaps.append({
                'area': f"Foundation: {file_name}",
                'blueprint': "Created and current",
                'reality': "Missing / Needs creation",
                'gap': f"{file_name} not found",
                'severity': '🟥'  # Critical because it blocks all builds
            })

        return gaps

    def _determine_severity(self, phase: int) -> str:
        """Determine gap severity based on build phase"""

        if phase == 1:
            return '🟥'  # CRITICAL - Phase 1 is foundation
        elif phase == 2:
            return '🟧'  # HIGH - Phase 2 is infrastructure
        elif phase == 3:
            return '🟨'  # MEDIUM - Phase 3 is automation
        else:
            return '🟩'  # LOW - Phase 4 is intelligence

    def _generate_report(self, droplet_gaps: List[Dict],
                        infrastructure_gaps: List[Dict],
                        foundation_gaps: List[Dict]) -> str:
        """Generate gap analysis report"""

        timestamp = self.analysis_date.strftime('%Y-%m-%d %H:%M UTC')
        filename = f"GAP_ANALYSIS_{self.analysis_date.strftime('%Y-%m-%d')}.md"
        report_path = os.path.join(self.output_dir, filename)

        all_gaps = droplet_gaps + infrastructure_gaps + foundation_gaps
        critical_gaps = [g for g in all_gaps if g['severity'] == '🟥']
        high_gaps = [g for g in all_gaps if g['severity'] == '🟧']

        # Determine primary blocker
        primary_blocker = self._identify_primary_blocker(critical_gaps, high_gaps)

        content = f"""🟪 GAP ANALYSIS
Generated: {timestamp}

⸻

🔹 Metadata
• Analysis Date: {timestamp}
• Based On SSOT Snapshot: {os.path.basename(self.snapshot_path)}
• Analyzed By: Gap Analyzer (Automated)
• Architect Approval: Pending

⸻

1️⃣ BLUEPRINT vs REALITY – GAP TABLE

| Area | Blueprint (Ideal) | Snapshot (Reality) | Gap Summary | Severity |
|------|-------------------|--------------------| ------------|----------|
"""

        # Add all gaps to table
        for gap in all_gaps:
            content += f"| {gap['area']} | {gap['blueprint']} | {gap['reality']} | {gap['gap']} | {gap['severity']} |\n"

        content += """
Severity:
🟥 CRITICAL | 🟧 HIGH | 🟨 MEDIUM | 🟩 LOW

⸻

2️⃣ CRITICAL PATH ANALYSIS

"""

        if primary_blocker:
            content += f"""Primary Blocker:
{primary_blocker['description']}

Evidence (from SSOT):
{primary_blocker['evidence']}

This Blocker Prevents:
"""
            for blocked in primary_blocker['blocks']:
                content += f"• {blocked}\n"

            content += f"""
Impact:
{primary_blocker['impact']}

Current Assignment (from SSOT Active Work):
[To be assigned]

"""
        else:
            content += "[No critical blockers identified]\n\n"

        content += """⸻

3️⃣ REQUIRED FIXES (Broken Down by Priority)

"""

        # Critical fixes
        content += "🟥 BLOCKING (Must Fix Before Anything Else)\n\n"
        for gap in critical_gaps:
            content += f"""- Fix: {gap['gap']}
  Area: {gap['area']}
  Assignee: [To be assigned]
  Timeline: [To be estimated]
  Dependencies: Foundation Files

"""

        # High priority fixes
        content += "🟧 HIGH PRIORITY (Blocks Multiple Items)\n\n"
        for gap in high_gaps:
            content += f"""- Fix: {gap['gap']}
  Area: {gap['area']}
  Assignee: [To be assigned]
  Timeline: [To be estimated]

"""

        content += """⸻

4️⃣ NEXT ACTIONS (Ordered by Priority)

| Action | Type | Assignee | Timeline | Blockers | Deliverable |
|--------|------|----------|----------|----------|-------------|
"""

        # Generate recommended actions
        actions = self._generate_recommended_actions(all_gaps)
        for action in actions:
            content += f"| {action['name']} | {action['type']} | {action['assignee']} | {action['timeline']} | {action['blockers']} | {action['deliverable']} |\n"

        content += f"""
Dependencies:
• Foundation Files must be created first (blocks all droplet builds)
• Registry (#1) and Orchestrator (#10) are Phase 1 dependencies
• Infrastructure droplets depend on Phase 1 completion

⸻

5️⃣ EXPECTED SYSTEM STATE AFTER ACTIONS

Droplet Changes
• All Phase 1 droplets: ⚫ → 🔵 → 🟡 → 🟢
• Foundation Files: ⚠️ → ✅

Integration Changes
• Registry ← Droplets: ❌ → ✅
• Orchestrator ← Heartbeats: ❌ → ✅

Metrics
• Operational Droplets: 0/11 → 2/11 (Phase 1)
• System Autonomy: 0% → 20%
• Critical Blockers: {len(critical_gaps)} → 0

Timeline
• Start: {timestamp}
• Expected Completion: [Est. 2-3 weeks for Phase 1]
• Next Snapshot: {(datetime.utcnow().replace(day=datetime.utcnow().day + 7)).strftime('%Y-%m-%d')}

⸻

6️⃣ ARCHITECT APPROVAL
• Are priorities correct? [Pending]
• Is the critical path correct? [Pending]
• Do actions align with Blueprint? [Pending]

Architect Notes:

[To be filled]

Approved for Coordinator Execution?

[Yes / No / With Modifications]

Required Modifications (if any):

[List]

⸻

END GAP ANALYSIS

Generated by: Full Potential AI - Gap Analyzer v1.0
"""

        with open(report_path, 'w') as f:
            f.write(content)

        return report_path

    def _identify_primary_blocker(self, critical_gaps: List[Dict],
                                  high_gaps: List[Dict]) -> Dict:
        """Identify the primary blocker"""

        # Foundation Files block everything
        foundation_critical = [g for g in critical_gaps if 'Foundation' in g['area']]

        if foundation_critical:
            return {
                'description': 'Foundation Files (5 files) are missing',
                'evidence': 'All 5 Foundation Files show status ⚠️ Needs creation',
                'blocks': [
                    'All droplet builds (Apprentices need these to generate code)',
                    'Code standardization',
                    'Security compliance',
                    'UDC compliance',
                    'System integration'
                ],
                'impact': '100% of development blocked - Foundation Files are required for Sacred Loop'
            }

        # Phase 1 droplets block everything else
        phase1_gaps = [g for g in critical_gaps if g.get('phase') == 1]

        if phase1_gaps:
            return {
                'description': 'Phase 1 droplets (Registry + Orchestrator) missing',
                'evidence': 'Registry (#1) and Orchestrator (#10) show status ⚫',
                'blocks': [
                    'All other droplet deployments',
                    'System authentication (JWT)',
                    'Inter-droplet messaging',
                    'System SSOT'
                ],
                'impact': '90% of system functionality blocked'
            }

        return None

    def _generate_recommended_actions(self, all_gaps: List[Dict]) -> List[Dict]:
        """Generate recommended next actions"""

        actions = []

        # Check for Foundation Files gap
        foundation_gaps = [g for g in all_gaps if 'Foundation' in g['area']]

        if foundation_gaps:
            actions.append({
                'name': 'Create Foundation Files (5 files)',
                'type': 'Build',
                'assignee': 'Architect',
                'timeline': '4-6 hours',
                'blockers': 'None',
                'deliverable': '5 Foundation Files ready'
            })

        # Check for Phase 1 droplets
        phase1_gaps = [g for g in all_gaps if g.get('phase') == 1]

        if phase1_gaps:
            for gap in phase1_gaps:
                droplet_match = re.search(r'Droplet #(\d+)', gap['area'])
                if droplet_match:
                    droplet_id = droplet_match.group(1)
                    actions.append({
                        'name': f"Build Droplet #{droplet_id} ({gap['blueprint'].split(' - ')[0]})",
                        'type': 'Build',
                        'assignee': 'Apprentice',
                        'timeline': '4-6 hours',
                        'blockers': 'Foundation Files',
                        'deliverable': f"Droplet #{droplet_id} deployed"
                    })

        return actions[:5]  # Limit to top 5 actions


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate Gap Analysis')
    parser.add_argument('--blueprint', default='../1-blueprints (architecture)/1-SYSTEM-BLUEPRINT.txt',
                       help='Path to blueprint file')
    parser.add_argument('--snapshot', required=True,
                       help='Path to SSOT snapshot file')
    parser.add_argument('--output-dir', default='../output/gap-analyses',
                       help='Output directory for gap analyses')

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    analyzer = GapAnalyzer(args.blueprint, args.snapshot, args.output_dir)

    print("🔍 Analyzing gaps between Blueprint and SSOT...")
    report_path = analyzer.analyze()
    print(f"✅ Gap analysis generated: {report_path}")


if __name__ == '__main__':
    main()
