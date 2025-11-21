# Code Standards

**Coding conventions for all Full Potential AI services**

---

## General Principles

1. **Readability** - Code is read more than written
2. **Simplicity** - Simple solutions over clever ones
3. **Consistency** - Follow established patterns
4. **Documentation** - Explain why, not what
5. **Testing** - Test behavior, not implementation

---

## Python Standards

### Style Guide
Follow **PEP 8** with these additions:

**Line Length:**
- Max 100 characters (not 79)
- Break long lines logically

**Naming:**
```python
# Classes: PascalCase
class UserService:
    pass

# Functions/variables: snake_case
def get_user_data():
    user_name = "John"

# Constants: UPPER_SNAKE_CASE
API_VERSION = "1.0.0"
MAX_RETRIES = 3

# Private: _leading_underscore
def _internal_helper():
    pass
```

**Imports:**
```python
# Standard library
import os
import sys
from datetime import datetime

# Third party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local
from .models import User
from .services import UserService
```

---

## FastAPI Patterns

### Project Structure
```python
src/
├── main.py              # FastAPI app initialization
├── api/
│   ├── __init__.py
│   ├── routes.py        # Route definitions
│   └── dependencies.py  # Dependency injection
├── models/
│   ├── __init__.py
│   └── schemas.py       # Pydantic models
├── services/
│   ├── __init__.py
│   └── user_service.py  # Business logic
└── utils/
    ├── __init__.py
    └── helpers.py       # Utility functions
```

### Dependency Injection
```python
from fastapi import Depends

async def get_db():
    db = Database()
    try:
        yield db
    finally:
        await db.close()

@app.get("/users")
async def get_users(db = Depends(get_db)):
    return await db.query("SELECT * FROM users")
```

### Error Handling
```python
from fastapi import HTTPException

@app.get("/user/{user_id}")
async def get_user(user_id: int):
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

---

## Type Hints

**Always use type hints:**
```python
from typing import List, Optional, Dict, Any

def get_users(limit: int = 10) -> List[Dict[str, Any]]:
    """Get list of users.

    Args:
        limit: Maximum number of users to return

    Returns:
        List of user dictionaries
    """
    return users[:limit]

async def get_user(user_id: int) -> Optional[User]:
    """Get user by ID."""
    return await db.query_one(User, user_id)
```

---

## Docstrings

**Use Google-style docstrings:**
```python
def calculate_revenue(
    sessions: int,
    rate_per_session: float,
    conversion_rate: float = 0.3
) -> float:
    """Calculate projected revenue.

    Args:
        sessions: Number of sessions
        rate_per_session: Revenue per session
        conversion_rate: Conversion rate (default 0.3)

    Returns:
        Projected revenue in dollars

    Raises:
        ValueError: If sessions or rate is negative

    Examples:
        >>> calculate_revenue(100, 50.0)
        1500.0
    """
    if sessions < 0 or rate_per_session < 0:
        raise ValueError("Sessions and rate must be positive")

    return sessions * rate_per_session * conversion_rate
```

---

## Error Handling

### Use Specific Exceptions
```python
# ❌ WRONG - Too broad
try:
    result = risky_operation()
except Exception:
    pass

# ✅ CORRECT - Specific
try:
    result = risky_operation()
except FileNotFoundError:
    logger.error("File not found")
    raise
except PermissionError:
    logger.error("Permission denied")
    raise
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Log levels
logger.debug("Detailed diagnostic info")
logger.info("General informational messages")
logger.warning("Warning messages")
logger.error("Error messages")
logger.critical("Critical issues")

# Include context
logger.error(f"Failed to process user {user_id}: {error}", exc_info=True)
```

---

## Async/Await

**Use async for I/O operations:**
```python
import httpx

# ✅ CORRECT - Async for network calls
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# ❌ WRONG - Sync blocks event loop
def fetch_data(url: str) -> dict:
    import requests
    return requests.get(url).json()
```

---

## Testing

### Test Structure
```python
# tests/test_user_service.py
import pytest
from src.services.user_service import UserService

@pytest.fixture
def user_service():
    """Create user service for testing."""
    return UserService()

def test_get_user_success(user_service):
    """Test successful user retrieval."""
    user = user_service.get_user(1)
    assert user is not None
    assert user.id == 1

def test_get_user_not_found(user_service):
    """Test user not found."""
    user = user_service.get_user(999)
    assert user is None

@pytest.mark.asyncio
async def test_async_operation():
    """Test async operations."""
    result = await async_function()
    assert result == expected
```

### Test Coverage
```bash
# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Minimum 80% coverage required
```

---

## Configuration

**Use environment variables:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    service_name: str
    service_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## Database Queries

**Use parameterized queries:**
```python
# ❌ WRONG - SQL injection risk
user_id = request.user_id
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ CORRECT - Parameterized
query = "SELECT * FROM users WHERE id = %s"
result = await db.query(query, (user_id,))
```

---

## API Response Format

**Standardize responses:**
```python
from pydantic import BaseModel

class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    data: Any
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None

@app.get("/users")
async def get_users():
    users = await db.get_users()
    return SuccessResponse(data=users, message="Users retrieved")
```

---

## Comments

**Write self-documenting code:**
```python
# ❌ WRONG - Obvious comment
# Increment counter
counter += 1

# ✅ CORRECT - Explain why
# Reset counter after batch to prevent overflow
if counter >= BATCH_SIZE:
    counter = 0
```

**Comment complex logic:**
```python
# Calculate revenue with tiered pricing:
# - First 100 sessions: $50/session
# - Next 400 sessions: $40/session
# - Remaining sessions: $30/session
revenue = calculate_tiered_revenue(sessions)
```

---

## Git Commit Messages

**Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat: Add user authentication endpoint

Implements JWT-based authentication with refresh tokens.
Includes rate limiting to prevent brute force attacks.

Closes #123

---

fix: Correct revenue calculation for tiered pricing

Previous calculation didn't account for edge case when
sessions exactly matched tier boundary.

---

docs: Update API documentation for /users endpoint
```

---

## Code Review Checklist

**Before submitting code:**

- [ ] Code follows style guide
- [ ] Type hints added
- [ ] Docstrings written
- [ ] Tests added/updated
- [ ] Tests pass locally
- [ ] No sensitive data in code
- [ ] Error handling implemented
- [ ] Logging added where appropriate
- [ ] Documentation updated
- [ ] Commit messages clear

---

## Performance

**Optimize where it matters:**
```python
# ❌ WRONG - N+1 query problem
users = await db.get_users()
for user in users:
    posts = await db.get_posts(user.id)  # Separate query per user

# ✅ CORRECT - Single query with join
users_with_posts = await db.query("""
    SELECT u.*, p.* FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
""")
```

**Cache expensive operations:**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """Cached expensive operation."""
    return sum(range(n))
```

---

## Security

**Validate all inputs:**
```python
from pydantic import BaseModel, validator, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    age: int

    @validator('age')
    def age_valid(cls, v):
        if not 0 < v < 150:
            raise ValueError('Age must be between 0 and 150')
        return v
```

**Never expose internal errors:**
```python
try:
    result = dangerous_operation()
except Exception as e:
    logger.error(f"Internal error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

**Code quality matters. Follow these standards for consistency and maintainability.**
