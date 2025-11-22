# 📝 CODE STANDARDS - Coding Standards for All Droplets

**Version:** 1.0
**Last Updated:** 2025-11-15
**Purpose:** Enforce consistent, maintainable, high-quality code across all droplets

---

## 1. PHILOSOPHY

**Code is read more than it's written.**

We optimize for:
- ✅ **Readability** - Clear intent over cleverness
- ✅ **Maintainability** - Easy to change in 6 months
- ✅ **Consistency** - Same patterns everywhere
- ✅ **Simplicity** - Simple solutions over complex ones

**"Any fool can write code that a computer can understand. Good programmers write code that humans can understand."** - Martin Fowler

---

## 2. PYTHON VERSION

**Standard:** Python 3.11+

**Style Guide:** PEP 8 (with modifications)

---

## 3. CODE FORMATTING

### 3.1 Use Black

**Requirement:** ALL code must be formatted with Black.

```bash
# Format all Python files
black app/ tests/ --line-length 100

# Check formatting
black app/ tests/ --check
```

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py311']
skip-string-normalization = false
```

**Why 100 chars?**
- Modern screens are wider
- Reduces line breaks in complex expressions
- Still readable

---

### 3.2 Import Ordering

**Use:** isort (compatible with Black)

```bash
isort app/ tests/
```

**Configuration** (`pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 100
```

**Import Order:**
```python
# 1. Standard library
import os
import sys
from datetime import datetime
from typing import Optional, List

# 2. Third-party libraries
from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from pydantic import BaseModel

# 3. Local imports
from app.config import settings
from app.models import Service
from app.schemas import ServiceCreate
```

---

## 4. NAMING CONVENTIONS

### 4.1 Variables & Functions
```python
# ✅ Good: snake_case
user_count = 10
def get_user_by_id(user_id: int):
    pass

# ❌ Bad: camelCase
userCount = 10
def getUserById(userId: int):
    pass
```

### 4.2 Classes
```python
# ✅ Good: PascalCase
class UserService:
    pass

class HTTPClient:
    pass

# ❌ Bad: snake_case or camelCase
class user_service:
    pass
```

### 4.3 Constants
```python
# ✅ Good: UPPERCASE_WITH_UNDERSCORES
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30

# ❌ Bad: lowercase or PascalCase
max_retry_attempts = 3
DefaultTimeout = 30
```

### 4.4 Private Members
```python
class UserService:
    # ✅ Good: leading underscore for private
    def _internal_helper(self):
        pass

    # ✅ Good: public method
    def public_method(self):
        pass

    # ❌ Bad: no indication of privacy
    def internal_helper(self):
        pass
```

### 4.5 Type Aliases
```python
# ✅ Good: PascalCase for type aliases
UserId = int
ServiceName = str
UserDict = dict[str, any]
```

---

## 5. TYPE HINTS

### 5.1 Always Use Type Hints

**Requirement:** ALL functions must have type hints.

**Good:**
```python
# ✅ Full type hints
def get_user(user_id: int) -> Optional[dict]:
    if user_id < 0:
        return None
    return {"id": user_id, "name": "John"}

def process_users(users: List[dict]) -> int:
    return len(users)
```

**Bad:**
```python
# ❌ No type hints
def get_user(user_id):
    return {"id": user_id}
```

### 5.2 Use Modern Type Hints (Python 3.10+)

```python
# ✅ Modern (Python 3.10+)
def process(items: list[str]) -> dict[str, int]:
    pass

# ❌ Old style (but still acceptable)
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]:
    pass
```

### 5.3 Optional vs Union

```python
# ✅ Preferred: Optional
def get_user(user_id: int) -> Optional[User]:
    pass

# ✅ Also acceptable: Union
def get_user(user_id: int) -> User | None:
    pass
```

---

## 6. DOCSTRINGS

### 6.1 Use Docstrings for Public APIs

**Format:** Google-style docstrings

```python
def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID.

    Args:
        user_id: The unique identifier for the user

    Returns:
        User object if found, None otherwise

    Raises:
        ValueError: If user_id is negative
    """
    if user_id < 0:
        raise ValueError("user_id must be non-negative")

    return db.query(User).filter(User.id == user_id).first()
```

**When to use docstrings:**
- ✅ Public functions and methods
- ✅ Classes
- ✅ Complex algorithms
- ❌ Simple getters/setters (type hints are enough)
- ❌ Private helper functions (unless complex)

---

## 7. FUNCTION DESIGN

### 7.1 Keep Functions Small

**Guideline:** <50 lines per function

**Good:**
```python
# ✅ Small, focused function
def validate_user(user: UserCreate) -> None:
    if not user.email:
        raise ValueError("Email required")
    if len(user.password) < 8:
        raise ValueError("Password too short")

def create_user(user: UserCreate) -> User:
    validate_user(user)
    hashed_password = hash_password(user.password)
    return User(email=user.email, password=hashed_password)
```

**Bad:**
```python
# ❌ Too long, doing too much
def create_user(user: UserCreate) -> User:
    # Validation
    if not user.email:
        raise ValueError("Email required")
    if len(user.password) < 8:
        raise ValueError("Password too short")
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", user.email):
        raise ValueError("Invalid email")

    # Password hashing
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(user.password.encode(), salt)

    # Database insertion
    ...
    # (50 more lines)
```

### 7.2 Single Responsibility

**Each function should do ONE thing.**

```python
# ✅ Good: Separate concerns
def validate_email(email: str) -> bool:
    return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def create_user(email: str, password: str) -> User:
    if not validate_email(email):
        raise ValueError("Invalid email")
    hashed = hash_password(password)
    return User(email=email, password=hashed)
```

### 7.3 Avoid Flag Arguments

**Bad:**
```python
# ❌ Boolean flag makes function do two things
def get_users(include_inactive: bool = False):
    if include_inactive:
        return db.query(User).all()
    else:
        return db.query(User).filter(User.active == True).all()
```

**Good:**
```python
# ✅ Separate functions with clear names
def get_active_users():
    return db.query(User).filter(User.active == True).all()

def get_all_users():
    return db.query(User).all()
```

---

## 8. ERROR HANDLING

### 8.1 Be Specific

**Good:**
```python
# ✅ Specific exception handling
try:
    user = get_user_by_id(user_id)
except ValueError as e:
    logger.error(f"Invalid user_id: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Bad:**
```python
# ❌ Bare except catches everything
try:
    user = get_user_by_id(user_id)
except:
    return None
```

### 8.2 Don't Swallow Exceptions

**Bad:**
```python
# ❌ Silent failure
try:
    risky_operation()
except Exception:
    pass  # Error is lost!
```

**Good:**
```python
# ✅ Log and re-raise or handle appropriately
try:
    risky_operation()
except Exception as e:
    logger.error(f"risky_operation failed: {e}")
    raise  # Re-raise the exception
```

---

## 9. LOGGING

### 9.1 Use Structured Logging

**Good:**
```python
# ✅ Structured JSON logging
import logging
import json

logger = logging.getLogger(__name__)

logger.info(json.dumps({
    "event": "user_created",
    "user_id": user.id,
    "timestamp": datetime.utcnow().isoformat()
}))
```

**Bad:**
```python
# ❌ Unstructured logging
print(f"Created user {user.id}")  # NEVER use print()
logger.info(f"Created user {user.id}")  # Hard to parse
```

### 9.2 Log Levels

```python
# DEBUG: Detailed diagnostic information
logger.debug(f"Processing user {user_id}")

# INFO: General informational messages
logger.info(json.dumps({"event": "user_login", "user_id": user_id}))

# WARNING: Degraded functionality but still working
logger.warning(f"Database slow: {duration_ms}ms")

# ERROR: Errors that need attention
logger.error(f"Failed to process payment: {error}")

# CRITICAL: System failure
logger.critical("Database connection lost")
```

### 9.3 Never Log Secrets

**Bad:**
```python
# ❌ NEVER log secrets
logger.info(f"API key: {api_key}")
logger.debug(f"Password: {password}")
```

**Good:**
```python
# ✅ Log that operation happened, not the secret
logger.info(json.dumps({"event": "api_key_created", "user_id": user.id}))
```

---

## 10. COMMENTS

### 10.1 Write Self-Documenting Code

**Good:**
```python
# ✅ Code explains itself
def calculate_total_price(items: List[Item], tax_rate: float) -> float:
    subtotal = sum(item.price for item in items)
    tax = subtotal * tax_rate
    return subtotal + tax
```

**Bad:**
```python
# ❌ Needs comments to explain
def calc(items, rate):
    # Add up prices
    s = sum(i.p for i in items)
    # Calculate tax
    t = s * rate
    # Return total
    return s + t
```

### 10.2 Use Comments for "Why", Not "What"

**Good:**
```python
# ✅ Explains WHY
# We retry 3 times because the external API is flaky
# and usually succeeds on retry
for attempt in range(3):
    try:
        return call_external_api()
    except APIError:
        if attempt == 2:
            raise
```

**Bad:**
```python
# ❌ Explains WHAT (obvious from code)
# Loop 3 times
for attempt in range(3):
    # Try to call API
    try:
        return call_external_api()
    # If error, continue
    except APIError:
        pass
```

---

## 11. TESTING

### 11.1 Test File Organization

```
tests/
├── test_health.py        # UDC endpoints
├── test_api.py           # Business logic
├── test_crud.py          # Database operations
└── conftest.py           # Pytest fixtures
```

### 11.2 Test Naming

```python
# ✅ Descriptive test names
def test_get_user_by_id_returns_user_when_exists():
    pass

def test_get_user_by_id_returns_none_when_not_found():
    pass

def test_create_user_raises_error_when_email_invalid():
    pass

# ❌ Vague test names
def test_get_user():
    pass

def test_create():
    pass
```

### 11.3 Test Structure (Arrange-Act-Assert)

```python
def test_create_user_successfully():
    # Arrange: Set up test data
    user_data = UserCreate(email="test@example.com", password="password123")

    # Act: Execute the operation
    user = create_user(user_data)

    # Assert: Verify the results
    assert user.email == "test@example.com"
    assert user.password != "password123"  # Should be hashed
    assert user.id is not None
```

### 11.4 Coverage Target

**Requirement:** >80% test coverage on business logic

```bash
# Run tests with coverage
pytest --cov=app --cov-report=html tests/

# View coverage report
open htmlcov/index.html
```

---

## 12. ANTI-PATTERNS

### 12.1 Avoid Global Mutable State

**Bad:**
```python
# ❌ Global mutable state
cache = {}

def get_from_cache(key):
    return cache.get(key)
```

**Good:**
```python
# ✅ Dependency injection
from functools import lru_cache

@lru_cache(maxsize=100)
def get_from_cache(key):
    return expensive_operation(key)
```

### 12.2 Avoid Nested Conditionals

**Bad:**
```python
# ❌ Deeply nested
def process_user(user):
    if user:
        if user.active:
            if user.email_verified:
                if user.has_subscription:
                    return do_something(user)
    return None
```

**Good:**
```python
# ✅ Early returns
def process_user(user: Optional[User]) -> Optional[Result]:
    if not user:
        return None
    if not user.active:
        return None
    if not user.email_verified:
        return None
    if not user.has_subscription:
        return None

    return do_something(user)
```

### 12.3 Avoid Magic Numbers

**Bad:**
```python
# ❌ Magic numbers
if user.age > 18:
    pass

time.sleep(86400)
```

**Good:**
```python
# ✅ Named constants
LEGAL_AGE = 18
SECONDS_IN_DAY = 86400

if user.age > LEGAL_AGE:
    pass

time.sleep(SECONDS_IN_DAY)
```

---

## 13. CODE REVIEW CHECKLIST

Before submitting code for review:

**Functionality:**
- [ ] Code works as intended
- [ ] All tests pass
- [ ] No regression in existing functionality

**Style:**
- [ ] Black formatting applied
- [ ] isort applied
- [ ] Type hints on all functions
- [ ] No print() statements

**Documentation:**
- [ ] Public APIs have docstrings
- [ ] Complex logic has comments explaining WHY
- [ ] README updated if needed

**Security:**
- [ ] No secrets in code
- [ ] Input validation with Pydantic
- [ ] SQL queries parameterized
- [ ] Errors don't leak information

**Testing:**
- [ ] New code has tests
- [ ] Coverage >80% on new code
- [ ] Edge cases tested

**Performance:**
- [ ] No obvious performance issues
- [ ] Database queries optimized
- [ ] No N+1 query problems

---

## 14. TOOLING SETUP

**Required tools:**

```bash
# Install development dependencies
pip install black isort ruff mypy pytest pytest-cov

# Format code
black app/ tests/
isort app/ tests/

# Lint code
ruff check app/ tests/

# Type check
mypy app/ --strict

# Run tests
pytest --cov=app tests/
```

**VS Code settings.json:**
```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "editor.formatOnSave": true,
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

---

## 15. PERFORMANCE CONSIDERATIONS

### 15.1 Database Queries

**Bad:**
```python
# ❌ N+1 query problem
users = db.query(User).all()
for user in users:
    user.posts  # Triggers separate query for each user
```

**Good:**
```python
# ✅ Eager loading
users = db.query(User).options(joinedload(User.posts)).all()
```

### 15.2 List Comprehensions vs Loops

**Prefer list comprehensions:**
```python
# ✅ List comprehension (faster, more Pythonic)
squares = [x ** 2 for x in range(10)]

# ❌ Loop (slower, more verbose)
squares = []
for x in range(10):
    squares.append(x ** 2)
```

### 15.3 Use Generators for Large Datasets

```python
# ✅ Generator (memory efficient)
def read_large_file(file_path):
    with open(file_path) as f:
        for line in f:
            yield line.strip()

# ❌ Load everything into memory
def read_large_file(file_path):
    with open(file_path) as f:
        return [line.strip() for line in f]  # All in memory!
```

---

**Write code as if the person maintaining it is a violent psychopath who knows where you live.**

**Be that psychopath. Demand quality.**

📝⚡💎
