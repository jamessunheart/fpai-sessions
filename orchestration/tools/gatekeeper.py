#!/usr/bin/env python3
"""
🛡️ GATEKEEPER - The Sovereign Verification Engine

Automates the "Verify then Trust" workflow:
1. Harvests external code into STAGING/ (Quarantine)
2. Verifies it using the Verifier Service
3. DECISION:
   - PASS (>90%): Merges to SERVICES/ and commits
   - FAIL: Dispatches Autonomous Executor to fix it
"""

import argparse
import asyncio
import json
import logging
import shutil
import subprocess
import sys
import time
import httpx
from pathlib import Path
from typing import Dict, Optional

# Add core to path to import telemetry_client
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "core"))
try:
    from telemetry_client import TelemetryClient
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

# Configuration
VERIFIER_URL = "http://localhost:8200"
STAGING_DIR = Path("STAGING/incoming")
PRODUCTION_DIR = Path("SERVICES")
INTENTS_DIR = Path("docs/coordination/intents")
REMOTE_NAME_PREFIX = "gatekeeper_temp_"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - 🛡️ GATEKEEPER - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Gatekeeper")

class GatekeeperError(Exception):
    """Custom error for Gatekeeper failures."""
    pass

async def run_command(cmd: list, cwd: Path = None) -> str:
    """Run a shell command and return output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise GatekeeperError(f"Command failed: {' '.join(cmd)}\nStderr: {stderr.decode()}")
            
        return stdout.decode().strip()
    except Exception as e:
        raise GatekeeperError(f"Execution error: {str(e)}")

class Gatekeeper:
    def __init__(self):
        self.root_dir = Path.cwd()
        self.staging_dir = self.root_dir / STAGING_DIR
        self.production_dir = self.root_dir / PRODUCTION_DIR
        self.intents_dir = self.root_dir / INTENTS_DIR
        
        # Ensure directories exist
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.intents_dir.mkdir(parents=True, exist_ok=True)

        self.telemetry = None
        if TELEMETRY_AVAILABLE:
            self.telemetry = TelemetryClient()

    async def harvest_safe(self, url: str, branch: str, repo_name: str) -> Path:
        """
        Harvests a repo into STAGING without committing to main.
        Uses git subtree logic but isolates it.
        """
        logger.info(f"🚜 Harvesting {repo_name} from {url} ({branch})...")
        target_path = self.staging_dir / repo_name
        
        if target_path.exists():
            logger.warning(f"Target {target_path} exists. Cleaning up...")
            shutil.rmtree(target_path)
        
        # We'll use a simpler clone strategy for staging to avoid cluttering the main repo git history
        # with temporary remotes until we are ready to merge.
        # Step 1: Clone to temp location
        try:
            await run_command(["git", "clone", "--depth", "1", "--branch", branch, url, str(target_path)])
            # Remove .git folder to make it a simple directory of files for verification
            shutil.rmtree(target_path / ".git")
            logger.info(f"✅ Harvested to {target_path}")
            return target_path
        except Exception as e:
            raise GatekeeperError(f"Harvest failed: {e}")

    async def verify_codebase(self, path: Path, repo_name: str) -> Dict:
        """Submit to Verifier Service and poll for results."""
        logger.info(f"🔍 Verifying {repo_name}...")
        
        async with httpx.AsyncClient() as client:
            # Check if verifier is up
            try:
                await client.get(f"{VERIFIER_URL}/health")
            except:
                raise GatekeeperError(f"Verifier Service not reachable at {VERIFIER_URL}")

            # Submit job
            resp = await client.post(f"{VERIFIER_URL}/verify", json={
                "droplet_path": str(path.absolute()),
                "droplet_name": repo_name
            })
            
            if resp.status_code != 202:
                raise GatekeeperError(f"Verification submission failed: {resp.text}")
                
            job_id = resp.json()["job_id"]
            logger.info(f"📋 Job ID: {job_id}. Waiting for results...")
            
            # Poll
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{VERIFIER_URL}/verify/{job_id}")
                status_data = status_resp.json()
                
                if status_data["status"] in ["completed", "failed"]:
                    break
                
                logger.info(f"   ... {status_data.get('current_phase', 'processing')} ({status_data.get('progress_percent', 0)}%)")

            # Get Report
            report_resp = await client.get(f"{VERIFIER_URL}/verify/{job_id}/report")
            return report_resp.json()

    async def dispatch_fix_mission(self, repo_name: str, report: Dict):
        """Create an intent file for the Autonomous Executor."""
        logger.info(f"🚑 Dispatching FIX Mission for {repo_name}")
        
        issues = report.get("critical_issues", []) + report.get("important_issues", [])
        issue_text = "\n".join([f"- {i['description']}" for i in issues[:10]])
        
        intent = {
            "architect_intent": f"Fix validation issues in {repo_name}.\n\nContext: The Code is in {self.staging_dir}/{repo_name}.\n\nIssues:\n{issue_text}",
            "droplet_name": repo_name,
            "approval_mode": "auto",
            "auto_deploy": False
        }
        
        intent_file = self.intents_dir / f"fix-{repo_name}-{int(time.time())}.json"
        with open(intent_file, "w") as f:
            json.dump(intent, f, indent=2)
            
        logger.info(f"📨 Intent dropped: {intent_file}")

    async def promote_to_production(self, repo_name: str, source_path: Path):
        """Move code to SERVICES/ and commit."""
        logger.info(f"🏆 Promoting {repo_name} to Production...")
        
        dest_path = self.production_dir / repo_name
        
        # Move files
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.move(str(source_path), str(dest_path))
        
        # Git Commit
        try:
            await run_command(["git", "add", str(dest_path)], cwd=self.root_dir)
            await run_command(["git", "commit", "-m", f"feat: Gatekeeper promoted {repo_name} (Verified)"], cwd=self.root_dir)
            # await run_command(["git", "push"], cwd=self.root_dir) # Optional: Push immediately or let human push
            logger.info(f"✅ Committed to {dest_path}")
        except Exception as e:
            logger.warning(f"File moved but git commit failed: {e}")

    async def process(self, url: str, branch: str, name: str):
        """Main Gatekeeper Workflow."""
        try:
            # 1. Harvest
            path = await self.harvest_safe(url, branch, name)
            
            # 2. Verify
            report = await self.verify_codebase(path, name)
            
            score = report.get("summary", {}).get("score", 0)
            decision = report.get("decision", "REJECT")
            
            logger.info(f"📊 Score: {score}/100 | Decision: {decision}")
            
            if self.telemetry:
                self.telemetry.capture("gatekeeper", "verification_complete", {
                    "repo_name": name,
                    "score": score,
                    "decision": decision,
                    "report_summary": report.get("summary", {})
                })

            # 3. Decide
            if decision == "APPROVED" or score >= 90:
                await self.promote_to_production(name, path)
                print(f"\n✅ SUCCESS: {name} merged to production.\n")
                
                if self.telemetry:
                    self.telemetry.capture("gatekeeper", "promotion_success", {
                        "repo_name": name
                    })
            else:
                await self.dispatch_fix_mission(name, report)
                print(f"\n❌ REJECTED: {name} needs fixes. Autonomous Agent dispatched.\n")
                
                if self.telemetry:
                    self.telemetry.capture("gatekeeper", "promotion_rejected", {
                        "repo_name": name,
                        "action": "fix_dispatched"
                    })
                
        except Exception as e:
            logger.error(f"Gatekeeper halted: {e}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gatekeeper: Verify then Trust")
    parser.add_argument("--url", required=True, help="Git URL")
    parser.add_argument("--name", required=True, help="Target Name (e.g. my-service)")
    parser.add_argument("--branch", default="main", help="Branch")
    
    args = parser.parse_args()
    
    keeper = Gatekeeper()
    asyncio.run(keeper.process(args.url, args.branch, args.name))

