#!/usr/bin/env python3
"""
Delegate Testnet Deployment via API

This script connects to your delegation server and creates the VA task.
"""

import subprocess
import json
import sys
from pathlib import Path

SERVER = "198.54.123.234"
SERVER_USER = "root"
DELEGATION_DIR = "/root/delegation-system"

def run_ssh_command(command):
    """Execute command on delegation server via SSH"""

    ssh_cmd = [
        "ssh",
        f"{SERVER_USER}@{SERVER}",
        f"cd {DELEGATION_DIR} && {command}"
    ]

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def create_task_on_server():
    """Create the testnet deployment task on delegation server"""

    print("\n" + "="*70)
    print("🚀 CREATING TESTNET DEPLOYMENT TASK VIA API")
    print("="*70)

    # Read task definition
    task_file = Path(__file__).parent.parent / "delegation" / "testnet_deployment_task.json"

    if not task_file.exists():
        print(f"\n❌ Task definition not found: {task_file}")
        return None

    with open(task_file) as f:
        task_data = json.load(f)

    print(f"\n📋 Task: {task_data['title']}")
    print(f"Budget: ${task_data['budget']['amount']}")
    print(f"Timeline: {task_data['timeline']}")

    # Create Python script to run on server
    python_script = f"""
import json
from upwork_recruiter import TaskDelegator

# Task data
task_data = {json.dumps({
    'description': task_data['description'],
    'deliverables': task_data['deliverables'],
    'deadline': task_data['timeline'],
    'credentials': [],  # No credentials needed
    'budget': task_data['budget']['amount']
})}

# Create task
delegator = TaskDelegator()
result = delegator.delegate_task(task_data)

# Output result as JSON
print(json.dumps(result, indent=2))
"""

    # Save script in delegation-system directory
    script_path = f"{DELEGATION_DIR}/create_testnet_task.py"

    print(f"\n🔄 Connecting to delegation server: {SERVER_USER}@{SERVER}")

    # Upload and execute
    upload_cmd = f"cat > {script_path} << 'EOFPYTHON'\n{python_script}\nEOFPYTHON"

    print(f"📤 Uploading task creation script...")
    result = run_ssh_command(upload_cmd)

    if not result['success']:
        print(f"\n❌ Failed to upload script: {result['error']}")
        return None

    print(f"✅ Script uploaded")

    # Execute (with proper directory context)
    print(f"\n⚡ Creating task...")
    exec_result = run_ssh_command(f"cd /root/delegation-system && python3 {script_path}")

    if not exec_result['success']:
        print(f"\n❌ Failed to create task: {exec_result['error']}")
        return None

    # Parse result
    try:
        task_result = json.loads(exec_result['output'])
    except:
        print(f"\n⚠️  Task created but couldn't parse result")
        print(f"Output: {exec_result['output']}")
        task_result = {"status": "unknown"}

    print(f"\n✅ Task created successfully!")
    print(f"\nTask Details:")
    print(json.dumps(task_result, indent=2))

    return task_result


def get_task_status():
    """Get current tasks from server"""

    print(f"\n📊 Fetching current tasks...")

    command = "cat upwork-api/task_log.json 2>/dev/null || echo '[]'"
    result = run_ssh_command(command)

    if result['success']:
        try:
            tasks = json.loads(result['output'])
            return tasks
        except:
            return []
    return []


def get_upwork_job_posting():
    """Get the job posting text for manual posting"""

    posting_file = Path(__file__).parent.parent / "UPWORK_JOB_POSTING.md"

    if posting_file.exists():
        return posting_file.read_text()
    return None


def main():
    """Main delegation workflow"""

    print("\n" + "🔥"*35)
    print("FPAI TESTNET DEPLOYMENT - VA DELEGATION")
    print("🔥"*35)

    print("\n💡 This script will:")
    print("   1. Connect to your delegation server")
    print("   2. Create the testnet deployment task")
    print("   3. Generate Upwork job posting")
    print("   4. Provide next steps")

    # Check existing tasks first
    print("\n" + "="*70)
    print("STEP 1: CHECK EXISTING TASKS")
    print("="*70)

    existing_tasks = get_task_status()

    if existing_tasks:
        print(f"\n📊 Found {len(existing_tasks)} existing task(s):")
        for task in existing_tasks:
            print(f"\n   Task: {task.get('description', 'Unknown')[:50]}...")
            print(f"   Status: {task.get('status', 'unknown')}")
            print(f"   Budget: ${task.get('budget', 0)}")
    else:
        print(f"\n✨ No existing tasks found")

    # Create new task
    print("\n" + "="*70)
    print("STEP 2: CREATE NEW TASK")
    print("="*70)

    task = create_task_on_server()

    if not task:
        print("\n❌ Failed to create task via API")
        print("\n💡 Fallback: You can create the task manually on the server:")
        print(f"\n   ssh {SERVER_USER}@{SERVER}")
        print(f"   cd {DELEGATION_DIR}")
        print(f"   python3 -c \"from upwork_recruiter import TaskDelegator; ...\"")
        sys.exit(1)

    # Get job posting
    print("\n" + "="*70)
    print("STEP 3: GET UPWORK JOB POSTING")
    print("="*70)

    job_posting = get_upwork_job_posting()

    if job_posting:
        print(f"\n✅ Job posting ready ({len(job_posting)} characters)")

        # Save to file for easy access
        output_file = Path("/tmp/upwork_testnet_posting.txt")
        output_file.write_text(job_posting)
        print(f"\n💾 Saved to: {output_file}")
    else:
        print(f"\n⚠️  Job posting file not found")

    # Next steps
    print("\n" + "="*70)
    print("✅ TASK CREATED SUCCESSFULLY!")
    print("="*70)

    print("\n📋 TASK SUMMARY:")
    print(f"   ID: {task.get('id', 'N/A')}")
    print(f"   Status: {task.get('status', 'pending')}")
    print(f"   Budget: ${task.get('budget', 15)}")

    print("\n" + "="*70)
    print("📤 NEXT STEPS:")
    print("="*70)

    print("\n1️⃣  POST TO UPWORK")
    print("   ────────────────────")
    print(f"   • Go to: https://www.upwork.com/nx/wm/client/postjob")
    print(f"   • Copy posting from: /tmp/upwork_testnet_posting.txt")
    print(f"   • Or use: UPWORK_JOB_POSTING.md")
    print(f"   • Job type: Fixed price")
    print(f"   • Budget: $15 (or $10-20 range)")
    print(f"   • Experience: Entry level")

    print("\n2️⃣  SCREEN APPLICANTS")
    print("   ────────────────────")
    print(f"   Look for:")
    print(f"   ✅ Answered all 3 questions")
    print(f"   ✅ Included 'TESTNET READY'")
    print(f"   ✅ Clear communication")
    print(f"   ✅ Available within 2-4 hours")

    print("\n3️⃣  HIRE 2-3 VAs")
    print("   ────────────────────")
    print(f"   • Test multiple in parallel")
    print(f"   • See who delivers best")
    print(f"   • Keep winners")

    print("\n4️⃣  MONITOR PROGRESS")
    print("   ────────────────────")
    print(f"   Dashboard: http://{SERVER}:8007")
    print(f"   Or SSH: ssh {SERVER_USER}@{SERVER}")

    print("\n5️⃣  VERIFY & PAY")
    print("   ────────────────────")
    print(f"   • Check Etherscan link")
    print(f"   • Verify deployment")
    print(f"   • Release $15 payment")

    print("\n" + "="*70)
    print("🎯 AUTOMATION OPTIONS:")
    print("="*70)

    print("\n💡 For full automation (requires setup):")
    print(f"   1. Setup Upwork OAuth on server")
    print(f"   2. Run: ssh {SERVER_USER}@{SERVER}")
    print(f"   3. Run: cd {DELEGATION_DIR}")
    print(f"   4. Run: python3 delegation_orchestrator.py")
    print(f"   → Automatically posts, screens, hires, monitors")

    print("\n💡 Current (semi-automated):")
    print(f"   1. Task created via API ✅")
    print(f"   2. Post to Upwork manually")
    print(f"   3. Screen with our AI system")
    print(f"   4. Monitor via dashboard")

    print("\n" + "="*70)
    print("📊 VIEW DASHBOARD:")
    print("="*70)

    print(f"\n🌐 Open: http://{SERVER}:8007")
    print(f"   • Overview: Current status")
    print(f"   • Tasks: Track this deployment")
    print(f"   • Spending: Monitor $15 payment")
    print(f"   • Credentials: Store results")

    print("\n" + "="*70)
    print("✅ READY TO DELEGATE!")
    print("="*70)

    print(f"\n💎 Task created on delegation server")
    print(f"📤 Job posting ready: /tmp/upwork_testnet_posting.txt")
    print(f"🎯 Next: Post to Upwork and hire VAs!")

    print("\n" + "🔥"*35 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
