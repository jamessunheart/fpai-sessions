"""
Access layer - Universal file system, terminal, and git operations.
"""

from .filesystem import (
    UniversalFileSystem,
    get_filesystem,
    read_file,
    write_file,
    search_code,
    FileResult,
    Location
)

from .terminal import (
    TerminalExecutor,
    get_executor,
    run_command,
    run_on_all,
    classify_command,
    CommandResult,
    SafetyLevel,
    Server
)

from .git_ops import (
    GitOperations,
    get_git,
    git_status,
    git_commit,
    git_push,
    git_branch,
    create_pr,
    GitResult
)

__all__ = [
    "UniversalFileSystem",
    "get_filesystem",
    "read_file",
    "write_file",
    "search_code",
    "FileResult",
    "Location",
    "TerminalExecutor",
    "get_executor",
    "run_command",
    "run_on_all",
    "classify_command",
    "CommandResult",
    "SafetyLevel",
    "Server",
    "GitOperations",
    "get_git",
    "git_status",
    "git_commit",
    "git_push",
    "git_branch",
    "create_pr",
    "GitResult"
]


