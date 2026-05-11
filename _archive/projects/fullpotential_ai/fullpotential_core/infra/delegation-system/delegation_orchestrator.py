#!/usr/bin/env python3
"""
Delegation Orchestrator
Automatically manages the entire delegation lifecycle:
1. Detect blockers → 2. Create tasks → 3. Recruit VAs → 4. Receive credentials → 5. Auto-integrate → 6. Deploy
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from credential_vault import CredentialVault
from blocker_delegation import BlockerDelegation, BLOCKER_TEMPLATES
from upwork_recruiter import TaskDelegator
from auto_integrator import AutoIntegrator


class DelegationOrchestrator:
    """Orchestrates the complete delegation workflow"""

    def __init__(self):
        self.vault = CredentialVault()
        self.delegation = BlockerDelegation()
        self.task_delegator = TaskDelegator()
        self.integrator = AutoIntegrator()

        self.base_dir = Path("/root/delegation-system")
        self.orchestrator_log = self.base_dir / "orchestrator_log.json"

        if not self.orchestrator_log.exists():
            self.orchestrator_log.write_text(json.dumps([], indent=2))

    def detect_blockers(self) -> List[str]:
        """Detect what services are blocking progress"""

        print("🔍 Detecting blockers...")

        blockers = []

        # Check which credentials are missing
        required_credentials = {
            "stripe": "Payment processing",
            "calendly": "Booking system",
            "facebook_oauth": "Facebook Ads automation",
            "google_oauth": "Google Ads automation"
        }

        for service, description in required_credentials.items():
            try:
                creds = self.vault.get_credential("tier2_monitored", service)
                if not creds:
                    blockers.append(service)
                    print(f"  ❌ Missing: {service} ({description})")
            except:
                blockers.append(service)
                print(f"  ❌ Missing: {service} ({description})")

        if not blockers:
            print("  ✅ No blockers detected!")

        return blockers

    def create_blocker_tasks(self, blockers: List[str]) -> List[Dict]:
        """Create delegation tasks for blockers"""

        print(f"\n📋 Creating {len(blockers)} blocker tasks...")

        tasks = []

        for blocker in blockers:
            if blocker in BLOCKER_TEMPLATES:
                task = self.delegation.create_blocker_task(
                    blocker_name=blocker,
                    task_template=BLOCKER_TEMPLATES[blocker]
                )

                # Save template to file for VA
                template_file = self.delegation.tasks_dir / f"{task['id']}_instructions.md"
                template_file.write_text(BLOCKER_TEMPLATES[blocker])

                print(f"  ✅ Created task: {task['id']}")

                tasks.append(task)

        return tasks

    def recruit_vas_for_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Automatically recruit VAs for blocker tasks"""

        print(f"\n🎯 Recruiting VAs for {len(tasks)} tasks...")

        recruitment_results = []

        task_configs = {
            "stripe": {
                "deliverables": ["Stripe Account ID", "Payment Link", "Publishable Key", "Secret Key"],
                "deadline": "24 hours",
                "budget": 50
            },
            "calendly": {
                "deliverables": ["Calendly Account Email", "Booking Link", "API Token (optional)"],
                "deadline": "24 hours",
                "budget": 30
            },
            "facebook_oauth": {
                "deliverables": ["Business Manager ID", "Ad Account ID", "Page ID", "Access Token"],
                "deadline": "48 hours",
                "budget": 75
            },
            "google_oauth": {
                "deliverables": ["Customer ID", "Developer Token", "Client ID", "Client Secret", "Refresh Token"],
                "deadline": "72 hours",
                "budget": 100
            }
        }

        for task in tasks:
            blocker = task['blocker']

            if blocker in task_configs:
                config = task_configs[blocker]

                delegation_task = {
                    'description': f"Setup {blocker.replace('_', ' ').title()} account and provide API credentials",
                    'deliverables': config['deliverables'],
                    'deadline': config['deadline'],
                    'credentials': ['operations_email', 'operations_card'],
                    'budget': config['budget']
                }

                result = self.task_delegator.delegate_task(delegation_task)

                recruitment_results.append({
                    "blocker": blocker,
                    "task_id": task['id'],
                    "delegation_result": result
                })

                print(f"  ✅ VA recruitment initiated for {blocker}")

        return recruitment_results

    def monitor_task_completion(self) -> List[Dict]:
        """Monitor tasks and check for completed credentials"""

        print("\n👀 Monitoring task completion...")

        completed = []

        # Get all pending tasks
        pending = self.delegation.get_pending_blockers()

        print(f"  📊 {len(pending)} tasks pending")

        # Check if any have been completed (credentials stored)
        for task in pending:
            if task.get('credentials_stored'):
                completed.append(task)
                print(f"  ✅ Completed: {task['blocker']}")

        return completed

    def auto_integrate_completed_tasks(self, completed_tasks: List[Dict]):
        """Automatically integrate credentials from completed tasks"""

        print(f"\n🔄 Auto-integrating {len(completed_tasks)} completed tasks...")

        for task in completed_tasks:
            blocker = task['blocker']

            # Retrieve credentials from vault
            try:
                credentials = self.vault.get_credential("tier2_monitored", blocker)

                if credentials:
                    # Auto-integrate
                    result = self.integrator.auto_integrate_service(blocker, credentials)

                    print(f"  ✅ Integrated: {blocker}")
                    print(f"     Actions: {', '.join(result.get('actions', []))}")

            except Exception as e:
                print(f"  ⚠️ Failed to integrate {blocker}: {e}")

    def check_and_deploy(self):
        """Check if ready to deploy and do it"""

        print("\n🚀 Checking deployment readiness...")

        deployment = self.integrator.check_readiness_and_deploy()

        return deployment

    def run_full_cycle(self):
        """Run the complete delegation cycle"""

        print("\n" + "=" * 70)
        print("🤖 DELEGATION ORCHESTRATOR - FULL CYCLE")
        print("=" * 70)
        print()

        # Log cycle start
        cycle = {
            "started_at": datetime.now().isoformat(),
            "steps": []
        }

        # Step 1: Detect blockers
        print("\n### STEP 1: DETECT BLOCKERS")
        blockers = self.detect_blockers()
        cycle['steps'].append({
            "step": "detect_blockers",
            "blockers_found": blockers
        })

        if not blockers:
            print("\n✅ No blockers! System is ready.")
            cycle['status'] = 'no_blockers'
            return cycle

        # Step 2: Create tasks
        print("\n### STEP 2: CREATE TASKS")
        tasks = self.create_blocker_tasks(blockers)
        cycle['steps'].append({
            "step": "create_tasks",
            "tasks_created": [t['id'] for t in tasks]
        })

        # Step 3: Recruit VAs
        print("\n### STEP 3: RECRUIT VAs")
        recruitments = self.recruit_vas_for_tasks(tasks)
        cycle['steps'].append({
            "step": "recruit_vas",
            "recruitments": recruitments
        })

        # Step 4: Monitor completion (would run continuously in production)
        print("\n### STEP 4: MONITOR COMPLETION")
        completed = self.monitor_task_completion()
        cycle['steps'].append({
            "step": "monitor_completion",
            "completed_count": len(completed)
        })

        # Step 5: Auto-integrate
        if completed:
            print("\n### STEP 5: AUTO-INTEGRATE")
            self.auto_integrate_completed_tasks(completed)
            cycle['steps'].append({
                "step": "auto_integrate",
                "integrated_count": len(completed)
            })

        # Step 6: Check deployment readiness
        print("\n### STEP 6: CHECK DEPLOYMENT")
        deployment = self.check_and_deploy()
        cycle['steps'].append({
            "step": "check_deployment",
            "deployment": deployment
        })

        # Log cycle completion
        cycle['completed_at'] = datetime.now().isoformat()
        cycle['status'] = 'completed'

        log = json.loads(self.orchestrator_log.read_text())
        log.append(cycle)
        self.orchestrator_log.write_text(json.dumps(log, indent=2))

        print("\n" + "=" * 70)
        print("✅ CYCLE COMPLETE")
        print("=" * 70)
        print()

        return cycle

    def run_monitoring_loop(self, interval_minutes: int = 30):
        """Run continuous monitoring loop"""

        print("\n🔄 Starting monitoring loop...")
        print(f"Checking every {interval_minutes} minutes")
        print()

        while True:
            try:
                # Run cycle
                self.run_full_cycle()

                # Wait
                print(f"\n💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

            except KeyboardInterrupt:
                print("\n\n👋 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"\n⚠️ Error in monitoring loop: {e}")
                print(f"Retrying in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)


def main():
    """Run orchestrator"""

    orchestrator = DelegationOrchestrator()

    print("\n🤖 DELEGATION ORCHESTRATOR")
    print("=" * 70)
    print()
    print("This system automatically:")
    print("  1. Detects what credentials are missing (blockers)")
    print("  2. Creates detailed tasks for VAs")
    print("  3. Posts jobs to Upwork and recruits VAs")
    print("  4. Provides VAs with secure portal to submit credentials")
    print("  5. Auto-integrates credentials when received")
    print("  6. Deploys landing page when ready")
    print()
    print("=" * 70)
    print()

    # Run single cycle
    orchestrator.run_full_cycle()

    print("\n📊 SUMMARY")
    print("-" * 70)
    print()
    print("VAs will:")
    print("  • Receive task via Upwork")
    print("  • Access instructions via secure portal")
    print("  • Submit credentials when complete")
    print()
    print("System will:")
    print("  • Automatically integrate credentials")
    print("  • Deploy landing page when ready")
    print("  • Notify you when live")
    print()
    print("Your involvement:")
    print("  • 0 minutes (fully automated)")
    print("  • Just review notification when live")
    print()


if __name__ == "__main__":
    main()
