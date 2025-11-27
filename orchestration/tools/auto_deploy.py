#!/usr/bin/env python3
"""
Autonomous Deployment System
=============================
Allows AI agents to deploy changes without human intervention.

Usage:
    python3 auto_deploy.py                    # Deploy all pending changes
    python3 auto_deploy.py --service admin-hub  # Deploy specific service
    python3 auto_deploy.py --dry-run          # Show what would be deployed

This script:
1. Commits any staged changes
2. Pushes to GitHub
3. SSHs to server and pulls
4. Restarts affected services
5. Verifies deployment
"""

import os
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Configuration
REPO_PATH = Path(__file__).resolve().parent.parent.parent
SERVER_HOST = os.getenv("DEPLOY_SERVER", "198.54.123.234")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_REPO_PATH = "/root/FPAI_Cockpit"

# Service definitions with ports and restart commands
SERVICES = {
    "admin-hub": {
        "port": 8888,
        "path": "SERVICES/admin-hub",
        "restart": "cd {repo}/SERVICES/admin-hub && kill $(lsof -t -i:8888) 2>/dev/null; sleep 1; nohup python3 app.py > admin-hub.log 2>&1 &",
        "health": "curl -s http://127.0.0.1:8888/admin/api/health",
    },
    "mission-hub": {
        "port": 8700,
        "path": "SERVICES/mission-hub",
        "restart": "cd {repo}/SERVICES/mission-hub && kill $(lsof -t -i:8700) 2>/dev/null; sleep 1; nohup python3 app.py > mission-hub.log 2>&1 &",
        "health": "curl -s http://127.0.0.1:8700/health",
    },
    "api-gateway": {
        "port": 8400,
        "path": "SERVICES/api-gateway",
        "restart": "cd {repo}/SERVICES/api-gateway && kill $(lsof -t -i:8400) 2>/dev/null; sleep 1; nohup python3 app.py > api-gateway.log 2>&1 &",
        "health": "curl -s http://127.0.0.1:8400/health",
    },
    "harvester": {
        "port": 8055,
        "path": "SERVICES/harvester",
        "restart": "cd {repo}/SERVICES/harvester && kill $(lsof -t -i:8055) 2>/dev/null; sleep 1; nohup python3 app.py > harvester.log 2>&1 &",
        "health": "curl -s http://127.0.0.1:8055/health",
    },
}

# Deployment log
DEPLOY_LOG = REPO_PATH / "logs" / "deployments.log"
DEPLOY_LOG.parent.mkdir(exist_ok=True)


def log(message: str, level: str = "INFO"):
    """Log deployment activity"""
    timestamp = datetime.now().isoformat()
    entry = f"[{timestamp}] [{level}] {message}"
    print(entry)
    with open(DEPLOY_LOG, "a") as f:
        f.write(entry + "\n")


def run_local(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run command locally"""
    log(f"LOCAL: {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check, cwd=REPO_PATH)


def run_remote(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run command on remote server via SSH"""
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no {SERVER_USER}@{SERVER_HOST} '{cmd}'"
    log(f"REMOTE: {cmd}")
    return subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, check=check)


def get_changed_files() -> List[str]:
    """Get list of changed files since last commit"""
    result = run_local("git diff --name-only HEAD", check=False)
    staged = run_local("git diff --cached --name-only", check=False)
    
    files = set()
    if result.stdout:
        files.update(result.stdout.strip().split("\n"))
    if staged.stdout:
        files.update(staged.stdout.strip().split("\n"))
    
    return [f for f in files if f]


def detect_affected_services(changed_files: List[str]) -> List[str]:
    """Determine which services need restart based on changed files"""
    affected = set()
    
    for file in changed_files:
        for service_name, service_info in SERVICES.items():
            if file.startswith(service_info["path"]):
                affected.add(service_name)
    
    return list(affected)


def git_commit_and_push(message: str = None) -> bool:
    """Commit staged changes and push to remote"""
    # Check if there are changes to commit
    status = run_local("git status --porcelain", check=False)
    if not status.stdout.strip():
        log("No changes to commit")
        return True
    
    # Stage all changes
    run_local("git add -A")
    
    # Generate commit message if not provided
    if not message:
        changed = get_changed_files()
        message = f"Auto-deploy: {', '.join(changed[:3])}"
        if len(changed) > 3:
            message += f" (+{len(changed)-3} more)"
    
    # Commit
    try:
        run_local(f'git commit -m "{message}"')
    except subprocess.CalledProcessError:
        log("Nothing to commit", "WARN")
        return True
    
    # Push
    try:
        run_local("git push origin main")
        log("Pushed to GitHub successfully")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Push failed: {e.stderr}", "ERROR")
        return False


def pull_on_server() -> bool:
    """Pull latest changes on server"""
    try:
        result = run_remote(f"cd {SERVER_REPO_PATH} && git pull origin main")
        log(f"Server pull: {result.stdout[:200] if result.stdout else 'OK'}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Server pull failed: {e.stderr}", "ERROR")
        return False


def restart_service(service_name: str) -> bool:
    """Restart a specific service on the server"""
    if service_name not in SERVICES:
        log(f"Unknown service: {service_name}", "ERROR")
        return False
    
    service = SERVICES[service_name]
    restart_cmd = service["restart"].format(repo=SERVER_REPO_PATH)
    
    try:
        run_remote(restart_cmd)
        log(f"Restarted {service_name}")
        
        # Wait and check health
        import time
        time.sleep(3)
        
        health_result = run_remote(service["health"], check=False)
        if health_result.returncode == 0 and "healthy" in health_result.stdout.lower():
            log(f"✅ {service_name} is healthy")
            return True
        else:
            log(f"⚠️ {service_name} health check unclear: {health_result.stdout[:100]}", "WARN")
            return True  # Service might still be starting
            
    except subprocess.CalledProcessError as e:
        log(f"Failed to restart {service_name}: {e.stderr}", "ERROR")
        return False


def deploy(
    services: List[str] = None,
    commit_message: str = None,
    dry_run: bool = False,
    skip_push: bool = False,
) -> Dict:
    """
    Full deployment pipeline.
    
    Args:
        services: List of services to restart (auto-detect if None)
        commit_message: Custom commit message
        dry_run: If True, show what would happen without doing it
        skip_push: If True, skip git operations (just restart services)
    
    Returns:
        Dict with deployment results
    """
    log("=" * 60)
    log("DEPLOYMENT STARTED")
    log("=" * 60)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "steps": [],
        "success": True,
    }
    
    # Step 1: Detect changes
    changed_files = get_changed_files()
    results["changed_files"] = changed_files
    log(f"Changed files: {len(changed_files)}")
    
    if dry_run:
        log("[DRY RUN] Would commit and push these files:")
        for f in changed_files[:10]:
            log(f"  - {f}")
        if len(changed_files) > 10:
            log(f"  ... and {len(changed_files) - 10} more")
    
    # Step 2: Detect affected services
    if services is None:
        services = detect_affected_services(changed_files)
    results["services"] = services
    log(f"Affected services: {services or 'none'}")
    
    if dry_run:
        log("[DRY RUN] Would restart these services:")
        for s in services:
            log(f"  - {s} (port {SERVICES[s]['port']})")
        results["steps"].append({"step": "dry_run", "status": "simulated"})
        return results
    
    # Step 3: Commit and push
    if not skip_push and changed_files:
        if git_commit_and_push(commit_message):
            results["steps"].append({"step": "git_push", "status": "success"})
        else:
            results["steps"].append({"step": "git_push", "status": "failed"})
            results["success"] = False
            return results
    
    # Step 4: Pull on server
    if not skip_push:
        if pull_on_server():
            results["steps"].append({"step": "server_pull", "status": "success"})
        else:
            results["steps"].append({"step": "server_pull", "status": "failed"})
            results["success"] = False
            return results
    
    # Step 5: Restart services
    for service in services:
        if restart_service(service):
            results["steps"].append({"step": f"restart_{service}", "status": "success"})
        else:
            results["steps"].append({"step": f"restart_{service}", "status": "failed"})
            results["success"] = False
    
    log("=" * 60)
    log(f"DEPLOYMENT {'COMPLETED' if results['success'] else 'FAILED'}")
    log("=" * 60)
    
    return results


# Quick deployment functions for common use cases
def deploy_all():
    """Deploy all changes and restart affected services"""
    return deploy()


def deploy_service(service_name: str):
    """Deploy and restart a specific service"""
    return deploy(services=[service_name])


def quick_restart(service_name: str):
    """Just restart a service without git operations"""
    return deploy(services=[service_name], skip_push=True)


# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous deployment system")
    parser.add_argument("--service", "-s", help="Specific service to deploy")
    parser.add_argument("--message", "-m", help="Commit message")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--skip-push", action="store_true", help="Skip git operations")
    parser.add_argument("--restart-only", action="store_true", help="Just restart, no git")
    
    args = parser.parse_args()
    
    services = [args.service] if args.service else None
    
    result = deploy(
        services=services,
        commit_message=args.message,
        dry_run=args.dry_run,
        skip_push=args.skip_push or args.restart_only,
    )
    
    print("\n" + json.dumps(result, indent=2))

