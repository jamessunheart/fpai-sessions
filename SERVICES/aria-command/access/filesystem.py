#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - UNIVERSAL FILE SYSTEM
============================================

Read/write files across all repos and servers.

Locations:
- local: FPAI_Cockpit workspace
- primary: 198.54.123.234
- secondary: 162.0.208.88
- github: Remote repositories
"""

import os
import re
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncssh
import httpx

logger = logging.getLogger("aria.filesystem")

# ============================================================================
# CONFIGURATION
# ============================================================================

class Location(str, Enum):
    LOCAL = "local"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GITHUB = "github"

SERVERS = {
    Location.PRIMARY: {
        "host": "198.54.123.234",
        "user": "root",
        "base_path": "/opt/fpai"
    },
    Location.SECONDARY: {
        "host": "162.0.208.88",
        "user": "root",
        "base_path": "/opt/fpai"
    }
}

LOCAL_BASE = Path(os.getenv("FPAI_WORKSPACE", "/Users/jamessunheart/FPAI_Cockpit"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ORG = "fullpotential-ai"

# File patterns that are always blocked
BLOCKED_PATTERNS = [
    r"\.env$",           # Don't expose env files via read
    r"id_rsa",           # SSH keys
    r"\.pem$",           # Certificates
    r"password",         # Password files
    r"secret",           # Secret files
]

# Max file size to read (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


@dataclass
class FileResult:
    """Result of a file operation."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    path: str = ""
    location: str = ""
    size: int = 0
    truncated: bool = False


class UniversalFileSystem:
    """
    Access files anywhere in the system.
    
    Supports:
    - Local workspace files
    - Remote server files (via SSH)
    - GitHub repository files (via API)
    """
    
    def __init__(self):
        self.ssh_connections: Dict[Location, asyncssh.SSHClientConnection] = {}
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close all connections."""
        for conn in self.ssh_connections.values():
            conn.close()
        await self.http.aclose()
    
    def _is_blocked(self, path: str) -> bool:
        """Check if path matches blocked patterns."""
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False
    
    def _parse_path(self, path: str) -> Tuple[Location, str]:
        """
        Parse a path into location and relative path.
        
        Examples:
            "server.py" -> (LOCAL, "server.py")
            "primary:/opt/fpai/aria/server.py" -> (PRIMARY, "/opt/fpai/aria/server.py")
            "github:fpai-cockpit/main/README.md" -> (GITHUB, "fpai-cockpit/main/README.md")
        """
        if ":" in path and not path.startswith("/"):
            prefix, rest = path.split(":", 1)
            prefix = prefix.lower()
            
            if prefix == "primary":
                return Location.PRIMARY, rest
            elif prefix == "secondary":
                return Location.SECONDARY, rest
            elif prefix == "github":
                return Location.GITHUB, rest
        
        return Location.LOCAL, path
    
    async def _get_ssh_connection(self, location: Location) -> asyncssh.SSHClientConnection:
        """Get or create SSH connection to server."""
        if location not in self.ssh_connections:
            server = SERVERS[location]
            self.ssh_connections[location] = await asyncssh.connect(
                server["host"],
                username=server["user"],
                known_hosts=None
            )
        return self.ssh_connections[location]
    
    async def read(self, path: str, max_lines: Optional[int] = None) -> FileResult:
        """
        Read a file from anywhere.
        
        Args:
            path: File path (can include location prefix)
            max_lines: Optional limit on lines to return
        
        Returns:
            FileResult with content or error
        """
        location, rel_path = self._parse_path(path)
        
        # Security check
        if self._is_blocked(rel_path):
            return FileResult(
                success=False,
                error=f"Access to {rel_path} is blocked for security",
                path=path,
                location=location.value
            )
        
        try:
            if location == Location.LOCAL:
                return await self._read_local(rel_path, max_lines)
            elif location in [Location.PRIMARY, Location.SECONDARY]:
                return await self._read_ssh(location, rel_path, max_lines)
            elif location == Location.GITHUB:
                return await self._read_github(rel_path)
            else:
                return FileResult(success=False, error=f"Unknown location: {location}")
        except Exception as e:
            logger.error(f"Read error for {path}: {e}")
            return FileResult(
                success=False,
                error=str(e),
                path=path,
                location=location.value
            )
    
    async def _read_local(self, path: str, max_lines: Optional[int] = None) -> FileResult:
        """Read from local filesystem."""
        # Resolve path
        if path.startswith("/"):
            full_path = Path(path)
        else:
            full_path = LOCAL_BASE / path
        
        if not full_path.exists():
            return FileResult(success=False, error=f"File not found: {path}", path=path, location="local")
        
        if not full_path.is_file():
            return FileResult(success=False, error=f"Not a file: {path}", path=path, location="local")
        
        size = full_path.stat().st_size
        if size > MAX_FILE_SIZE:
            return FileResult(
                success=False,
                error=f"File too large: {size} bytes (max {MAX_FILE_SIZE})",
                path=path,
                location="local",
                size=size
            )
        
        content = full_path.read_text()
        truncated = False
        
        if max_lines:
            lines = content.split('\n')
            if len(lines) > max_lines:
                content = '\n'.join(lines[:max_lines])
                truncated = True
        
        return FileResult(
            success=True,
            content=content,
            path=str(full_path),
            location="local",
            size=size,
            truncated=truncated
        )
    
    async def _read_ssh(self, location: Location, path: str, max_lines: Optional[int] = None) -> FileResult:
        """Read from remote server via SSH."""
        conn = await self._get_ssh_connection(location)
        server = SERVERS[location]
        
        # If relative path, prepend base
        if not path.startswith("/"):
            path = f"{server['base_path']}/{path}"
        
        # Check if exists and get size
        result = await conn.run(f"stat -c %s '{path}' 2>/dev/null || echo 'NOT_FOUND'")
        output = result.stdout.strip()
        
        if output == "NOT_FOUND":
            return FileResult(success=False, error=f"File not found: {path}", location=location.value)
        
        size = int(output)
        if size > MAX_FILE_SIZE:
            return FileResult(
                success=False,
                error=f"File too large: {size} bytes",
                location=location.value,
                size=size
            )
        
        # Read file
        if max_lines:
            result = await conn.run(f"head -n {max_lines} '{path}'")
        else:
            result = await conn.run(f"cat '{path}'")
        
        return FileResult(
            success=True,
            content=result.stdout,
            path=path,
            location=location.value,
            size=size,
            truncated=bool(max_lines)
        )
    
    async def _read_github(self, path: str) -> FileResult:
        """Read from GitHub repository."""
        if not GITHUB_TOKEN:
            return FileResult(success=False, error="GitHub token not configured")
        
        # Parse: repo/branch/path
        parts = path.split("/", 2)
        if len(parts) < 3:
            return FileResult(success=False, error="GitHub path format: repo/branch/path")
        
        repo, branch, file_path = parts
        
        url = f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/contents/{file_path}?ref={branch}"
        
        response = await self.http.get(
            url,
            headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3.raw"
            }
        )
        
        if response.status_code == 404:
            return FileResult(success=False, error=f"File not found in GitHub: {path}")
        elif response.status_code != 200:
            return FileResult(success=False, error=f"GitHub error: {response.status_code}")
        
        return FileResult(
            success=True,
            content=response.text,
            path=path,
            location="github",
            size=len(response.text)
        )
    
    async def write(
        self,
        path: str,
        content: str,
        create_backup: bool = True
    ) -> FileResult:
        """
        Write to a file.
        
        Args:
            path: File path (can include location prefix)
            content: Content to write
            create_backup: Whether to backup existing file
        
        Returns:
            FileResult with success/error
        """
        location, rel_path = self._parse_path(path)
        
        # Security check
        if self._is_blocked(rel_path):
            return FileResult(
                success=False,
                error=f"Write to {rel_path} is blocked for security",
                path=path,
                location=location.value
            )
        
        try:
            if location == Location.LOCAL:
                return await self._write_local(rel_path, content, create_backup)
            elif location in [Location.PRIMARY, Location.SECONDARY]:
                return await self._write_ssh(location, rel_path, content, create_backup)
            else:
                return FileResult(success=False, error=f"Cannot write to {location}")
        except Exception as e:
            logger.error(f"Write error for {path}: {e}")
            return FileResult(success=False, error=str(e), path=path, location=location.value)
    
    async def _write_local(self, path: str, content: str, create_backup: bool) -> FileResult:
        """Write to local filesystem."""
        if path.startswith("/"):
            full_path = Path(path)
        else:
            full_path = LOCAL_BASE / path
        
        # Create backup
        if create_backup and full_path.exists():
            backup_path = full_path.with_suffix(full_path.suffix + ".bak")
            import shutil
            shutil.copy2(full_path, backup_path)
        
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write
        full_path.write_text(content)
        
        return FileResult(
            success=True,
            path=str(full_path),
            location="local",
            size=len(content)
        )
    
    async def _write_ssh(
        self,
        location: Location,
        path: str,
        content: str,
        create_backup: bool
    ) -> FileResult:
        """Write to remote server via SSH."""
        conn = await self._get_ssh_connection(location)
        server = SERVERS[location]
        
        if not path.startswith("/"):
            path = f"{server['base_path']}/{path}"
        
        # Create backup
        if create_backup:
            await conn.run(f"cp '{path}' '{path}.bak' 2>/dev/null || true")
        
        # Write via heredoc
        # Escape content for shell
        escaped = content.replace("'", "'\"'\"'")
        result = await conn.run(f"cat > '{path}' << 'ARIA_EOF'\n{content}\nARIA_EOF")
        
        if result.returncode != 0:
            return FileResult(success=False, error=f"Write failed: {result.stderr}")
        
        return FileResult(
            success=True,
            path=path,
            location=location.value,
            size=len(content)
        )
    
    async def search(
        self,
        pattern: str,
        location: Optional[Location] = None,
        file_pattern: str = "*.py",
        max_results: int = 50
    ) -> List[Dict]:
        """
        Search for pattern across files.
        
        Args:
            pattern: Regex pattern to search for
            location: Optional location to search (None = all)
            file_pattern: File glob pattern
            max_results: Maximum results to return
        
        Returns:
            List of matches with file, line, content
        """
        results = []
        locations = [location] if location else [Location.LOCAL, Location.PRIMARY, Location.SECONDARY]
        
        for loc in locations:
            try:
                if loc == Location.LOCAL:
                    matches = await self._search_local(pattern, file_pattern, max_results)
                else:
                    matches = await self._search_ssh(loc, pattern, file_pattern, max_results)
                
                for m in matches:
                    m["location"] = loc.value
                results.extend(matches)
                
                if len(results) >= max_results:
                    break
            except Exception as e:
                logger.warning(f"Search error in {loc}: {e}")
        
        return results[:max_results]
    
    async def _search_local(self, pattern: str, file_pattern: str, max_results: int) -> List[Dict]:
        """Search local files."""
        import subprocess
        
        cmd = f"grep -rn --include='{file_pattern}' -E '{pattern}' {LOCAL_BASE} 2>/dev/null | head -n {max_results}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        matches = []
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    matches.append({
                        "file": parts[0],
                        "line": int(parts[1]),
                        "content": parts[2][:200]
                    })
        
        return matches
    
    async def _search_ssh(self, location: Location, pattern: str, file_pattern: str, max_results: int) -> List[Dict]:
        """Search remote files via SSH."""
        conn = await self._get_ssh_connection(location)
        server = SERVERS[location]
        
        cmd = f"grep -rn --include='{file_pattern}' -E '{pattern}' {server['base_path']} 2>/dev/null | head -n {max_results}"
        result = await conn.run(cmd)
        
        matches = []
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    matches.append({
                        "file": parts[0],
                        "line": int(parts[1]),
                        "content": parts[2][:200]
                    })
        
        return matches
    
    async def list_dir(self, path: str) -> List[Dict]:
        """List directory contents."""
        location, rel_path = self._parse_path(path)
        
        try:
            if location == Location.LOCAL:
                return await self._list_local(rel_path)
            else:
                return await self._list_ssh(location, rel_path)
        except Exception as e:
            logger.error(f"List error for {path}: {e}")
            return []
    
    async def _list_local(self, path: str) -> List[Dict]:
        """List local directory."""
        if path.startswith("/"):
            dir_path = Path(path)
        else:
            dir_path = LOCAL_BASE / path
        
        if not dir_path.exists():
            return []
        
        items = []
        for item in sorted(dir_path.iterdir()):
            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0
            })
        
        return items
    
    async def _list_ssh(self, location: Location, path: str) -> List[Dict]:
        """List remote directory."""
        conn = await self._get_ssh_connection(location)
        server = SERVERS[location]
        
        if not path.startswith("/"):
            path = f"{server['base_path']}/{path}"
        
        result = await conn.run(f"ls -la '{path}' 2>/dev/null")
        
        items = []
        for line in result.stdout.strip().split('\n')[1:]:  # Skip total line
            parts = line.split()
            if len(parts) >= 9:
                name = parts[-1]
                is_dir = parts[0].startswith('d')
                size = int(parts[4]) if not is_dir else 0
                items.append({
                    "name": name,
                    "type": "dir" if is_dir else "file",
                    "size": size
                })
        
        return items


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_fs: Optional[UniversalFileSystem] = None


def get_filesystem() -> UniversalFileSystem:
    """Get or create global filesystem instance."""
    global _fs
    if _fs is None:
        _fs = UniversalFileSystem()
    return _fs


async def read_file(path: str, max_lines: Optional[int] = None) -> FileResult:
    """Read a file from anywhere."""
    fs = get_filesystem()
    return await fs.read(path, max_lines)


async def write_file(path: str, content: str) -> FileResult:
    """Write to a file."""
    fs = get_filesystem()
    return await fs.write(path, content)


async def search_code(pattern: str, file_pattern: str = "*.py") -> List[Dict]:
    """Search for code pattern."""
    fs = get_filesystem()
    return await fs.search(pattern, file_pattern=file_pattern)


