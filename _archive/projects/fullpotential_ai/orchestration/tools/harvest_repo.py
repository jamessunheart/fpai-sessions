#!/usr/bin/env python3
"""
Automate harvesting code from external repositories via git subtree.

Steps performed:
1. Add/fetch a temporary remote.
2. Run `git subtree add --prefix ... --squash`.
3. Drop the temporary remote.
4. Commit any pending changes (if subtree did not create one).
5. Push the updated main branch.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REMOTE_NAME = "temp_harvest"
PLACEHOLDER_FILES = {".gitkeep", ".keep"}


class HarvestError(RuntimeError):
    """Raised when the harvest workflow cannot proceed safely."""


def find_repo_root() -> Path:
    script_path = Path(__file__).resolve()
    for ancestor in [script_path, *script_path.parents]:
        if (ancestor / ".git").is_dir():
            return ancestor
    raise HarvestError("Unable to locate repository root (.git not found).")


def run_git(args: Sequence[str], repo_root: Path, capture_output: bool = True) -> str:
    cmd = ["git", *args]
    if capture_output:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return result.stdout.strip()
    subprocess.run(cmd, cwd=repo_root, check=True)
    return ""


def ensure_clean_worktree(repo_root: Path) -> None:
    status = run_git(["status", "--porcelain"], repo_root)
    if status:
        raise HarvestError("Working tree has uncommitted changes. Commit or stash them before harvesting.")


def ensure_on_main(repo_root: Path) -> None:
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if branch != "main":
        raise HarvestError(f"Current branch is '{branch}'. Checkout 'main' before running the harvester.")


def ensure_remote_slot_available(repo_root: Path) -> None:
    remotes = run_git(["remote"], repo_root).splitlines()
    if REMOTE_NAME in remotes:
        raise HarvestError(f"Remote '{REMOTE_NAME}' already exists. Remove it manually or choose a different name.")


def is_effectively_empty(path: Path) -> bool:
    for child in path.iterdir():
        if child.is_file() and child.name in PLACEHOLDER_FILES:
            continue
        return False
    return True


def ensure_safe_prefix(repo_root: Path, requested_prefix: str) -> str:
    cleaned = requested_prefix.strip()
    if not cleaned:
        raise HarvestError("Target path (--path) must be provided.")

    path_obj = Path(cleaned)
    if path_obj.is_absolute():
        raise HarvestError("Target path must be relative to the repo root.")

    resolved = (repo_root / path_obj).resolve()
    try:
        relative = resolved.relative_to(repo_root)
    except ValueError as exc:
        raise HarvestError("Target path escapes the repository root. Refusing to continue.") from exc

    if resolved.exists():
        if not resolved.is_dir():
            raise HarvestError(f"Target path '{relative}' already exists and is not a directory.")
        if not is_effectively_empty(resolved):
            raise HarvestError(f"Target directory '{relative}' is not empty. Choose an empty/non-existent path.")

    return relative.as_posix()


def add_remote(repo_root: Path, url: str) -> None:
    print(f"Adding temporary remote '{REMOTE_NAME}' for {url}...")
    run_git(["remote", "add", "-f", REMOTE_NAME, url], repo_root, capture_output=False)


def remove_remote(repo_root: Path) -> None:
    print(f"Removing temporary remote '{REMOTE_NAME}'...")
    run_git(["remote", "remove", REMOTE_NAME], repo_root, capture_output=False)


def run_subtree_add(repo_root: Path, prefix: str, branch: str, commit_message: str) -> None:
    print(f"Running git subtree add into '{prefix}' from {REMOTE_NAME}/{branch}...")
    run_git(
        ["subtree", "add", "--prefix", prefix, REMOTE_NAME, branch, "--squash", "--message", commit_message],
        repo_root,
        capture_output=False,
    )


def commit_if_needed(repo_root: Path, prefix: str, commit_message: str) -> bool:
    status = run_git(["status", "--porcelain"], repo_root)
    if not status:
        print("No pending changes to commit; git subtree already created the merge commit.")
        return False

    print("Staging harvested files for commit...")
    run_git(["add", "--all", prefix], repo_root, capture_output=False)
    print(f"Committing harvested code with message: {commit_message}")
    run_git(["commit", "-m", commit_message], repo_root, capture_output=False)
    return True


def push_main(repo_root: Path) -> None:
    print("Pushing 'main' to origin...")
    run_git(["push", "origin", "main"], repo_root, capture_output=False)


def harvest(url: str, branch: str, target_path: str) -> None:
    repo_root = find_repo_root()
    ensure_clean_worktree(repo_root)
    ensure_on_main(repo_root)
    ensure_remote_slot_available(repo_root)
    prefix = ensure_safe_prefix(repo_root, target_path)
    commit_message = f"harvest: merged {url} into {prefix}"

    remote_added = False
    try:
        add_remote(repo_root, url)
        remote_added = True
        run_subtree_add(repo_root, prefix, branch, commit_message)
        
        # VERIFICATION STEP
        verify_harvest(repo_root, prefix)
        
    except Exception:
        # If verification or anything else fails, we might want to cleanup
        # But subtree add is already committed by default if we don't be careful
        # For now, we rely on 'verify_harvest' raising an error which stops the script
        # before the final push.
        raise
    finally:

        if remote_added:
            try:
                remove_remote(repo_root)
            except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
                raise HarvestError(f"Failed to remove temporary remote '{REMOTE_NAME}': {exc}") from exc

    commit_if_needed(repo_root, prefix, commit_message)
    push_main(repo_root)
    print("Harvest complete.")


def verify_harvest(repo_root: Path, prefix: str) -> None:
    """
    Enhanced verification with multiple quality checks.
    If validation fails, raises HarvestError to trigger a rollback/abort.
    """
    target_path = repo_root / prefix
    
    print(f"\n🔍 Verifying harvested code in '{prefix}'...")
    print("=" * 60)
    
    checks = {
        "tests_exist": False,
        "tests_pass": False,
        "has_readme": False,
        "has_dependencies": False,
        "no_obvious_secrets": True
    }
    
    # Check 1: Tests exist
    if (target_path / "tests").exists() or list(target_path.glob("test_*.py")):
        checks["tests_exist"] = True
        print("✅ Tests found")
        
        # Check 2: Tests pass
        print("🧪 Running tests...")
        try:
            result = subprocess.run(
                ["pytest", prefix, "-v", "--tb=short"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            checks["tests_pass"] = True
            print("✅ Tests passed")
        except subprocess.TimeoutExpired:
            print("⚠️  Tests timed out after 5 minutes")
        except subprocess.CalledProcessError as e:
            print("❌ Tests failed")
            if e.stdout:
                print(f"   Output: {e.stdout[-500:]}")  # Last 500 chars
        except FileNotFoundError:
            print("⚠️  pytest not available, skipping test execution")
    else:
        print("⚠️  No tests found")
    
    # Check 3: Documentation
    if (target_path / "README.md").exists():
        checks["has_readme"] = True
        print("✅ README.md found")
    else:
        print("⚠️  No README.md")
    
    # Check 4: Dependencies declared
    has_reqs = (target_path / "requirements.txt").exists()
    has_pkg = (target_path / "package.json").exists()
    if has_reqs or has_pkg:
        checks["has_dependencies"] = True
        dep_file = "requirements.txt" if has_reqs else "package.json"
        print(f"✅ Dependencies specified ({dep_file})")
    else:
        print("⚠️  No dependency file (requirements.txt, package.json)")
    
    # Check 5: No obvious secrets
    print("🔐 Scanning for hardcoded secrets...")
    secret_patterns = ["API_KEY", "SECRET_KEY", "PASSWORD", "TOKEN", "PRIVATE_KEY"]
    found_secrets = False
    
    for pattern in secret_patterns:
        try:
            result = subprocess.run(
                ["grep", "-r", "-i", pattern, str(prefix), 
                 "--exclude-dir=.git", "--exclude-dir=venv", 
                 "--exclude-dir=node_modules", "--exclude=*.pyc"],
                cwd=repo_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout:
                # Filter out comments and common false positives
                lines = result.stdout.split('\n')
                real_matches = [l for l in lines if l and '# nosec' not in l and 'example' not in l.lower()]
                if real_matches:
                    found_secrets = True
                    print(f"⚠️  Possible secret '{pattern}' found in code")
                    for match in real_matches[:2]:  # Show first 2 matches
                        print(f"     {match[:100]}")
        except Exception:
            pass
    
    if found_secrets:
        checks["no_obvious_secrets"] = False
    else:
        print("✅ No obvious secrets detected")
    
    # Calculate score
    score = sum(checks.values()) / len(checks) * 100
    
    print("=" * 60)
    print(f"📊 Verification Score: {score:.0f}%")
    print()
    print("Checks:")
    for check_name, passed in checks.items():
        symbol = "✅" if passed else "❌"
        display_name = check_name.replace('_', ' ').title()
        print(f"  {symbol} {display_name}")
    print("=" * 60)
    
    # Decision
    if not checks["tests_exist"]:
        raise HarvestError(
            f"CRITICAL: No tests found in '{prefix}'. "
            "All submissions must include tests. Harvest aborted."
        )
    
    if not checks["tests_pass"]:
        raise HarvestError(
            f"CRITICAL: Tests failed for '{prefix}'. "
            "Fix failing tests before resubmitting. Harvest aborted."
        )
    
    if score < 60:
        raise HarvestError(
            f"Verification failed (score: {score:.0f}%). "
            "Code needs significant improvement before acceptance."
        )
    elif score < 80:
        print(f"\n⚠️  WARNING: Score is acceptable ({score:.0f}%) but improvements recommended.")
        print("Consider adding:")
        if not checks["has_readme"]:
            print("  - README.md with documentation")
        if not checks["has_dependencies"]:
            print("  - Dependency specification file")
        if not checks["no_obvious_secrets"]:
            print("  - Move secrets to environment variables")
        print()
    else:
        print(f"\n✅ Excellent! High quality submission ({score:.0f}%)")
    
    print("Proceeding with harvest...\n")



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harvest external repos via git subtree.")
    parser.add_argument("--url", required=True, help="Git URL of the repository to harvest.")
    parser.add_argument("--branch", default="main", help="Branch to harvest from the remote repository.")
    parser.add_argument("--path", required=True, help="Target directory (relative to repo root) for the subtree.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        harvest(args.url, args.branch, args.path)
    except HarvestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(
            f"Command '{' '.join(exc.cmd)}' failed with exit code {exc.returncode}.",
            file=sys.stderr,
        )
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()

