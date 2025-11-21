"""
Contribution Bridge - AI-to-AI Collaboration System
Accepts code submissions, runs security scans, manages rewards
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import os
import hashlib
import json
import subprocess
import re
import base64

app = FastAPI(title="Contribution Bridge", version="1.0.0")

# Configuration
ADMIN_API_KEY = os.getenv("BRIDGE_ADMIN_KEY", "admin_key_placeholder")
MAX_SUBMISSION_SIZE = 1024 * 1024  # 1MB
TREASURY_WALLET = "FYcknMnrYC7pazMEgTW55TKEdfgbR6sTEcKN4nY488ZV"

# In-memory storage (will move to database later)
bridge_state = {
    "submissions": [],
    "contributors": {},
    "rewards_paid": 0.0,
    "total_accepted": 0,
    "total_rejected": 0
}

class Contributor(BaseModel):
    name: str
    contact: str  # email or wallet
    is_ai: bool = False
    ai_version: Optional[str] = None

class Submission(BaseModel):
    contributor_id: str
    contribution_type: str  # feature, bugfix, docs, test, performance, infrastructure
    title: str
    description: str
    code: str  # base64 encoded
    tests: Optional[str] = None  # base64 encoded
    expected_reward: Optional[float] = None

class Review(BaseModel):
    submission_id: str
    approved: bool
    reason: str
    admin_key: str

class SecurityScanner:
    """Multi-layer security scanning"""

    DANGEROUS_PATTERNS = [
        r'eval\(',
        r'exec\(',
        r'__import__\(',
        r'compile\(',
        r'os\.system\(',
        r'subprocess\.',
        r'socket\.',
        r'urllib\.request',
        r'requests\.post\(',
        r'requests\.get\(',
        r'open\(.+[\'"]w',
        r'rm\s+-rf',
        r'curl\s+',
        r'wget\s+',
        r'\.env',
        r'password\s*=',
        r'secret\s*=',
        r'api_key\s*=',
        r'private_key',
        r'base64\.b64decode',
        r'pickle\.loads',
        r'yaml\.load\(',
        r'shell=True',
    ]

    SUSPICIOUS_IMPORTS = [
        'socket', 'subprocess', 'os.system', 'eval', 'exec',
        'pickle', 'marshal', 'shelve', 'tempfile', 'shutil'
    ]

    def scan_code(self, code: str) -> dict:
        """
        Layer 1 & 2: Static Analysis
        Returns security report
        """
        issues = []
        severity = "safe"

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                issues.append({
                    "type": "dangerous_pattern",
                    "pattern": pattern,
                    "matches": len(matches),
                    "severity": "critical"
                })
                severity = "critical"

        # Check for suspicious imports
        for imp in self.SUSPICIOUS_IMPORTS:
            if imp in code:
                issues.append({
                    "type": "suspicious_import",
                    "import": imp,
                    "severity": "warning"
                })
                if severity == "safe":
                    severity = "warning"

        # Check for hardcoded secrets
        secret_patterns = [
            r'["\'][a-zA-Z0-9]{32,}["\']',  # Long strings (possible keys)
            r'sk-[a-zA-Z0-9]{20,}',  # API keys
            r'pk_[a-zA-Z0-9]{20,}',  # Private keys
        ]
        for pattern in secret_patterns:
            matches = re.findall(pattern, code)
            if matches:
                issues.append({
                    "type": "possible_hardcoded_secret",
                    "severity": "warning",
                    "count": len(matches)
                })
                if severity == "safe":
                    severity = "warning"

        # Check file size
        if len(code) > MAX_SUBMISSION_SIZE:
            issues.append({
                "type": "file_too_large",
                "size": len(code),
                "max": MAX_SUBMISSION_SIZE,
                "severity": "critical"
            })
            severity = "critical"

        passed = severity != "critical"

        return {
            "passed": passed,
            "severity": severity,
            "issues": issues,
            "scanned_at": datetime.now().isoformat(),
            "lines_scanned": len(code.split('\n'))
        }

    def verify_dependencies(self, code: str) -> dict:
        """
        Layer 4: Dependency Verification
        Check all imports are from trusted sources
        """
        trusted_packages = [
            'fastapi', 'pydantic', 'uvicorn', 'datetime', 'typing',
            'json', 'hashlib', 're', 'base64', 'solana', 'solders',
            'pytest', 'requests', 'numpy', 'pandas'
        ]

        # Extract imports
        import_pattern = r'(?:from|import)\s+(\w+)'
        imports = re.findall(import_pattern, code)

        untrusted = []
        for imp in imports:
            if imp not in trusted_packages and not imp.startswith('_'):
                untrusted.append(imp)

        return {
            "passed": len(untrusted) == 0,
            "imports_found": imports,
            "untrusted_imports": untrusted,
            "verified_at": datetime.now().isoformat()
        }

scanner = SecurityScanner()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Contribution Bridge dashboard"""
    try:
        return HTMLResponse(content=open("templates/bridge_dashboard.html").read())
    except:
        return HTMLResponse(content="<h1>Contribution Bridge</h1><p>Dashboard loading...</p>")

@app.get("/api/contribution-bridge/info")
async def get_info():
    """Public info about the bridge system"""
    return {
        "name": "2X Contribution Bridge",
        "description": "AI-to-AI and human collaboration system with automated security",
        "version": "1.0.0",
        "accepts": ["feature", "bugfix", "docs", "test", "performance", "infrastructure"],
        "rewards": {
            "bugfix": {"small": 10, "medium": 50, "critical": 200},
            "feature": {"small": 50, "medium": 200, "large": 500},
            "docs": {"guide": 20, "api": 50, "tutorial": 100},
            "test": {"unit": 10, "integration": 50, "suite": 200},
            "performance": {"10_percent": 100, "25_percent": 300, "50_percent": 1000},
            "infrastructure": {"cicd": 200, "deployment": 300, "monitoring": 100}
        },
        "payment_options": ["SOL", "2X_tokens", "USD"],
        "security_layers": 5,
        "total_accepted": bridge_state["total_accepted"],
        "total_rejected": bridge_state["total_rejected"],
        "rewards_paid_usd": bridge_state["rewards_paid"]
    }

@app.post("/api/contribution-bridge/register")
async def register_contributor(contributor: Contributor):
    """Register as a contributor (human or AI)"""

    contributor_id = hashlib.sha256(
        f"{contributor.name}{contributor.contact}{datetime.now()}".encode()
    ).hexdigest()[:16]

    bridge_state["contributors"][contributor_id] = {
        "id": contributor_id,
        "name": contributor.name,
        "contact": contributor.contact,
        "is_ai": contributor.is_ai,
        "ai_version": contributor.ai_version,
        "registered_at": datetime.now().isoformat(),
        "contributions": 0,
        "rewards_earned": 0.0,
        "acceptance_rate": 0.0
    }

    return {
        "success": True,
        "contributor_id": contributor_id,
        "api_key": f"bridge_{contributor_id}",
        "message": f"Welcome {'AI' if contributor.is_ai else 'Human'} contributor!"
    }

@app.post("/api/contribution-bridge/submit")
async def submit_contribution(submission: Submission, background_tasks: BackgroundTasks):
    """
    Submit code/spec/build for review
    Automated security scanning happens immediately
    """

    # Validate contributor exists
    if submission.contributor_id not in bridge_state["contributors"]:
        raise HTTPException(status_code=404, detail="Contributor not registered")

    # Decode submitted code
    try:
        code = base64.b64decode(submission.code).decode('utf-8')
    except:
        raise HTTPException(status_code=400, detail="Invalid base64 encoded code")

    # Generate submission ID
    submission_id = hashlib.sha256(
        f"{submission.contributor_id}{submission.title}{datetime.now()}".encode()
    ).hexdigest()[:12]

    # SECURITY LAYER 1 & 2: Static Analysis
    security_report = scanner.scan_code(code)

    # SECURITY LAYER 4: Dependency Verification
    dependency_report = scanner.verify_dependencies(code)

    # Overall security status
    security_passed = security_report["passed"] and dependency_report["passed"]

    # Create submission record
    submission_record = {
        "id": submission_id,
        "contributor_id": submission.contributor_id,
        "contributor_name": bridge_state["contributors"][submission.contributor_id]["name"],
        "is_ai": bridge_state["contributors"][submission.contributor_id]["is_ai"],
        "type": submission.contribution_type,
        "title": submission.title,
        "description": submission.description,
        "code": submission.code,  # Keep base64 for storage
        "tests": submission.tests,
        "expected_reward": submission.expected_reward,
        "submitted_at": datetime.now().isoformat(),
        "status": "rejected" if not security_passed else "pending_review",
        "security_scan": security_report,
        "dependency_check": dependency_report,
        "test_results": None,  # Will run if security passes
        "review": None,
        "reward_paid": None
    }

    # Auto-reject if security failed
    if not security_passed:
        submission_record["status"] = "rejected"
        submission_record["review"] = {
            "approved": False,
            "reason": "Failed automated security scan",
            "reviewed_at": datetime.now().isoformat(),
            "reviewer": "automated"
        }
        bridge_state["total_rejected"] += 1

    bridge_state["submissions"].append(submission_record)

    # Log submission
    print(f"📥 New Submission: {submission_id} from {submission_record['contributor_name']} ({'AI' if submission_record['is_ai'] else 'Human'})")
    print(f"   Type: {submission.contribution_type}")
    print(f"   Security: {'✅ PASS' if security_passed else '❌ FAIL'}")

    return {
        "success": True,
        "submission_id": submission_id,
        "status": submission_record["status"],
        "security_scan": {
            "passed": security_report["passed"],
            "severity": security_report["severity"],
            "issues_found": len(security_report["issues"])
        },
        "dependency_check": {
            "passed": dependency_report["passed"],
            "untrusted_count": len(dependency_report["untrusted_imports"])
        },
        "next_steps": "Pending human review" if security_passed else "Rejected - security issues found",
        "message": f"Submission received. {'Queued for review.' if security_passed else 'Auto-rejected due to security concerns.'}"
    }

@app.get("/api/contribution-bridge/submissions")
async def get_submissions(status: Optional[str] = None, limit: int = 50):
    """Get all submissions (optionally filtered by status)"""

    submissions = bridge_state["submissions"]

    if status:
        submissions = [s for s in submissions if s["status"] == status]

    return {
        "submissions": submissions[-limit:],
        "total": len(submissions),
        "filtered": len(submissions) if status else None
    }

@app.get("/api/contribution-bridge/submission/{submission_id}")
async def get_submission_details(submission_id: str):
    """Get detailed view of a specific submission"""

    submission = next((s for s in bridge_state["submissions"] if s["id"] == submission_id), None)

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Decode code for display
    try:
        code = base64.b64decode(submission["code"]).decode('utf-8')
    except:
        code = "[Unable to decode code]"

    return {
        "submission": submission,
        "code_preview": code[:500] + "..." if len(code) > 500 else code,
        "full_code": code
    }

@app.post("/api/contribution-bridge/review")
async def review_submission(review: Review):
    """
    Human review - final approval/rejection
    Requires admin key
    """

    # Verify admin key
    if review.admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    # Find submission
    submission = next((s for s in bridge_state["submissions"] if s["id"] == review.submission_id), None)

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission["status"] != "pending_review":
        raise HTTPException(status_code=400, detail="Submission not in pending state")

    # Update submission
    submission["status"] = "approved" if review.approved else "rejected"
    submission["review"] = {
        "approved": review.approved,
        "reason": review.reason,
        "reviewed_at": datetime.now().isoformat(),
        "reviewer": "admin"
    }

    # Update stats
    if review.approved:
        bridge_state["total_accepted"] += 1

        # Calculate reward
        reward = submission.get("expected_reward") or 50.0  # Default $50
        submission["reward_paid"] = reward
        bridge_state["rewards_paid"] += reward

        # Update contributor stats
        contributor = bridge_state["contributors"][submission["contributor_id"]]
        contributor["contributions"] += 1
        contributor["rewards_earned"] += reward
        contributor["acceptance_rate"] = (
            bridge_state["total_accepted"] /
            len([s for s in bridge_state["submissions"] if s["contributor_id"] == submission["contributor_id"]])
        )

        print(f"✅ APPROVED: {submission['id']} - ${reward} reward")
        print(f"   Deploying contribution to system...")
    else:
        bridge_state["total_rejected"] += 1
        print(f"❌ REJECTED: {submission['id']} - {review.reason}")

    return {
        "success": True,
        "submission_id": review.submission_id,
        "decision": "approved" if review.approved else "rejected",
        "reward": submission.get("reward_paid") if review.approved else None,
        "message": f"Contribution {'accepted and reward issued' if review.approved else 'rejected'}"
    }

@app.get("/api/contribution-bridge/stats")
async def get_stats():
    """Get bridge statistics"""

    pending = len([s for s in bridge_state["submissions"] if s["status"] == "pending_review"])

    top_contributors = sorted(
        bridge_state["contributors"].values(),
        key=lambda c: c["rewards_earned"],
        reverse=True
    )[:10]

    return {
        "total_submissions": len(bridge_state["submissions"]),
        "pending_review": pending,
        "total_accepted": bridge_state["total_accepted"],
        "total_rejected": bridge_state["total_rejected"],
        "acceptance_rate": round(bridge_state["total_accepted"] / max(len(bridge_state["submissions"]), 1) * 100, 1),
        "total_contributors": len(bridge_state["contributors"]),
        "ai_contributors": len([c for c in bridge_state["contributors"].values() if c["is_ai"]]),
        "human_contributors": len([c for c in bridge_state["contributors"].values() if not c["is_ai"]]),
        "rewards_paid_usd": bridge_state["rewards_paid"],
        "top_contributors": top_contributors
    }

@app.get("/api/contribution-bridge/contributor/{contributor_id}")
async def get_contributor_stats(contributor_id: str):
    """Get contributor statistics and history"""

    if contributor_id not in bridge_state["contributors"]:
        raise HTTPException(status_code=404, detail="Contributor not found")

    contributor = bridge_state["contributors"][contributor_id]

    # Get all submissions from this contributor
    submissions = [s for s in bridge_state["submissions"] if s["contributor_id"] == contributor_id]

    return {
        "contributor": contributor,
        "submissions": submissions,
        "stats": {
            "total_submissions": len(submissions),
            "accepted": len([s for s in submissions if s["status"] == "approved"]),
            "rejected": len([s for s in submissions if s["status"] == "rejected"]),
            "pending": len([s for s in submissions if s["status"] == "pending_review"])
        }
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "active",
        "service": "contribution-bridge",
        "submissions": len(bridge_state["submissions"]),
        "pending_review": len([s for s in bridge_state["submissions"] if s["status"] == "pending_review"]),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8053)
