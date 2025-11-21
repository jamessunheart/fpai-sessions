#!/usr/bin/env python3
"""
AUTONOMOUS VERIFICATION - Zero Commands Required

Architect declares intent, system verifies everything automatically.
Reports results when complete.
"""

import subprocess
import sys
import time
import json
import os
from pathlib import Path

def print_section(title):
    """Print a section header"""
    print("\n" + "━" * 70)
    print(f"🔍 {title}")
    print("━" * 70 + "\n")

def run_command(cmd, cwd=None, capture=True):
    """Run a command and return output"""
    try:
        if capture:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True, cwd=cwd)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def setup_verifier():
    """Automatically setup and start Verifier service"""
    print_section("SETTING UP VERIFIER SERVICE")

    verifier_path = Path("/Users/jamessunheart/Development/SERVICES/verifier")

    if not verifier_path.exists():
        print("❌ Verifier not found at expected path")
        return False, None

    print(f"📁 Found Verifier at: {verifier_path}")

    # Check if venv exists, recreate if corrupted
    venv_path = verifier_path / ".venv"

    # Always recreate venv to ensure it's fresh
    if venv_path.exists():
        print("🗑️  Removing old virtual environment...")
        run_command(f"rm -rf .venv", cwd=verifier_path)

    print("📦 Creating fresh virtual environment...")
    success, stdout, stderr = run_command("python3 -m venv .venv", cwd=verifier_path)
    if not success:
        print(f"❌ Failed to create venv: {stderr}")
        return False, None
    print("✅ Virtual environment created")

    # Install dependencies (use venv's pip directly)
    print("📦 Installing dependencies...")
    pip_path = venv_path / "bin" / "pip"
    pip_cmd = f"{pip_path} install -q -r requirements.txt"
    success, stdout, stderr = run_command(pip_cmd, cwd=verifier_path)
    if not success:
        print(f"⚠️  Warning: pip install had issues: {stderr[:200]}")
    else:
        print("✅ Dependencies installed")

    # Start Verifier service in background (use venv's uvicorn directly)
    print("🚀 Starting Verifier service...")
    uvicorn_path = venv_path / "bin" / "uvicorn"
    start_cmd = f"{uvicorn_path} app.main:app --port 8200 > /tmp/verifier.log 2>&1 &"
    success, stdout, stderr = run_command(start_cmd, cwd=verifier_path)

    # Wait for service to start
    print("⏳ Waiting for Verifier to start...")
    for i in range(20):
        time.sleep(1)
        # Check if service is responding
        success, stdout, stderr = run_command("curl -s http://localhost:8200/health")
        if success and stdout:
            print("✅ Verifier service started successfully")
            return True, verifier_path

    print("❌ Verifier failed to start within 20 seconds")
    print("Check logs: tail /tmp/verifier.log")
    return False, None

def submit_verification(droplet_path, droplet_name):
    """Submit a droplet for verification"""
    print(f"\n📤 Submitting {droplet_name} for verification...")

    payload = {
        "droplet_path": str(droplet_path),
        "droplet_name": droplet_name,
        "quick_mode": False
    }

    cmd = f"curl -s -X POST http://localhost:8200/verify -H 'Content-Type: application/json' -d '{json.dumps(payload)}'"
    success, stdout, stderr = run_command(cmd)

    if not success:
        print(f"❌ Failed to submit verification: {stderr}")
        return None

    try:
        response = json.loads(stdout)
        job_id = response.get("job_id")
        print(f"✅ Verification job created: {job_id}")
        return job_id
    except json.JSONDecodeError:
        print(f"❌ Invalid response: {stdout}")
        return None

def wait_for_verification(job_id, droplet_name, timeout=300):
    """Wait for verification to complete and return results"""
    print(f"⏳ Running verification for {droplet_name}...")
    print("   (This takes 3-5 minutes)")

    start_time = time.time()

    while time.time() - start_time < timeout:
        cmd = f"curl -s http://localhost:8200/verify/{job_id}"
        success, stdout, stderr = run_command(cmd)

        if not success:
            time.sleep(3)
            continue

        try:
            response = json.loads(stdout)
            status = response.get("status")

            if status == "completed":
                print(f"\n✅ {droplet_name} verification completed!")
                return True, response
            elif status == "failed":
                print(f"\n❌ {droplet_name} verification failed!")
                return False, response
            else:
                # Still running, show progress
                print(".", end="", flush=True)
                time.sleep(3)

        except json.JSONDecodeError:
            time.sleep(3)
            continue

    print(f"\n⏰ Verification timed out after {timeout} seconds")
    return False, None

def print_verification_results(droplet_name, response):
    """Print verification results in a readable format"""
    print_section(f"RESULTS: {droplet_name.upper()}")

    summary = response.get("summary", {})

    decision = summary.get("decision", "UNKNOWN")
    phases_passed = summary.get("phases_passed", 0)
    total_phases = summary.get("total_phases", 6)

    # Print decision
    if decision == "APPROVED":
        print("🎉 DECISION: ✅ APPROVED")
        print(f"   All {total_phases} phases passed!")
    elif decision == "FIXES_REQUIRED":
        print("⚠️  DECISION: ❌ FIXES REQUIRED")
        print(f"   Passed: {phases_passed}/{total_phases} phases")
    else:
        print(f"❓ DECISION: {decision}")

    print()

    # Print phase results
    phases = response.get("phases", [])
    if phases:
        print("📊 Phase Results:")
        for phase in phases:
            phase_name = phase.get("phase", "Unknown")
            phase_status = phase.get("status", "unknown")

            if phase_status == "passed":
                status_icon = "✅"
            elif phase_status == "failed":
                status_icon = "❌"
            else:
                status_icon = "⏳"

            print(f"   {status_icon} {phase_name:20s} - {phase_status}")

            # Print issues if any
            issues = phase.get("issues", [])
            if issues:
                for issue in issues[:3]:  # Show first 3 issues
                    print(f"      • {issue}")
                if len(issues) > 3:
                    print(f"      ... and {len(issues) - 3} more issues")

    print()

    # Print recommendations
    recommendations = summary.get("recommendations", [])
    if recommendations:
        print("💡 Recommendations:")
        for rec in recommendations:
            print(f"   • {rec}")
        print()

def main():
    """Main autonomous verification flow"""
    print("\n" + "🌟" * 35)
    print("AUTONOMOUS VERIFICATION - ZERO COMMANDS REQUIRED")
    print("🌟" * 35)

    # Setup Verifier
    verifier_running, verifier_path = setup_verifier()
    if not verifier_running:
        print("\n❌ Failed to start Verifier service")
        print("   Check manually: cd /Users/jamessunheart/Development/SERVICES/verifier")
        return 1

    # Services to verify
    services = [
        {
            "path": "/Users/jamessunheart/Development/SERVICES/i-proactive",
            "name": "i-proactive"
        },
        {
            "path": "/Users/jamessunheart/Development/SERVICES/i-match",
            "name": "i-match"
        }
    ]

    results = {}

    # Verify each service
    for service in services:
        print_section(f"VERIFYING: {service['name'].upper()}")

        # Submit verification
        job_id = submit_verification(service['path'], service['name'])
        if not job_id:
            results[service['name']] = {"success": False, "error": "Failed to submit"}
            continue

        # Wait for results
        success, response = wait_for_verification(job_id, service['name'])

        if success and response:
            results[service['name']] = {"success": True, "response": response}
            print_verification_results(service['name'], response)
        else:
            results[service['name']] = {"success": False, "error": "Verification failed or timed out"}

    # Final summary
    print_section("FINAL SUMMARY")

    approved = 0
    fixes_required = 0
    failed = 0

    for service_name, result in results.items():
        if result.get("success"):
            response = result.get("response", {})
            decision = response.get("summary", {}).get("decision", "UNKNOWN")

            if decision == "APPROVED":
                print(f"✅ {service_name:20s} - APPROVED (Ready to deploy)")
                approved += 1
            elif decision == "FIXES_REQUIRED":
                print(f"⚠️  {service_name:20s} - FIXES REQUIRED")
                fixes_required += 1
            else:
                print(f"❓ {service_name:20s} - {decision}")
        else:
            print(f"❌ {service_name:20s} - FAILED")
            failed += 1

    print()
    print(f"Total Services: {len(services)}")
    print(f"✅ Approved: {approved}")
    print(f"⚠️  Fixes Required: {fixes_required}")
    print(f"❌ Failed: {failed}")
    print()

    if approved == len(services):
        print("🎉 ALL SERVICES APPROVED!")
        print("   Ready to deploy to production with 100% confidence")
        return 0
    else:
        print("⚠️  Some services need attention")
        print("   Review issues above and fix before deploying")
        return 1

if __name__ == "__main__":
    sys.exit(main())
