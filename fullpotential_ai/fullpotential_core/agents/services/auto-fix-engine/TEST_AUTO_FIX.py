#!/usr/bin/env python3
"""
Test Auto-Fix Engine on I PROACTIVE

This script demonstrates the complete autonomous Sacred Loop:
1. Start Verifier (if not running)
2. Start Auto-Fix Engine
3. Submit I PROACTIVE for verification
4. Submit verification report to Auto-Fix Engine
5. Watch Auto-Fix Engine fix issues automatically
6. Verify service becomes APPROVED
"""

import subprocess
import time
import httpx
import json
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a shell command"""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stdout, result.stderr


def check_service_running(port):
    """Check if service is running on port"""
    try:
        response = httpx.get(f"http://localhost:{port}/health", timeout=2.0)
        return response.status_code == 200
    except:
        return False


def start_verifier():
    """Start Verifier service"""
    print("\n🔍 Starting Verifier...")

    verifier_path = Path("/Users/jamessunheart/Development/agents/services/verifier")
    venv_path = verifier_path / ".venv"

    # Check if already running
    if check_service_running(8200):
        print("✅ Verifier already running on port 8200")
        return True

    # Create venv if needed
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        success, _, _ = run_command("python3 -m venv .venv", cwd=verifier_path)
        if not success:
            print("❌ Failed to create venv")
            return False

    # Install dependencies
    print("📦 Installing dependencies...")
    pip_path = venv_path / "bin" / "pip"
    success, _, _ = run_command(f"{pip_path} install -q -r requirements.txt", cwd=verifier_path)

    # Start Verifier in background
    print("🚀 Starting Verifier service...")
    uvicorn_path = venv_path / "bin" / "uvicorn"
    start_cmd = f"nohup {uvicorn_path} app.main:app --port 8200 > /tmp/verifier.log 2>&1 &"
    run_command(start_cmd, cwd=verifier_path)

    # Wait for startup
    for i in range(10):
        time.sleep(2)
        if check_service_running(8200):
            print("✅ Verifier started on port 8200")
            return True

    print("❌ Verifier failed to start")
    return False


def start_auto_fix_engine():
    """Start Auto-Fix Engine"""
    print("\n🛠️  Starting Auto-Fix Engine...")

    engine_path = Path("/Users/jamessunheart/Development/agents/services/auto-fix-engine")
    venv_path = engine_path / ".venv"

    # Check if already running
    if check_service_running(8300):
        print("✅ Auto-Fix Engine already running on port 8300")
        return True

    # Create venv if needed
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        success, _, _ = run_command("python3 -m venv .venv", cwd=engine_path)
        if not success:
            print("❌ Failed to create venv")
            return False

    # Install dependencies
    print("📦 Installing dependencies...")
    pip_path = venv_path / "bin" / "pip"
    success, _, _ = run_command(f"{pip_path} install -q -r requirements.txt", cwd=engine_path)

    # Create .env if needed (with ANTHROPIC_API_KEY from environment)
    import os
    env_file = engine_path / ".env"
    if not env_file.exists():
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            print("📝 Creating .env with ANTHROPIC_API_KEY...")
            with open(env_file, 'w') as f:
                f.write(f"ANTHROPIC_API_KEY={api_key}\n")
                f.write("SERVICE_PORT=8300\n")
                f.write("VERIFIER_URL=http://localhost:8200\n")
        else:
            print("⚠️  ANTHROPIC_API_KEY not found in environment - fixes may fail")

    # Start Auto-Fix Engine in background
    print("🚀 Starting Auto-Fix Engine...")
    uvicorn_path = venv_path / "bin" / "uvicorn"
    start_cmd = f"nohup {uvicorn_path} app.main:app --port 8300 > /tmp/auto-fix-engine.log 2>&1 &"
    run_command(start_cmd, cwd=engine_path)

    # Wait for startup
    for i in range(10):
        time.sleep(2)
        if check_service_running(8300):
            print("✅ Auto-Fix Engine started on port 8300")
            return True

    print("❌ Auto-Fix Engine failed to start")
    return False


def submit_verification(droplet_path, droplet_name):
    """Submit service for verification"""
    print(f"\n📥 Submitting {droplet_name} for verification...")

    try:
        response = httpx.post(
            "http://localhost:8200/verify",
            json={
                "droplet_path": str(droplet_path),
                "droplet_name": droplet_name,
                "quick_mode": False
            },
            timeout=10.0
        )

        if response.status_code == 202:
            data = response.json()
            job_id = data.get("job_id")
            print(f"✅ Verification job created: {job_id}")
            return job_id
        else:
            print(f"❌ Failed to submit: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def wait_for_verification(job_id, timeout=180):
    """Wait for verification to complete"""
    print(f"\n⏳ Waiting for verification {job_id}...")

    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(f"http://localhost:8200/verify/{job_id}", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")

                if status == "completed":
                    print("✅ Verification completed")
                    return True
                elif status == "failed":
                    print("❌ Verification failed")
                    return False
                else:
                    print(f"   Status: {status}...")
        except:
            pass

        time.sleep(5)

    print("⏱️  Verification timeout")
    return False


def get_verification_report(job_id):
    """Get verification report"""
    try:
        response = httpx.get(f"http://localhost:8200/verify/{job_id}/report", timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def submit_auto_fix(droplet_path, droplet_name, verification_job_id):
    """Submit service for auto-fixing"""
    print(f"\n🛠️  Submitting {droplet_name} for auto-fixing...")

    try:
        response = httpx.post(
            "http://localhost:8300/fix",
            json={
                "droplet_path": str(droplet_path),
                "droplet_name": droplet_name,
                "verification_job_id": verification_job_id,
                "max_iterations": 3
            },
            timeout=10.0
        )

        if response.status_code == 200:
            data = response.json()
            fix_job_id = data.get("fix_job_id")
            print(f"✅ Auto-fix job created: {fix_job_id}")
            return fix_job_id
        else:
            print(f"❌ Failed to submit: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def monitor_auto_fix(fix_job_id, timeout=600):
    """Monitor auto-fix progress"""
    print(f"\n🔄 Monitoring auto-fix {fix_job_id}...")
    print("(This may take several minutes as it iterates through fixes)\n")

    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(f"http://localhost:8300/fix/{fix_job_id}", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                current_iteration = data.get("current_iteration", 0)
                max_iterations = data.get("max_iterations", 3)
                final_decision = data.get("final_decision")

                print(f"   Status: {status}, Iteration: {current_iteration}/{max_iterations}")

                if status in ["verified", "failed"]:
                    print(f"\n✅ Auto-fix completed!")
                    print(f"   Final Decision: {final_decision}")
                    print(f"   Total Fixes Applied: {data.get('total_fixes_applied', 0)}")
                    print(f"\nFull Status:")
                    print(json.dumps(data, indent=2))
                    return final_decision == "APPROVED"
        except Exception as e:
            print(f"   Error checking status: {e}")

        time.sleep(10)

    print("\n⏱️  Auto-fix timeout")
    return False


def main():
    """Run complete auto-fix test"""
    print("=" * 60)
    print("AUTO-FIX ENGINE TEST - SACRED LOOP COMPLETION")
    print("=" * 60)

    # Step 1: Start Verifier
    if not start_verifier():
        print("\n❌ Cannot proceed without Verifier")
        return

    # Step 2: Start Auto-Fix Engine
    if not start_auto_fix_engine():
        print("\n❌ Cannot proceed without Auto-Fix Engine")
        return

    # Step 3: Submit I PROACTIVE for verification
    i_proactive_path = Path("/Users/jamessunheart/Development/agents/services/i-proactive")

    verification_job_id = submit_verification(i_proactive_path, "i-proactive")
    if not verification_job_id:
        print("\n❌ Failed to submit verification")
        return

    # Step 4: Wait for verification to complete
    if not wait_for_verification(verification_job_id):
        print("\n❌ Verification did not complete")
        return

    # Step 5: Get verification report
    report = get_verification_report(verification_job_id)
    if report:
        decision = report.get("decision", "UNKNOWN")
        print(f"\n📊 Verification Decision: {decision}")

        if decision == "APPROVED":
            print("✅ Service already APPROVED - no fixing needed!")
            return

        # Show issues found
        print("\n📋 Issues Found:")
        for phase in report.get("phases", []):
            phase_name = phase.get("phase")
            phase_status = phase.get("status")
            if phase_status in ["FAIL", "MINOR_ISSUES"]:
                print(f"   {phase_name}: {phase_status}")
                for check in phase.get("checks", []):
                    if check.get("status") in ["FAIL", "MINOR_ISSUE"]:
                        print(f"      - {check.get('name')}: {check.get('details', '')[:80]}")

    # Step 6: Submit to Auto-Fix Engine
    fix_job_id = submit_auto_fix(i_proactive_path, "i-proactive", verification_job_id)
    if not fix_job_id:
        print("\n❌ Failed to submit auto-fix")
        return

    # Step 7: Monitor auto-fix progress
    success = monitor_auto_fix(fix_job_id)

    print("\n" + "=" * 60)
    if success:
        print("✅ SUCCESS! I PROACTIVE is now APPROVED")
        print("🎉 Sacred Loop is complete and autonomous!")
    else:
        print("⚠️  Auto-fix completed but service not yet APPROVED")
        print("   Check logs for details: /tmp/auto-fix-engine.log")
    print("=" * 60)


if __name__ == "__main__":
    main()
