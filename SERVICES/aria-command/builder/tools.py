#!/usr/bin/env python3
"""
BUILDER TOOLS
=============

Tools for collaborative module building with apprentices.
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .templates import ModuleTemplates
from .sandbox import get_sandbox, get_test_runner

logger = logging.getLogger("aria.builder.tools")

# Base paths
LABS_DIR = Path(os.getenv("FPAI_LABS_DIR", "/opt/fpai/labs"))
SUBMISSIONS_DIR = Path(os.getenv("FPAI_SUBMISSIONS_DIR", "/opt/fpai/submissions"))
INSTALLED_DIR = Path(os.getenv("FPAI_MODULES_DIR", "/opt/fpai/aria/modules/installed"))


@dataclass
class BuilderResult:
    """Result from a builder tool."""
    success: bool
    message: str
    data: Optional[Dict] = None
    error: Optional[str] = None


def get_user_workspace(user_id: int) -> Path:
    """Get the workspace path for a user."""
    workspace = LABS_DIR / str(user_id) / "modules"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def scaffold_module(
    user_id: int,
    module_name: str,
    command: str,
    description: str,
    author: str = "Apprentice",
    initial_logic: str = None
) -> BuilderResult:
    """
    Create a new module scaffold in the user's workspace.
    
    Args:
        user_id: Telegram user ID
        module_name: Name for the module (e.g., "timer")
        command: Command trigger (e.g., "/timer")
        description: What the module does
        author: Who's building it
        initial_logic: Optional initial handler code
        
    Returns:
        BuilderResult with created files info
    """
    try:
        # Validate command format
        if not command.startswith("/"):
            command = "/" + command
        
        # Clean module name
        module_name = module_name.lower().replace(" ", "-").replace("/", "")
        if not module_name.endswith("-command"):
            module_name = f"{module_name}-command"
        
        # Create module directory
        workspace = get_user_workspace(user_id)
        module_path = workspace / module_name
        
        if module_path.exists():
            return BuilderResult(
                success=False,
                message=f"Module '{module_name}' already exists in your workspace",
                error="duplicate_module"
            )
        
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Generate files from templates
        templates = ModuleTemplates()
        
        # module.json
        module_json = templates.module_json(
            module_name=module_name,
            command=command,
            description=description,
            author=author
        )
        (module_path / "module.json").write_text(module_json)
        
        # handler.py
        handler_py = templates.handler_py(
            command=command,
            description=description,
            initial_logic=initial_logic
        )
        (module_path / "handler.py").write_text(handler_py)
        
        # README.md
        readme_md = templates.readme_md(
            module_name=module_name,
            command=command,
            description=description,
            author=author
        )
        (module_path / "README.md").write_text(readme_md)
        
        logger.info(f"Created module scaffold: {module_path}")
        
        return BuilderResult(
            success=True,
            message=f"Created module '{module_name}' at {module_path}",
            data={
                "module_name": module_name,
                "command": command,
                "path": str(module_path),
                "files": ["module.json", "handler.py", "README.md"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error scaffolding module: {e}")
        return BuilderResult(
            success=False,
            message=f"Failed to create module: {str(e)}",
            error=str(e)
        )


def update_module_code(
    user_id: int,
    module_name: str,
    new_code: str,
    file_name: str = "handler.py"
) -> BuilderResult:
    """
    Update the code in a module file.
    
    Args:
        user_id: Telegram user ID
        module_name: Name of the module
        new_code: New code content
        file_name: Which file to update (default: handler.py)
        
    Returns:
        BuilderResult with validation info
    """
    try:
        workspace = get_user_workspace(user_id)
        
        # Normalize module name
        if not module_name.endswith("-command"):
            module_name = f"{module_name}-command"
        
        module_path = workspace / module_name
        
        if not module_path.exists():
            return BuilderResult(
                success=False,
                message=f"Module '{module_name}' not found in your workspace",
                error="module_not_found"
            )
        
        file_path = module_path / file_name
        
        # Validate code security
        sandbox = get_sandbox()
        validation_error = sandbox._validate_code(new_code)
        
        if validation_error:
            return BuilderResult(
                success=False,
                message=f"Code validation failed: {validation_error}",
                error="validation_failed",
                data={"validation_error": validation_error}
            )
        
        # Write the new code
        file_path.write_text(new_code)
        
        logger.info(f"Updated {file_name} in {module_path}")
        
        return BuilderResult(
            success=True,
            message=f"Updated {file_name} successfully",
            data={
                "module_name": module_name,
                "file": file_name,
                "path": str(file_path),
                "size": len(new_code)
            }
        )
        
    except Exception as e:
        logger.error(f"Error updating module code: {e}")
        return BuilderResult(
            success=False,
            message=f"Failed to update code: {str(e)}",
            error=str(e)
        )


async def test_module(
    user_id: int,
    module_name: str,
    test_args: str = ""
) -> BuilderResult:
    """
    Test a module in sandbox mode.
    
    Args:
        user_id: Telegram user ID
        module_name: Name of the module
        test_args: Arguments to pass to the handler
        
    Returns:
        BuilderResult with test output
    """
    try:
        workspace = get_user_workspace(user_id)
        
        # Normalize module name
        if not module_name.endswith("-command"):
            module_name = f"{module_name}-command"
        
        module_path = workspace / module_name
        handler_path = module_path / "handler.py"
        
        if not handler_path.exists():
            return BuilderResult(
                success=False,
                message=f"Module '{module_name}' not found or missing handler.py",
                error="handler_not_found"
            )
        
        # Execute in sandbox
        sandbox = get_sandbox()
        context = {
            "user_id": user_id,
            "chat_id": user_id,
            "test_mode": True
        }
        
        result = await sandbox.execute_handler(handler_path, test_args, context)
        
        if result.success:
            return BuilderResult(
                success=True,
                message="Test executed successfully",
                data={
                    "output": result.output,
                    "execution_time": f"{result.execution_time:.3f}s",
                    "args": test_args
                }
            )
        else:
            return BuilderResult(
                success=False,
                message=f"Test failed: {result.error}",
                error=result.error,
                data={"args": test_args}
            )
            
    except Exception as e:
        logger.error(f"Error testing module: {e}")
        return BuilderResult(
            success=False,
            message=f"Test error: {str(e)}",
            error=str(e)
        )


def list_my_modules(user_id: int) -> BuilderResult:
    """
    List all modules in a user's workspace.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        BuilderResult with module list
    """
    try:
        workspace = get_user_workspace(user_id)
        modules = []
        
        for module_dir in workspace.iterdir():
            if module_dir.is_dir():
                module_json_path = module_dir / "module.json"
                
                if module_json_path.exists():
                    try:
                        module_info = json.loads(module_json_path.read_text())
                        
                        # Check submission status
                        submission_path = SUBMISSIONS_DIR / module_dir.name
                        installed_path = INSTALLED_DIR / module_dir.name
                        
                        if installed_path.exists():
                            status = "live"
                        elif submission_path.exists():
                            status = "submitted"
                        else:
                            status = "draft"
                        
                        modules.append({
                            "name": module_info.get("name", module_dir.name),
                            "command": module_info.get("command", ""),
                            "description": module_info.get("description", ""),
                            "status": status,
                            "path": str(module_dir)
                        })
                    except:
                        modules.append({
                            "name": module_dir.name,
                            "status": "invalid",
                            "path": str(module_dir)
                        })
        
        return BuilderResult(
            success=True,
            message=f"Found {len(modules)} module(s)",
            data={"modules": modules}
        )
        
    except Exception as e:
        logger.error(f"Error listing modules: {e}")
        return BuilderResult(
            success=False,
            message=f"Failed to list modules: {str(e)}",
            error=str(e)
        )


def submit_module(user_id: int, module_name: str) -> BuilderResult:
    """
    Submit a module for steward review.
    
    Args:
        user_id: Telegram user ID
        module_name: Name of the module to submit
        
    Returns:
        BuilderResult with submission info
    """
    try:
        workspace = get_user_workspace(user_id)
        
        # Normalize module name
        if not module_name.endswith("-command"):
            module_name = f"{module_name}-command"
        
        module_path = workspace / module_name
        
        if not module_path.exists():
            return BuilderResult(
                success=False,
                message=f"Module '{module_name}' not found in your workspace",
                error="module_not_found"
            )
        
        # Validate all required files exist
        required_files = ["module.json", "handler.py"]
        missing_files = []
        for f in required_files:
            if not (module_path / f).exists():
                missing_files.append(f)
        
        if missing_files:
            return BuilderResult(
                success=False,
                message=f"Missing required files: {', '.join(missing_files)}",
                error="missing_files"
            )
        
        # Validate handler.py security
        handler_code = (module_path / "handler.py").read_text()
        sandbox = get_sandbox()
        validation_error = sandbox._validate_code(handler_code)
        
        if validation_error:
            return BuilderResult(
                success=False,
                message=f"Security validation failed: {validation_error}",
                error="validation_failed"
            )
        
        # Copy to submissions directory
        SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        submission_path = SUBMISSIONS_DIR / module_name
        
        if submission_path.exists():
            # Remove old submission
            shutil.rmtree(submission_path)
        
        shutil.copytree(module_path, submission_path)
        
        # Add submission metadata
        submission_meta = {
            "submitted_by": user_id,
            "submitted_at": datetime.now().isoformat(),
            "status": "pending",
            "source_path": str(module_path)
        }
        (submission_path / "submission.json").write_text(
            json.dumps(submission_meta, indent=2)
        )
        
        logger.info(f"Module {module_name} submitted by user {user_id}")
        
        return BuilderResult(
            success=True,
            message=f"Module '{module_name}' submitted for review!",
            data={
                "module_name": module_name,
                "submission_path": str(submission_path),
                "submitted_at": submission_meta["submitted_at"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error submitting module: {e}")
        return BuilderResult(
            success=False,
            message=f"Failed to submit module: {str(e)}",
            error=str(e)
        )


def get_module_code(user_id: int, module_name: str) -> BuilderResult:
    """
    Get the current code of a module.
    
    Args:
        user_id: Telegram user ID
        module_name: Name of the module
        
    Returns:
        BuilderResult with code content
    """
    try:
        workspace = get_user_workspace(user_id)
        
        # Normalize module name
        if not module_name.endswith("-command"):
            module_name = f"{module_name}-command"
        
        module_path = workspace / module_name
        handler_path = module_path / "handler.py"
        
        if not handler_path.exists():
            return BuilderResult(
                success=False,
                message=f"Module '{module_name}' not found",
                error="module_not_found"
            )
        
        code = handler_path.read_text()
        
        return BuilderResult(
            success=True,
            message="Code retrieved",
            data={
                "module_name": module_name,
                "code": code,
                "path": str(handler_path)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting module code: {e}")
        return BuilderResult(
            success=False,
            message=f"Failed to get code: {str(e)}",
            error=str(e)
        )


def delete_module(user_id: int, module_name: str) -> BuilderResult:
    """
    Delete a module from user's workspace (not submissions or installed).
    
    Args:
        user_id: Telegram user ID
        module_name: Name of the module
        
    Returns:
        BuilderResult confirming deletion
    """
    try:
        workspace = get_user_workspace(user_id)
        
        # Normalize module name
        if not module_name.endswith("-command"):
            module_name = f"{module_name}-command"
        
        module_path = workspace / module_name
        
        if not module_path.exists():
            return BuilderResult(
                success=False,
                message=f"Module '{module_name}' not found",
                error="module_not_found"
            )
        
        shutil.rmtree(module_path)
        
        logger.info(f"Deleted module {module_name} for user {user_id}")
        
        return BuilderResult(
            success=True,
            message=f"Module '{module_name}' deleted",
            data={"module_name": module_name}
        )
        
    except Exception as e:
        logger.error(f"Error deleting module: {e}")
        return BuilderResult(
            success=False,
            message=f"Failed to delete module: {str(e)}",
            error=str(e)
        )


async def ai_create_module(
    user_id: int,
    module_idea: str,
    auto_submit: bool = False
) -> BuilderResult:
    """
    Use AI to generate a complete module from a natural language description.
    
    This is the AI-to-module pipeline that:
    1. Uses Claude to design the module structure
    2. Generates module.json, handler.py, README.md
    3. Creates the scaffold in user's workspace
    4. Optionally auto-submits for review
    
    Args:
        user_id: Telegram user ID
        module_idea: Natural language description (e.g., "a command that shows current weather")
        auto_submit: If True, auto-submit after creation
        
    Returns:
        BuilderResult with created module info
    """
    import httpx
    import hashlib
    
    CLAUDE_API = os.getenv("ANTHROPIC_API_KEY", "")
    
    if not CLAUDE_API:
        return BuilderResult(
            success=False,
            message="AI module creation unavailable",
            error="Claude API key not configured"
        )
    
    # Generate module via Claude
    prompt = f"""You are designing a Telegram bot command module. Create a complete module from this idea:

USER IDEA: {module_idea}

Generate a complete module with:
1. A catchy but simple command name (like /weather, /timer, /joke)
2. Complete handler.py code that works
3. Module metadata

RULES:
- Command must start with /
- Handler must have: def handle(args: str, context: dict) -> str
- Keep it simple and focused
- Include error handling
- No external API calls unless absolutely necessary
- Return helpful messages

OUTPUT FORMAT (JSON):
{{
    "command": "/example",
    "module_name": "example-command",
    "description": "What this command does",
    "handler_code": "def handle(args: str, context: dict) -> str:\\n    # Your code here\\n    return 'Response'",
    "usage_example": "/example hello",
    "readme": "# Module Title\\n\\nDescription and usage..."
}}

ONLY output valid JSON. No markdown wrapping."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            response = await http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            
            if response.status_code != 200:
                return BuilderResult(
                    success=False,
                    message="AI generation failed",
                    error=f"Claude API error: {response.status_code}"
                )
            
            result = response.json()
            content = result["content"][0]["text"]
            
            # Log cost
            usage = result.get("usage", {})
            try:
                from integrations.supabase_client import get_supabase_client
                client = get_supabase_client()
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
                
                await client.log_usage_cost(
                    telegram_id=user_id,
                    operation="ai_module_create",
                    tokens=input_tokens + output_tokens,
                    cost_usd=cost,
                    model="claude-sonnet-4"
                )
            except Exception as e:
                logger.warning(f"Failed to log cost: {e}")
            
            # Parse response
            try:
                # Handle markdown wrapping
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return BuilderResult(
                    success=False,
                    message="Failed to parse AI response",
                    error=str(e)
                )
            
            # Extract module info
            command = data.get("command", "/unknown")
            module_name = data.get("module_name", "unknown-command")
            description = data.get("description", "AI-generated module")
            handler_code = data.get("handler_code", "")
            readme = data.get("readme", "")
            
            # Clean module name
            if not module_name.endswith("-command"):
                module_name = f"{module_name}-command"
            
            # Scaffold the module with AI-generated code
            scaffold_result = scaffold_module(
                user_id=user_id,
                module_name=module_name.replace("-command", ""),
                command=command,
                description=description,
                author=f"Apprentice {user_id} (AI-assisted)",
                initial_logic=handler_code
            )
            
            if not scaffold_result.success:
                return scaffold_result
            
            # Update README with AI-generated content
            if readme:
                module_path = get_user_workspace(user_id) / module_name
                readme_path = module_path / "README.md"
                try:
                    readme_path.write_text(readme)
                except Exception as e:
                    logger.warning(f"Failed to update README: {e}")
            
            # Auto-submit if requested
            if auto_submit:
                submit_result = submit_module(user_id, module_name)
                if submit_result.success:
                    return BuilderResult(
                        success=True,
                        message=f"✨ AI created module `{module_name}` and submitted for review!\n\nCommand: {command}\n{description}",
                        data={
                            "module_name": module_name,
                            "command": command,
                            "submitted": True,
                            "path": str(get_user_workspace(user_id) / module_name)
                        }
                    )
            
            return BuilderResult(
                success=True,
                message=f"✨ AI created module `{module_name}`!\n\nCommand: {command}\n{description}\n\nTest with `test_module` then `submit_module` when ready.",
                data={
                    "module_name": module_name,
                    "command": command,
                    "submitted": False,
                    "path": str(get_user_workspace(user_id) / module_name)
                }
            )
            
    except Exception as e:
        logger.error(f"AI module creation error: {e}")
        return BuilderResult(
            success=False,
            message="AI module creation failed",
            error=str(e)
        )


# Tool definitions for Aria's brain
def get_builder_tools() -> List[Dict[str, Any]]:
    """Get tool definitions for the builder tools."""
    return [
        {
            "name": "scaffold_module",
            "description": "Create a new module scaffold for an apprentice. Use when they want to build a new command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "Name for the module (e.g., 'timer', 'joke')"
                    },
                    "command": {
                        "type": "string",
                        "description": "The command trigger (e.g., '/timer', '/joke')"
                    },
                    "description": {
                        "type": "string",
                        "description": "What the module does"
                    },
                    "author": {
                        "type": "string",
                        "description": "Name of the apprentice building it"
                    },
                    "initial_logic": {
                        "type": "string",
                        "description": "Optional: The Python code for the handler logic"
                    }
                },
                "required": ["user_id", "module_name", "command", "description"]
            }
        },
        {
            "name": "update_module_code",
            "description": "Update the handler.py code in an apprentice's module. Use when they want to change or improve their code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to update"
                    },
                    "new_code": {
                        "type": "string",
                        "description": "The complete new handler.py code"
                    }
                },
                "required": ["user_id", "module_name", "new_code"]
            }
        },
        {
            "name": "test_module",
            "description": "Test an apprentice's module with given arguments. Use to let them try their code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to test"
                    },
                    "test_args": {
                        "type": "string",
                        "description": "Arguments to pass to the handler"
                    }
                },
                "required": ["user_id", "module_name"]
            }
        },
        {
            "name": "list_my_modules",
            "description": "List all modules in an apprentice's workspace with their status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    }
                },
                "required": ["user_id"]
            }
        },
        {
            "name": "submit_module",
            "description": "Submit an apprentice's module for steward review. Use when they're ready to go live.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to submit"
                    }
                },
                "required": ["user_id", "module_name"]
            }
        },
        {
            "name": "get_module_code",
            "description": "Get the current code of an apprentice's module to show or modify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module"
                    }
                },
                "required": ["user_id", "module_name"]
            }
        },
        {
            "name": "delete_module",
            "description": "Delete a module from an apprentice's workspace. Use with caution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    },
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to delete"
                    }
                },
                "required": ["user_id", "module_name"]
            }
        },
        {
            "name": "ai_create_module",
            "description": "Use AI to generate a complete module from a natural language idea. Creates module.json, handler.py, and README automatically. Perfect for apprentices who want to build something quickly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The apprentice's Telegram user ID"
                    },
                    "module_idea": {
                        "type": "string",
                        "description": "Natural language description of what the module should do (e.g., 'a command that tells dad jokes' or 'a timer that reminds me in X minutes')"
                    },
                    "auto_submit": {
                        "type": "boolean",
                        "description": "If true, automatically submit for review after creation. Default: false"
                    }
                },
                "required": ["user_id", "module_idea"]
            }
        }
    ]

