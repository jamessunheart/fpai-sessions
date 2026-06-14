"""
Mini App API - Backend endpoints for the Telegram Mini App IDE.

Provides file operations, diff generation, and code execution
for the embedded Monaco editor.
"""

import os
import hashlib
import difflib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Constants
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/Users/jamessunheart/FPAI_Cockpit")
MAX_FILE_SIZE = 1024 * 1024  # 1MB max file size


router = APIRouter(prefix="/miniapp", tags=["miniapp"])


# ============================================================================
# Models
# ============================================================================

class FileNode(BaseModel):
    """Represents a file or directory in the file tree."""
    name: str
    path: str
    type: str  # "file" or "directory"
    children: Optional[List["FileNode"]] = None
    size: Optional[int] = None
    modified: Optional[str] = None


class FileContent(BaseModel):
    """File content with metadata."""
    path: str
    content: str
    language: str
    size: int
    modified: str
    hash: str


class FileEdit(BaseModel):
    """A proposed file edit."""
    path: str
    original_content: str
    new_content: str


class DiffResult(BaseModel):
    """Result of a diff operation."""
    path: str
    original_hash: str
    new_hash: str
    additions: int
    deletions: int
    diff_html: str
    diff_unified: str


class ApplyEditRequest(BaseModel):
    """Request to apply a file edit."""
    path: str
    new_content: str
    expected_hash: str  # For optimistic locking


class SearchResult(BaseModel):
    """A search result."""
    path: str
    line: int
    content: str
    match_start: int
    match_end: int


# ============================================================================
# File Tree Operations
# ============================================================================

def get_language_from_extension(filename: str) -> str:
    """Determine language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescriptreact",
        ".jsx": "javascriptreact",
        ".json": "json",
        ".md": "markdown",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sh": "shell",
        ".bash": "shell",
        ".sql": "sql",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".r": "r",
        ".R": "r",
        ".toml": "toml",
        ".ini": "ini",
        ".conf": "ini",
        ".xml": "xml",
        ".vue": "vue",
        ".svelte": "svelte",
    }
    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, "plaintext")


def build_file_tree(root_path: str, max_depth: int = 5, current_depth: int = 0) -> List[FileNode]:
    """Build a file tree structure from a directory."""
    if current_depth >= max_depth:
        return []
    
    nodes = []
    try:
        entries = sorted(os.listdir(root_path))
    except PermissionError:
        return []
    
    # Directories to skip
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache", "dist", "build"}
    
    for entry in entries:
        if entry.startswith(".") and entry not in [".env", ".env.example"]:
            continue
        
        full_path = os.path.join(root_path, entry)
        rel_path = os.path.relpath(full_path, WORKSPACE_ROOT)
        
        if os.path.isdir(full_path):
            if entry in skip_dirs:
                continue
            children = build_file_tree(full_path, max_depth, current_depth + 1)
            nodes.append(FileNode(
                name=entry,
                path=rel_path,
                type="directory",
                children=children
            ))
        else:
            try:
                stat = os.stat(full_path)
                nodes.append(FileNode(
                    name=entry,
                    path=rel_path,
                    type="file",
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                ))
            except OSError:
                continue
    
    return nodes


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/tree")
async def get_file_tree(
    path: str = Query(default="", description="Relative path from workspace root"),
    depth: int = Query(default=3, ge=1, le=10, description="Max depth to traverse")
) -> Dict[str, Any]:
    """Get the file tree for a directory."""
    full_path = os.path.join(WORKSPACE_ROOT, path) if path else WORKSPACE_ROOT
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    
    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
    
    tree = build_file_tree(full_path, max_depth=depth)
    
    return {
        "root": path or ".",
        "workspace": WORKSPACE_ROOT,
        "tree": [node.dict() for node in tree]
    }


@router.get("/file")
async def get_file_content(
    path: str = Query(..., description="Relative path to the file")
) -> FileContent:
    """Get the content of a file."""
    full_path = os.path.join(WORKSPACE_ROOT, path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    
    if os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail=f"Path is a directory: {path}")
    
    stat = os.stat(full_path)
    if stat.st_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large: {stat.st_size} bytes")
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file cannot be displayed")
    
    return FileContent(
        path=path,
        content=content,
        language=get_language_from_extension(path),
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        hash=hashlib.md5(content.encode()).hexdigest()
    )


@router.post("/diff")
async def generate_diff(edit: FileEdit) -> DiffResult:
    """Generate a diff between original and new content."""
    original_lines = edit.original_content.splitlines(keepends=True)
    new_lines = edit.new_content.splitlines(keepends=True)
    
    # Generate unified diff
    diff = list(difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{edit.path}",
        tofile=f"b/{edit.path}",
        lineterm=""
    ))
    
    # Count additions and deletions
    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    
    # Generate HTML diff
    differ = difflib.HtmlDiff()
    diff_html = differ.make_table(
        original_lines,
        new_lines,
        fromdesc="Original",
        todesc="Modified",
        context=True,
        numlines=3
    )
    
    return DiffResult(
        path=edit.path,
        original_hash=hashlib.md5(edit.original_content.encode()).hexdigest(),
        new_hash=hashlib.md5(edit.new_content.encode()).hexdigest(),
        additions=additions,
        deletions=deletions,
        diff_html=diff_html,
        diff_unified="\n".join(diff)
    )


@router.post("/apply")
async def apply_edit(request: ApplyEditRequest) -> Dict[str, Any]:
    """Apply a file edit with optimistic locking."""
    full_path = os.path.join(WORKSPACE_ROOT, request.path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.path}")
    
    # Read current content and verify hash
    with open(full_path, "r", encoding="utf-8") as f:
        current_content = f.read()
    
    current_hash = hashlib.md5(current_content.encode()).hexdigest()
    if current_hash != request.expected_hash:
        raise HTTPException(
            status_code=409,
            detail="File was modified since you loaded it. Please reload and try again."
        )
    
    # Create backup
    backup_dir = os.path.join(WORKSPACE_ROOT, ".aria-backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{Path(request.path).name}.{timestamp}.bak"
    backup_path = os.path.join(backup_dir, backup_name)
    
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(current_content)
    
    # Apply the edit
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(request.new_content)
    
    new_hash = hashlib.md5(request.new_content.encode()).hexdigest()
    
    return {
        "success": True,
        "path": request.path,
        "new_hash": new_hash,
        "backup_path": backup_path,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/search")
async def search_files(
    query: str = Query(..., min_length=2, description="Search query"),
    path: str = Query(default="", description="Directory to search in"),
    file_pattern: str = Query(default="*", description="File pattern (e.g., *.py)")
) -> List[SearchResult]:
    """Search for text in files."""
    import fnmatch
    
    search_root = os.path.join(WORKSPACE_ROOT, path) if path else WORKSPACE_ROOT
    results = []
    max_results = 100
    
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache"}
    
    for root, dirs, files in os.walk(search_root):
        # Skip hidden and excluded directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        
        for filename in files:
            if not fnmatch.fnmatch(filename, file_pattern):
                continue
            
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, WORKSPACE_ROOT)
            
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        idx = line.lower().find(query.lower())
                        if idx != -1:
                            results.append(SearchResult(
                                path=rel_path,
                                line=line_num,
                                content=line.strip()[:200],
                                match_start=idx,
                                match_end=idx + len(query)
                            ))
                            
                            if len(results) >= max_results:
                                return results
            except (UnicodeDecodeError, PermissionError):
                continue
    
    return results


@router.get("/recent")
async def get_recent_files(limit: int = Query(default=10, ge=1, le=50)) -> List[Dict[str, Any]]:
    """Get recently modified files."""
    files = []
    
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache", ".aria-backups"}
    
    for root, dirs, filenames in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        
        for filename in filenames:
            if filename.startswith("."):
                continue
            
            full_path = os.path.join(root, filename)
            try:
                stat = os.stat(full_path)
                files.append({
                    "path": os.path.relpath(full_path, WORKSPACE_ROOT),
                    "name": filename,
                    "modified": stat.st_mtime,
                    "size": stat.st_size
                })
            except OSError:
                continue
    
    # Sort by modification time, most recent first
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    # Format timestamps
    for f in files[:limit]:
        f["modified"] = datetime.fromtimestamp(f["modified"]).isoformat()
    
    return files[:limit]


