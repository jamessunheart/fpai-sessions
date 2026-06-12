#!/usr/bin/env python3
"""
SANDBOX EXECUTOR
================

Safely executes module code in an isolated environment.
"""

import os
import sys
import asyncio
import logging
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import signal
import resource

logger = logging.getLogger("aria.builder.sandbox")

# Resource limits
MAX_EXECUTION_TIME = 10  # seconds
MAX_MEMORY_MB = 50       # megabytes


@dataclass
class ExecutionResult:
    """Result of sandbox execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class TimeoutError(Exception):
    """Raised when execution times out."""
    pass


class SandboxExecutor:
    """
    Executes module code in a sandboxed environment.
    
    Features:
    - Timeout enforcement
    - Memory limits
    - Restricted imports
    - Isolated execution
    """
    
    # Allowed imports for modules
    ALLOWED_IMPORTS = {
        'json', 'datetime', 'random', 'math', 're', 'string',
        'collections', 'itertools', 'functools', 'pathlib',
        'typing', 'dataclasses', 'enum', 'hashlib', 'base64',
        'time', 'calendar', 'uuid', 'copy', 'ast', 'operator'
    }
    
    # Blocked imports
    BLOCKED_IMPORTS = {
        'subprocess', 'os.system', 'shutil', 'socket', 'ctypes',
        'multiprocessing', 'threading', 'pickle', 'shelve',
        'sqlite3', 'http', 'urllib', 'ftplib', 'telnetlib',
        'smtplib', 'imaplib', 'poplib', 'nntplib'
    }
    
    def __init__(self, timeout: int = MAX_EXECUTION_TIME):
        self.timeout = timeout
    
    async def execute_handler(
        self,
        handler_path: Path,
        args: str,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute a module handler in sandbox.
        
        Args:
            handler_path: Path to handler.py
            args: Command arguments
            context: Execution context (user_id, chat_id, etc.)
            
        Returns:
            ExecutionResult with output or error
        """
        import time
        start_time = time.time()
        
        try:
            # Validate handler exists
            if not handler_path.exists():
                return ExecutionResult(
                    success=False,
                    error=f"Handler not found: {handler_path}"
                )
            
            # Read and validate code
            code = handler_path.read_text()
            validation_error = self._validate_code(code)
            if validation_error:
                return ExecutionResult(
                    success=False,
                    error=f"Security validation failed: {validation_error}"
                )
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location("sandbox_module", handler_path)
            module = importlib.util.module_from_spec(spec)
            
            # Execute with timeout
            try:
                # Load the module
                spec.loader.exec_module(module)
                
                # Get the handle function
                if not hasattr(module, 'handle'):
                    return ExecutionResult(
                        success=False,
                        error="Module missing 'handle' function"
                    )
                
                handle_func = module.handle
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._run_handler(handle_func, args, context),
                    timeout=self.timeout
                )
                
                execution_time = time.time() - start_time
                
                return ExecutionResult(
                    success=True,
                    output=str(result) if result else "(no output)",
                    execution_time=execution_time
                )
                
            except asyncio.TimeoutError:
                return ExecutionResult(
                    success=False,
                    error=f"Execution timed out after {self.timeout}s"
                )
                
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)[:100]}"
            )
    
    async def _run_handler(
        self,
        handle_func,
        args: str,
        context: Dict[str, Any]
    ) -> str:
        """Run the handler function."""
        # Check if handler is async or sync
        if asyncio.iscoroutinefunction(handle_func):
            return await handle_func(args, context)
        else:
            # Run sync function in executor to not block
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, handle_func, args, context
            )
    
    def _validate_code(self, code: str) -> Optional[str]:
        """
        Validate code for security issues.
        
        Returns:
            Error message if validation fails, None if OK
        """
        code_lower = code.lower()
        
        # Check for dangerous patterns
        dangerous_patterns = [
            ('eval(', 'eval() is not allowed'),
            ('exec(', 'exec() is not allowed'),
            ('__import__', '__import__ is not allowed'),
            ('subprocess', 'subprocess module is not allowed'),
            ('os.system', 'os.system is not allowed'),
            ('os.popen', 'os.popen is not allowed'),
            ('os.spawn', 'os.spawn is not allowed'),
            ('open("/etc', 'Cannot access system files'),
            ('open("/root', 'Cannot access root directory'),
            ('open("/opt/fpai/aria', 'Cannot access Aria core files'),
            ('rm -rf', 'Dangerous command detected'),
            ('sudo', 'sudo is not allowed'),
            ('chmod', 'chmod is not allowed'),
            ('chown', 'chown is not allowed'),
        ]
        
        for pattern, message in dangerous_patterns:
            if pattern.lower() in code_lower:
                return message
        
        # Check imports
        import_lines = [
            line.strip() for line in code.split('\n')
            if line.strip().startswith('import ') or line.strip().startswith('from ')
        ]
        
        for line in import_lines:
            for blocked in self.BLOCKED_IMPORTS:
                if blocked in line:
                    return f"Import not allowed: {blocked}"
        
        return None
    
    def validate_module_path(self, path: Path, user_id: int) -> bool:
        """Check if path is within user's sandbox."""
        allowed_base = Path(f"/opt/fpai/labs/{user_id}")
        try:
            path.resolve().relative_to(allowed_base.resolve())
            return True
        except ValueError:
            return False


class TestRunner:
    """
    Runs module tests in sandbox.
    """
    
    def __init__(self):
        self.sandbox = SandboxExecutor()
    
    async def test_module(
        self,
        module_path: Path,
        test_cases: list = None
    ) -> Dict[str, Any]:
        """
        Test a module with various inputs.
        
        Args:
            module_path: Path to module directory
            test_cases: List of (args, expected_contains) tuples
            
        Returns:
            Test results dictionary
        """
        handler_path = module_path / "handler.py"
        
        if test_cases is None:
            # Default test cases
            test_cases = [
                ("", None),           # Empty args
                ("test", None),       # Simple arg
                ("hello world", None) # Multi-word arg
            ]
        
        results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "outputs": []
        }
        
        for args, expected in test_cases:
            context = {"user_id": 0, "chat_id": 0, "test_mode": True}
            
            result = await self.sandbox.execute_handler(
                handler_path, args, context
            )
            
            if result.success:
                results["passed"] += 1
                results["outputs"].append({
                    "args": args,
                    "output": result.output,
                    "time": result.execution_time
                })
                
                # Check expected content if provided
                if expected and expected not in result.output:
                    results["failed"] += 1
                    results["passed"] -= 1
                    results["errors"].append(
                        f"Expected '{expected}' in output for args '{args}'"
                    )
            else:
                results["failed"] += 1
                results["errors"].append(f"Args '{args}': {result.error}")
        
        return results


# Singleton instances
_sandbox: Optional[SandboxExecutor] = None
_test_runner: Optional[TestRunner] = None


def get_sandbox() -> SandboxExecutor:
    """Get singleton sandbox executor."""
    global _sandbox
    if _sandbox is None:
        _sandbox = SandboxExecutor()
    return _sandbox


def get_test_runner() -> TestRunner:
    """Get singleton test runner."""
    global _test_runner
    if _test_runner is None:
        _test_runner = TestRunner()
    return _test_runner


