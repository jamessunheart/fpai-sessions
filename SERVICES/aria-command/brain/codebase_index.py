#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - CODEBASE INDEX
=====================================

Index and search the entire codebase for context.
Like Cursor's codebase awareness.
"""

import os
import re
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

logger = logging.getLogger("aria.codebase")

# ============================================================================
# CONFIGURATION
# ============================================================================

# File patterns to index
INCLUDE_PATTERNS = [
    "*.py", "*.js", "*.ts", "*.tsx", "*.jsx",
    "*.md", "*.json", "*.yaml", "*.yml",
    "*.sh", "*.bash", "*.html", "*.css",
    "*.sql", "*.env.example"
]

# Directories to skip
EXCLUDE_DIRS = [
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    "dist", "build", ".next", ".cache", "coverage",
    ".pytest_cache", ".mypy_cache", "eggs", "*.egg-info"
]

# Max file size to index (500KB)
MAX_FILE_SIZE = 500 * 1024

# Index storage
INDEX_DIR = Path(os.getenv("ARIA_STATE_DIR", "/tmp/aria-command")) / "codebase_index"


@dataclass
class IndexedFile:
    """An indexed file in the codebase."""
    path: str
    relative_path: str
    content: str
    size: int
    modified: datetime
    hash: str
    language: str
    summary: str = ""
    
    # Extracted metadata
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "relative_path": self.relative_path,
            "size": self.size,
            "modified": self.modified.isoformat(),
            "hash": self.hash,
            "language": self.language,
            "summary": self.summary,
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports
        }


@dataclass
class SearchResult:
    """A search result from the codebase."""
    file: IndexedFile
    score: float
    matches: List[Dict] = field(default_factory=list)
    snippet: str = ""


class CodebaseIndex:
    """
    Full codebase indexer and searcher.
    
    Features:
    - Index all code files
    - Extract functions, classes, imports
    - Semantic search (when embeddings available)
    - Keyword search
    - Smart context building
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.getenv("FPAI_WORKSPACE", "/opt/fpai"))
        self.files: Dict[str, IndexedFile] = {}
        self.last_indexed: Optional[datetime] = None
        
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing index
        self._load_index()
    
    def _should_include(self, path: Path) -> bool:
        """Check if file should be indexed."""
        # Check exclusions
        for part in path.parts:
            for exclude in EXCLUDE_DIRS:
                if part == exclude or (exclude.startswith("*") and part.endswith(exclude[1:])):
                    return False
        
        # Check inclusions
        name = path.name
        for pattern in INCLUDE_PATTERNS:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        
        return False
    
    def _detect_language(self, path: Path) -> str:
        """Detect file language from extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".sh": "bash",
            ".bash": "bash",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
        }
        return ext_map.get(path.suffix.lower(), "text")
    
    def _extract_python_metadata(self, content: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract functions, classes, imports from Python code."""
        functions = re.findall(r'^(?:async\s+)?def\s+(\w+)\s*\(', content, re.MULTILINE)
        classes = re.findall(r'^class\s+(\w+)\s*[:\(]', content, re.MULTILINE)
        imports = re.findall(r'^(?:from\s+[\w.]+\s+)?import\s+([\w,\s]+)', content, re.MULTILINE)
        imports = [i.strip() for imp in imports for i in imp.split(',')]
        return functions, classes, imports
    
    def _extract_js_metadata(self, content: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract functions, classes, imports from JS/TS code."""
        functions = re.findall(r'(?:async\s+)?function\s+(\w+)\s*\(', content)
        functions += re.findall(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', content)
        functions += re.findall(r'(\w+)\s*:\s*(?:async\s+)?(?:function|\()', content)
        classes = re.findall(r'class\s+(\w+)\s*(?:extends|implements|{)', content)
        imports = re.findall(r"import\s+(?:{[^}]+}|\w+)\s+from\s+['\"]([^'\"]+)['\"]", content)
        return list(set(functions)), classes, imports
    
    def _generate_summary(self, file: IndexedFile) -> str:
        """Generate a brief summary of the file."""
        parts = []
        
        if file.classes:
            parts.append(f"Classes: {', '.join(file.classes[:5])}")
        if file.functions:
            parts.append(f"Functions: {', '.join(file.functions[:10])}")
        if file.imports:
            parts.append(f"Imports: {len(file.imports)} modules")
        
        # First docstring or comment
        if file.language == "python":
            doc_match = re.search(r'^"""(.+?)"""', file.content, re.DOTALL)
            if doc_match:
                doc = doc_match.group(1).strip()[:200]
                parts.insert(0, doc)
        
        return " | ".join(parts) if parts else f"{file.language} file, {file.size} bytes"
    
    async def index_file(self, path: Path) -> Optional[IndexedFile]:
        """Index a single file."""
        try:
            if not path.is_file():
                return None
            
            if path.stat().st_size > MAX_FILE_SIZE:
                logger.debug(f"Skipping large file: {path}")
                return None
            
            content = path.read_text(errors='ignore')
            file_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Check if unchanged
            relative_path = str(path.relative_to(self.base_path))
            if relative_path in self.files:
                if self.files[relative_path].hash == file_hash:
                    return self.files[relative_path]
            
            language = self._detect_language(path)
            
            # Extract metadata
            if language == "python":
                functions, classes, imports = self._extract_python_metadata(content)
            elif language in ["javascript", "typescript"]:
                functions, classes, imports = self._extract_js_metadata(content)
            else:
                functions, classes, imports = [], [], []
            
            indexed = IndexedFile(
                path=str(path),
                relative_path=relative_path,
                content=content,
                size=len(content),
                modified=datetime.fromtimestamp(path.stat().st_mtime),
                hash=file_hash,
                language=language,
                functions=functions,
                classes=classes,
                imports=imports
            )
            
            indexed.summary = self._generate_summary(indexed)
            
            return indexed
            
        except Exception as e:
            logger.debug(f"Failed to index {path}: {e}")
            return None
    
    async def index_directory(self, path: Path = None) -> int:
        """Index all files in a directory."""
        path = path or self.base_path
        count = 0
        
        logger.info(f"Indexing codebase at {path}...")
        
        for root, dirs, files in os.walk(path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for filename in files:
                file_path = Path(root) / filename
                
                if self._should_include(file_path):
                    indexed = await self.index_file(file_path)
                    if indexed:
                        self.files[indexed.relative_path] = indexed
                        count += 1
        
        self.last_indexed = datetime.now()
        self._save_index()
        
        logger.info(f"Indexed {count} files")
        return count
    
    async def refresh_index(self):
        """Refresh the index (only changed files)."""
        return await self.index_directory()
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        file_pattern: str = None
    ) -> List[SearchResult]:
        """
        Search the codebase.
        
        Args:
            query: Search query (regex supported)
            max_results: Maximum results to return
            file_pattern: Optional file pattern filter
        
        Returns:
            List of SearchResult
        """
        results = []
        
        # Compile query as regex
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            # Fall back to literal search
            pattern = re.compile(re.escape(query), re.IGNORECASE)
        
        for path, file in self.files.items():
            # Filter by pattern
            if file_pattern:
                if not re.search(file_pattern, path, re.IGNORECASE):
                    continue
            
            # Search in content
            matches = list(pattern.finditer(file.content))
            
            if matches:
                # Calculate score (more matches = higher score)
                score = len(matches)
                
                # Bonus for matches in function/class names
                for func in file.functions:
                    if pattern.search(func):
                        score += 5
                for cls in file.classes:
                    if pattern.search(cls):
                        score += 5
                
                # Build snippets
                snippets = []
                for match in matches[:3]:
                    start = max(0, match.start() - 50)
                    end = min(len(file.content), match.end() + 50)
                    snippet = file.content[start:end].strip()
                    snippets.append({
                        "match": match.group(),
                        "context": snippet,
                        "position": match.start()
                    })
                
                results.append(SearchResult(
                    file=file,
                    score=score,
                    matches=snippets,
                    snippet=snippets[0]["context"] if snippets else ""
                ))
        
        # Sort by score
        results.sort(key=lambda r: -r.score)
        
        return results[:max_results]
    
    def find_file(self, name: str) -> Optional[IndexedFile]:
        """Find a file by name."""
        for path, file in self.files.items():
            if name in path or path.endswith(name):
                return file
        return None
    
    def get_file(self, path: str) -> Optional[IndexedFile]:
        """Get a specific indexed file."""
        return self.files.get(path)
    
    def get_files_by_language(self, language: str) -> List[IndexedFile]:
        """Get all files of a specific language."""
        return [f for f in self.files.values() if f.language == language]
    
    def build_context(
        self,
        query: str,
        max_tokens: int = 50000,
        include_related: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Build context for an LLM query.
        
        Args:
            query: The user's query
            max_tokens: Maximum tokens for context
            include_related: Include related files
        
        Returns:
            (context_string, list_of_file_paths)
        """
        # Search for relevant files
        results = self.search(query, max_results=20)
        
        context_parts = []
        included_files = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough token estimate
        
        for result in results:
            file = result.file
            
            # Check if we have room
            if total_chars + file.size > max_chars:
                # Try to include just relevant snippets
                for match in result.matches:
                    snippet = f"# From {file.relative_path}:\n{match['context']}"
                    if total_chars + len(snippet) < max_chars:
                        context_parts.append(snippet)
                        total_chars += len(snippet)
                continue
            
            # Include full file
            header = f"# File: {file.relative_path}\n# {file.summary}\n"
            content = f"{header}\n{file.content}\n"
            
            context_parts.append(content)
            included_files.append(file.relative_path)
            total_chars += len(content)
        
        return "\n---\n".join(context_parts), included_files
    
    def get_structure(self) -> Dict:
        """Get codebase structure overview."""
        structure = {
            "total_files": len(self.files),
            "by_language": {},
            "by_directory": {},
            "last_indexed": self.last_indexed.isoformat() if self.last_indexed else None
        }
        
        for path, file in self.files.items():
            # Count by language
            lang = file.language
            if lang not in structure["by_language"]:
                structure["by_language"][lang] = {"count": 0, "total_size": 0}
            structure["by_language"][lang]["count"] += 1
            structure["by_language"][lang]["total_size"] += file.size
            
            # Count by directory
            dir_path = str(Path(path).parent)
            if dir_path not in structure["by_directory"]:
                structure["by_directory"][dir_path] = 0
            structure["by_directory"][dir_path] += 1
        
        return structure
    
    def _save_index(self):
        """Save index to disk."""
        index_file = INDEX_DIR / "index.json"
        
        data = {
            "last_indexed": self.last_indexed.isoformat() if self.last_indexed else None,
            "files": {path: f.to_dict() for path, f in self.files.items()}
        }
        
        # Save metadata only (not content)
        index_file.write_text(json.dumps(data, indent=2))
    
    def _load_index(self):
        """Load index from disk."""
        index_file = INDEX_DIR / "index.json"
        
        if not index_file.exists():
            return
        
        try:
            data = json.loads(index_file.read_text())
            self.last_indexed = datetime.fromisoformat(data["last_indexed"]) if data.get("last_indexed") else None
            
            # We only load metadata, content is loaded on demand
            logger.info(f"Loaded index metadata for {len(data.get('files', {}))} files")
            
        except Exception as e:
            logger.warning(f"Failed to load index: {e}")


# ============================================================================
# CONVENIENCE
# ============================================================================

_index: Optional[CodebaseIndex] = None


def get_index(base_path: str = None) -> CodebaseIndex:
    """Get global codebase index."""
    global _index
    if _index is None:
        _index = CodebaseIndex(base_path)
    return _index


async def search_codebase(query: str, max_results: int = 10) -> List[SearchResult]:
    """Search the codebase."""
    index = get_index()
    return index.search(query, max_results)


async def build_context_for_query(query: str, max_tokens: int = 50000) -> Tuple[str, List[str]]:
    """Build context for an LLM query."""
    index = get_index()
    return index.build_context(query, max_tokens)


async def ensure_indexed(base_path: str = None) -> int:
    """Ensure codebase is indexed."""
    index = get_index(base_path)
    
    # Re-index if never indexed or stale (> 1 hour)
    if not index.last_indexed or (datetime.now() - index.last_indexed).seconds > 3600:
        return await index.index_directory()
    
    return len(index.files)


