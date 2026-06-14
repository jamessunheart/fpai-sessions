#!/usr/bin/env python3
"""
🎯 APPRENTICE HARVESTER - Unified Submission Interface
One command to handle all apprentice code submissions.

Usage:
    # Safe mode with verification (default)
    ./harvest-apprentice.py JohnDoe https://github.com/john/cool-service
    
    # Trusted apprentice (skip verification)
    ./harvest-apprentice.py AliceVet https://github.com/alice/api --trusted
    
    # Custom service name
    ./harvest-apprentice.py Bob https://github.com/bob/repo --service bob-analytics
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ApprenticeHarvester:
    def __init__(self):
        self.root = Path(__file__).resolve().parent.parent
        self.config_file = self.root / "docs/coordination/apprentice-submissions.json"
        self.log_file = self.root / "docs/coordination/apprentice-submissions.log"
        self.load_config()
    
    def load_config(self):
        """Load standard paths and settings."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
        else:
            self.config = {
                "default_target": "SERVICES",
                "auto_verify": True,
                "require_tests": True,
                "auto_push": False,  # Safety: require manual push
                "submissions": []
            }
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def save_config(self):
        """Save updated configuration."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def harvest(self, 
                apprentice_name: str,
                repo_url: str, 
                service_name: Optional[str] = None,
                branch: str = "main",
                mode: str = "gatekeeper"):
        """
        Single entry point for harvesting apprentice submissions.
        
        Args:
            apprentice_name: Who submitted it (for tracking & accountability)
            repo_url: Git URL of their repository
            service_name: Auto-inferred from repo if not provided
            branch: Default 'main'
            mode: 'gatekeeper' (safe, verified) or 'direct' (trusted, skip verification)
        """
        print("=" * 70)
        print("🎯 APPRENTICE HARVESTER - Full Potential OS")
        print("=" * 70)
        print(f"📝 Apprentice: {apprentice_name}")
        print(f"🔗 Repository: {repo_url}")
        print(f"🌿 Branch: {branch}")
        
        # Auto-infer service name from URL if not provided
        if not service_name:
            service_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            print(f"🏷️  Auto-detected service name: {service_name}")
        
        print(f"🛡️  Mode: {mode.upper()}")
        print("=" * 70)
        print()
        
        # Initialize submission record
        submission = {
            "timestamp": datetime.now().isoformat(),
            "apprentice": apprentice_name,
            "service": service_name,
            "repo_url": repo_url,
            "branch": branch,
            "mode": mode,
            "status": "IN_PROGRESS"
        }
        
        try:
            # Route to appropriate harvester
            if mode == "gatekeeper":
                result = self._harvest_safe(repo_url, service_name, branch)
                submission["status"] = result["status"]
                submission["score"] = result.get("score")
                submission["path"] = result.get("path")
            else:
                result = self._harvest_direct(repo_url, service_name, branch)
                submission["status"] = "APPROVED"
                submission["path"] = result["path"]
            
            # Log successful submission
            self._log_submission(submission)
            self._save_submission_record(submission)
            
            print("\n" + "=" * 70)
            print(f"✅ SUCCESS: {service_name} harvested successfully!")
            print(f"📂 Location: {submission.get('path', 'N/A')}")
            
            if mode == "gatekeeper" and submission.get("score"):
                print(f"📊 Quality Score: {submission['score']}/100")
            
            print("\n🎉 Next steps:")
            if not self.config.get("auto_push", False):
                print("   1. Review the harvested code")
                print("   2. Run: git push origin main")
                print("   3. Notify apprentice of acceptance")
            else:
                print("   1. Notify apprentice of acceptance")
                print("   2. Proceed with integration")
            print("=" * 70)
            
            return submission
            
        except Exception as e:
            submission["status"] = "FAILED"
            submission["error"] = str(e)
            self._log_submission(submission)
            self._save_submission_record(submission)
            
            print("\n" + "=" * 70)
            print(f"❌ FAILED: Could not harvest {service_name}")
            print(f"🔴 Error: {e}")
            print("\n📋 Next steps:")
            print(f"   1. Notify {apprentice_name} of the issue")
            print("   2. Provide feedback for fixes")
            print("   3. Request resubmission after fixes")
            print("=" * 70)
            
            raise
    
    def _harvest_safe(self, url: str, name: str, branch: str) -> dict:
        """Use Gatekeeper for verification workflow."""
        print("🛡️  Using GATEKEEPER mode (Verify then Trust)")
        print("   → Cloning to STAGING/")
        print("   → Running verification tests")
        print("   → Auto-promoting if score ≥90%")
        print()
        
        gatekeeper_path = self.root / "orchestration/tools/gatekeeper.py"
        
        if not gatekeeper_path.exists():
            raise FileNotFoundError(
                f"Gatekeeper not found at {gatekeeper_path}. "
                "Try --trusted mode or check installation."
            )
        
        result = subprocess.run([
            sys.executable, str(gatekeeper_path),
            "--url", url,
            "--name", name,
            "--branch", branch
        ], cwd=self.root, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode != 0:
            raise RuntimeError(f"Gatekeeper verification failed (exit code {result.returncode})")
        
        # Parse output for results (basic parsing)
        # In a production system, gatekeeper would return JSON
        return {
            "status": "APPROVED" if "SUCCESS" in result.stdout else "NEEDS_FIXES",
            "path": f"SERVICES/{name}",
            "score": self._parse_score(result.stdout)
        }
    
    def _harvest_direct(self, url: str, name: str, branch: str) -> dict:
        """Use direct harvester (trusted apprentices only)."""
        print("⚡ Using DIRECT mode (Trusted)")
        print("   → Merging directly via git subtree")
        print("   → Running basic verification")
        print("   → Committing to main branch")
        print()
        
        target = f"{self.config['default_target']}/{name}"
        harvester_path = self.root / "fullpotential_ai/orchestration/tools/harvest_repo.py"
        
        if not harvester_path.exists():
            raise FileNotFoundError(
                f"Harvester not found at {harvester_path}. "
                "Check installation."
            )
        
        result = subprocess.run([
            sys.executable, str(harvester_path),
            "--url", url,
            "--branch", branch,
            "--path", target
        ], cwd=self.root, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode != 0:
            raise RuntimeError(f"Direct harvest failed (exit code {result.returncode})")
        
        return {
            "path": target
        }
    
    def _parse_score(self, output: str) -> Optional[int]:
        """Extract verification score from output."""
        import re
        match = re.search(r'Score:\s*(\d+)', output)
        if match:
            return int(match.group(1))
        return None
    
    def _log_submission(self, submission: dict):
        """Append to log file for audit trail."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = (
            f"{submission['timestamp']} | "
            f"{submission['apprentice']:20} | "
            f"{submission['service']:30} | "
            f"{submission['status']:12} | "
            f"{submission['repo_url']}\n"
        )
        
        with open(self.log_file, "a") as f:
            f.write(log_entry)
    
    def _save_submission_record(self, submission: dict):
        """Save to JSON for dashboard/tracking."""
        self.config["submissions"].append(submission)
        # Keep only last 100 submissions in memory
        if len(self.config["submissions"]) > 100:
            self.config["submissions"] = self.config["submissions"][-100:]
        self.save_config()
    
    def list_submissions(self, limit: int = 10):
        """Display recent submissions."""
        print("\n📊 Recent Apprentice Submissions")
        print("=" * 100)
        print(f"{'Date':<20} {'Apprentice':<15} {'Service':<25} {'Status':<12} {'Score':<6}")
        print("-" * 100)
        
        for sub in reversed(self.config["submissions"][-limit:]):
            date = sub["timestamp"][:19].replace('T', ' ')
            apprentice = sub["apprentice"][:14]
            service = sub["service"][:24]
            status = sub["status"]
            score = str(sub.get("score", "-"))
            
            print(f"{date:<20} {apprentice:<15} {service:<25} {status:<12} {score:<6}")
        
        print("=" * 100)


def main():
    parser = argparse.ArgumentParser(
        description="🎯 Unified Apprentice Harvester - Full Potential OS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Safe mode (default): Verify before accepting
  %(prog)s JohnDoe https://github.com/john/cool-service
  
  # Trusted mode: Skip verification
  %(prog)s AliceVet https://github.com/alice/api --trusted
  
  # Custom service name & branch
  %(prog)s Bob https://github.com/bob/repo --service analytics --branch develop
  
  # List recent submissions
  %(prog)s --list
        """
    )
    
    parser.add_argument("apprentice", nargs='?', help="Apprentice name (for tracking)")
    parser.add_argument("url", nargs='?', help="Git URL of their repository")
    parser.add_argument("--service", help="Service name (auto-inferred if omitted)")
    parser.add_argument("--branch", default="main", help="Branch to harvest (default: main)")
    parser.add_argument("--trusted", action="store_true", 
                       help="Skip verification - use for trusted apprentices only")
    parser.add_argument("--list", action="store_true",
                       help="List recent submissions")
    parser.add_argument("--limit", type=int, default=10,
                       help="Number of submissions to show with --list")
    
    args = parser.parse_args()
    
    harvester = ApprenticeHarvester()
    
    # Handle list command
    if args.list:
        harvester.list_submissions(args.limit)
        return
    
    # Validate required arguments
    if not args.apprentice or not args.url:
        parser.print_help()
        sys.exit(1)
    
    # Determine mode
    mode = "direct" if args.trusted else "gatekeeper"
    
    # Execute harvest
    try:
        harvester.harvest(
            args.apprentice,
            args.url,
            args.service,
            args.branch,
            mode
        )
    except Exception as e:
        print(f"\n💥 Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

