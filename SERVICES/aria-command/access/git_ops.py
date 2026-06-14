#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - GIT OPERATIONS
=====================================

Git operations for branch management, commits, pushes, and PRs.
"""

import os
import re
import asyncio
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess
import httpx

logger = logging.getLogger("aria.git")

# ============================================================================
# CONFIGURATION
# ============================================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ORG = os.getenv("GITHUB_ORG", "fullpotential-ai")
DEFAULT_REPO_PATH = Path(os.getenv("FPAI_WORKSPACE", "/Users/jamessunheart/FPAI_Cockpit"))


@dataclass
class GitResult:
    """Result of a git operation."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    operation: str = ""


@dataclass
class BranchInfo:
    """Information about a branch."""
    name: str
    is_current: bool
    last_commit: str
    author: str
    date: str


@dataclass
class CommitInfo:
    """Information about a commit."""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    files_changed: int = 0


class GitOperations:
    """
    Git operations with safety controls.
    
    Features:
    - Local repository operations
    - GitHub API integration
    - PR creation
    - Safe branching workflow
    """
    
    def __init__(self, repo_path: Path = DEFAULT_REPO_PATH):
        self.repo_path = repo_path
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run git command in repo directory."""
        cmd = ["git", *args]
        return subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=check
        )
    
    # ========== STATUS & INFO ==========
    
    async def status(self) -> GitResult:
        """Get repository status."""
        try:
            result = self._run_git("status", "--porcelain")
            
            if not result.stdout.strip():
                return GitResult(
                    success=True,
                    output="Working tree clean",
                    operation="status"
                )
            
            # Parse status
            lines = result.stdout.strip().split('\n')
            modified = [l[3:] for l in lines if l.startswith(' M')]
            added = [l[3:] for l in lines if l.startswith('A ')]
            untracked = [l[3:] for l in lines if l.startswith('??')]
            deleted = [l[3:] for l in lines if l.startswith(' D')]
            
            status_msg = []
            if modified:
                status_msg.append(f"Modified: {', '.join(modified[:5])}")
            if added:
                status_msg.append(f"Added: {', '.join(added[:5])}")
            if deleted:
                status_msg.append(f"Deleted: {', '.join(deleted[:5])}")
            if untracked:
                status_msg.append(f"Untracked: {', '.join(untracked[:5])}")
            
            return GitResult(
                success=True,
                output='\n'.join(status_msg),
                operation="status"
            )
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="status")
    
    async def diff(self, file: Optional[str] = None, staged: bool = False) -> GitResult:
        """Get diff of changes."""
        try:
            args = ["diff"]
            if staged:
                args.append("--staged")
            if file:
                args.append(file)
            
            result = self._run_git(*args)
            
            if not result.stdout.strip():
                return GitResult(
                    success=True,
                    output="No changes",
                    operation="diff"
                )
            
            # Truncate if too long
            output = result.stdout
            if len(output) > 5000:
                output = output[:5000] + "\n... (truncated)"
            
            return GitResult(success=True, output=output, operation="diff")
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="diff")
    
    async def log(self, count: int = 10, oneline: bool = True) -> GitResult:
        """Get commit log."""
        try:
            args = ["log", f"-{count}"]
            if oneline:
                args.append("--oneline")
            else:
                args.append("--format=%h|%s|%an|%ar")
            
            result = self._run_git(*args)
            return GitResult(success=True, output=result.stdout, operation="log")
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="log")
    
    async def get_branches(self) -> List[BranchInfo]:
        """Get all branches."""
        try:
            result = self._run_git("branch", "-a", "--format=%(refname:short)|%(objectname:short)|%(authorname)|%(committerdate:relative)")
            
            branches = []
            current_result = self._run_git("branch", "--show-current")
            current = current_result.stdout.strip()
            
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    branches.append(BranchInfo(
                        name=parts[0],
                        is_current=parts[0] == current,
                        last_commit=parts[1] if len(parts) > 1 else "",
                        author=parts[2] if len(parts) > 2 else "",
                        date=parts[3] if len(parts) > 3 else ""
                    ))
            
            return branches
        except:
            return []
    
    # ========== BRANCH OPERATIONS ==========
    
    async def branch(self, name: str, from_branch: Optional[str] = None) -> GitResult:
        """Create a new branch."""
        try:
            args = ["checkout", "-b", name]
            if from_branch:
                args.append(from_branch)
            
            result = self._run_git(*args)
            return GitResult(
                success=True,
                output=f"Created and switched to branch '{name}'",
                operation="branch"
            )
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="branch")
    
    async def checkout(self, branch: str) -> GitResult:
        """Switch to a branch."""
        try:
            result = self._run_git("checkout", branch)
            return GitResult(
                success=True,
                output=f"Switched to branch '{branch}'",
                operation="checkout"
            )
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="checkout")
    
    async def delete_branch(self, name: str, force: bool = False) -> GitResult:
        """Delete a branch."""
        try:
            flag = "-D" if force else "-d"
            result = self._run_git("branch", flag, name)
            return GitResult(
                success=True,
                output=f"Deleted branch '{name}'",
                operation="delete_branch"
            )
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="delete_branch")
    
    # ========== COMMIT OPERATIONS ==========
    
    async def add(self, files: List[str] = None) -> GitResult:
        """Stage files for commit."""
        try:
            if files:
                for f in files:
                    self._run_git("add", f)
                output = f"Staged: {', '.join(files)}"
            else:
                self._run_git("add", "-A")
                output = "Staged all changes"
            
            return GitResult(success=True, output=output, operation="add")
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="add")
    
    async def commit(self, message: str, add_all: bool = False) -> GitResult:
        """Create a commit."""
        try:
            if add_all:
                await self.add()
            
            result = self._run_git("commit", "-m", message)
            
            # Extract commit hash
            hash_match = re.search(r'\[[\w-]+\s+([a-f0-9]+)\]', result.stdout)
            commit_hash = hash_match.group(1) if hash_match else "unknown"
            
            return GitResult(
                success=True,
                output=f"Committed: {commit_hash} - {message}",
                operation="commit"
            )
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in e.stdout:
                return GitResult(
                    success=True,
                    output="Nothing to commit",
                    operation="commit"
                )
            return GitResult(success=False, error=e.stderr, operation="commit")
    
    async def push(self, branch: Optional[str] = None, set_upstream: bool = False) -> GitResult:
        """Push to remote."""
        try:
            args = ["push"]
            if set_upstream:
                args.extend(["-u", "origin"])
                if branch:
                    args.append(branch)
            elif branch:
                args.extend(["origin", branch])
            
            result = self._run_git(*args)
            return GitResult(
                success=True,
                output=f"Pushed successfully",
                operation="push"
            )
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="push")
    
    async def pull(self, branch: Optional[str] = None) -> GitResult:
        """Pull from remote."""
        try:
            args = ["pull"]
            if branch:
                args.extend(["origin", branch])
            
            result = self._run_git(*args)
            return GitResult(
                success=True,
                output=result.stdout or "Already up to date",
                operation="pull"
            )
        except subprocess.CalledProcessError as e:
            return GitResult(success=False, error=e.stderr, operation="pull")
    
    # ========== GITHUB API OPERATIONS ==========
    
    async def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False,
        repo: Optional[str] = None
    ) -> GitResult:
        """Create a pull request on GitHub."""
        if not GITHUB_TOKEN:
            return GitResult(
                success=False,
                error="GitHub token not configured",
                operation="create_pr"
            )
        
        repo = repo or self.repo_path.name
        
        try:
            response = await self.http.post(
                f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/pulls",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                    "draft": draft
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                return GitResult(
                    success=True,
                    output=f"PR created: {data['html_url']}",
                    operation="create_pr"
                )
            else:
                return GitResult(
                    success=False,
                    error=f"GitHub API error: {response.status_code} - {response.text}",
                    operation="create_pr"
                )
        except Exception as e:
            return GitResult(success=False, error=str(e), operation="create_pr")
    
    async def list_prs(self, state: str = "open", repo: Optional[str] = None) -> List[Dict]:
        """List pull requests."""
        if not GITHUB_TOKEN:
            return []
        
        repo = repo or self.repo_path.name
        
        try:
            response = await self.http.get(
                f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/pulls",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"state": state}
            )
            
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    async def merge_pr(self, pr_number: int, repo: Optional[str] = None) -> GitResult:
        """Merge a pull request."""
        if not GITHUB_TOKEN:
            return GitResult(
                success=False,
                error="GitHub token not configured",
                operation="merge_pr"
            )
        
        repo = repo or self.repo_path.name
        
        try:
            response = await self.http.put(
                f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/pulls/{pr_number}/merge",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"merge_method": "squash"}
            )
            
            if response.status_code == 200:
                return GitResult(
                    success=True,
                    output=f"PR #{pr_number} merged",
                    operation="merge_pr"
                )
            else:
                return GitResult(
                    success=False,
                    error=f"Merge failed: {response.text}",
                    operation="merge_pr"
                )
        except Exception as e:
            return GitResult(success=False, error=str(e), operation="merge_pr")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_git: Optional[GitOperations] = None


def get_git() -> GitOperations:
    """Get or create global git operations instance."""
    global _git
    if _git is None:
        _git = GitOperations()
    return _git


async def git_status() -> GitResult:
    """Get repository status."""
    return await get_git().status()


async def git_commit(message: str, add_all: bool = True) -> GitResult:
    """Create a commit."""
    return await get_git().commit(message, add_all)


async def git_push(branch: Optional[str] = None) -> GitResult:
    """Push to remote."""
    return await get_git().push(branch)


async def git_branch(name: str) -> GitResult:
    """Create a new branch."""
    return await get_git().branch(name)


async def create_pr(title: str, body: str, head: str, base: str = "main") -> GitResult:
    """Create a pull request."""
    return await get_git().create_pr(title, body, head, base)


