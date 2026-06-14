# Learning Progression

**Quality expectations and skill development for Claude Code sessions**

---

## Overview

As you build more services, your capabilities increase. This guide shows:
- What quality looks like at each stage
- How to progress from novice to expert
- What to focus on at each level

**Goal:** Continuous improvement in building production-quality services

---

## Progression Levels

### Level 1: Novice Builder 🌱
**Experience:** 0-2 services built
**Focus:** Learning the basics

**What you can do:**
- Follow ASSEMBLY_LINE_SOP.md step-by-step
- Copy from _TEMPLATE and customize
- Implement basic CRUD endpoints
- Write simple tests
- Deploy with guidance

**Quality expectations:**
- ✅ Service starts and responds
- ✅ Basic functionality works
- ✅ Tests exist (coverage >60%)
- ✅ Follows file structure
- ⚠️ May need help with errors

**Common challenges:**
- Understanding async/await
- Writing effective tests
- Debugging errors
- Deployment issues

**Next steps:**
- Build 2-3 simple services
- Read CODE_STANDARDS.md thoroughly
- Practice writing tests
- Learn deployment process

**Resources:**
- MEMORY/APPRENTICE_HANDBOOK.md
- MEMORY/DEVELOPER_ACCELERATION_KIT.md
- shared-knowledge/troubleshooting.md

---

### Level 2: Competent Builder 🌿
**Experience:** 3-5 services built
**Focus:** Building independently

**What you can do:**
- Build services without step-by-step guidance
- Design APIs from requirements
- Write comprehensive tests
- Handle errors gracefully
- Deploy independently
- Debug common issues

**Quality expectations:**
- ✅ All UDC endpoints implemented
- ✅ Test coverage >80%
- ✅ Error handling present
- ✅ Code follows standards
- ✅ Documentation clear
- ⚠️ May struggle with complex integrations

**Common challenges:**
- Service-to-service communication
- Complex business logic
- Performance optimization
- Security considerations

**Next steps:**
- Build services that integrate with others
- Practice security best practices
- Learn performance optimization
- Help novice builders

**Resources:**
- MEMORY/INTEGRATION_GUIDE.md
- MEMORY/SECURITY_REQUIREMENTS.md
- shared-knowledge/patterns.md

---

### Level 3: Proficient Builder 🌳
**Experience:** 6-10 services built
**Focus:** Quality and architecture

**What you can do:**
- Design complex service architectures
- Integrate multiple services
- Write highly testable code
- Optimize performance
- Implement security best practices
- Review others' code
- Share effective patterns

**Quality expectations:**
- ✅ Excellent test coverage (>90%)
- ✅ Comprehensive error handling
- ✅ Performance optimized
- ✅ Security audited
- ✅ Documentation excellent
- ✅ Patterns reusable

**Common challenges:**
- Microservices orchestration
- Distributed system complexity
- Scaling considerations
- Advanced security

**Next steps:**
- Design multi-service systems
- Optimize for scale
- Create reusable patterns
- Mentor other sessions

**Resources:**
- MEMORY/VERIFICATION_PROTOCOL.md
- shared-knowledge/best-practices.md
- Core architecture docs

---

### Level 4: Expert Builder 🌲
**Experience:** 10+ services built
**Focus:** Innovation and leadership

**What you can do:**
- Design entire ecosystems
- Create new patterns and standards
- Solve novel problems
- Optimize system-wide performance
- Lead architectural decisions
- Mentor multiple sessions
- Improve development processes

**Quality expectations:**
- ✅ Production-grade quality
- ✅ Innovative solutions
- ✅ Reusable components
- ✅ System thinking
- ✅ Documentation as teaching tool
- ✅ Standards advancement

**Contributions:**
- Improve MEMORY/ documentation
- Create new acceleration patterns
- Enhance verification protocols
- Guide system architecture
- Share advanced learnings

**Resources:**
- Create your own!
- Contribute to MEMORY/
- Share in shared-knowledge/

---

## Quality Rubric

### Code Quality

**Level 1 (Novice):**
```python
# ⚠️ Works but could be better
def get_user(id):
    user = db.query(f"SELECT * FROM users WHERE id = {id}")
    return user
```

**Level 2 (Competent):**
```python
# ✅ Better: Types, parameterized query
def get_user(user_id: int) -> dict:
    user = db.query("SELECT * FROM users WHERE id = %s", (user_id,))
    return user
```

**Level 3 (Proficient):**
```python
# ✅✅ Great: Error handling, logging, docs
from typing import Optional

async def get_user(user_id: int) -> Optional[User]:
    """Get user by ID.

    Args:
        user_id: User's unique identifier

    Returns:
        User object if found, None otherwise

    Raises:
        DatabaseError: If database query fails
    """
    try:
        user = await db.query_one("SELECT * FROM users WHERE id = %s", (user_id,))
        return User(**user) if user else None
    except DatabaseError as e:
        logger.error(f"Failed to fetch user {user_id}: {e}")
        raise
```

**Level 4 (Expert):**
```python
# ✅✅✅ Excellent: Caching, metrics, resilience
from functools import lru_cache
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
@lru_cache(maxsize=128)
async def get_user(
    user_id: int,
    include_deleted: bool = False
) -> Optional[User]:
    """Get user by ID with caching and retry logic.

    Automatically retries up to 3 times on failure.
    Results are cached for performance.

    Args:
        user_id: User's unique identifier
        include_deleted: Whether to include soft-deleted users

    Returns:
        User object if found, None otherwise

    Raises:
        DatabaseError: If database query fails after retries
    """
    query = """
        SELECT * FROM users
        WHERE id = %s
        AND (deleted_at IS NULL OR %s)
    """

    with metrics.timer("db.get_user"):
        try:
            user = await db.query_one(query, (user_id, include_deleted))
            metrics.increment("db.get_user.success")
            return User(**user) if user else None
        except DatabaseError as e:
            metrics.increment("db.get_user.error")
            logger.error(f"Failed to fetch user {user_id}: {e}", exc_info=True)
            raise
```

---

## Test Quality

### Level 1 (Novice):
```python
# ⚠️ Basic test
def test_get_user():
    user = get_user(1)
    assert user is not None
```

### Level 2 (Competent):
```python
# ✅ Tests happy path and error case
def test_get_user_success():
    user = get_user(1)
    assert user.id == 1
    assert user.name == "Test User"

def test_get_user_not_found():
    user = get_user(999)
    assert user is None
```

### Level 3 (Proficient):
```python
# ✅✅ Comprehensive tests with fixtures
import pytest

@pytest.fixture
async def sample_user(db):
    """Create sample user for testing."""
    user_id = await db.execute(
        "INSERT INTO users (name) VALUES (%s) RETURNING id",
        ("Test User",)
    )
    yield user_id
    await db.execute("DELETE FROM users WHERE id = %s", (user_id,))

@pytest.mark.asyncio
async def test_get_user_success(sample_user):
    user = await get_user(sample_user)
    assert user.id == sample_user
    assert user.name == "Test User"

@pytest.mark.asyncio
async def test_get_user_not_found():
    user = await get_user(999999)
    assert user is None

@pytest.mark.asyncio
async def test_get_user_database_error(monkeypatch):
    async def mock_query(*args):
        raise DatabaseError("Connection failed")

    monkeypatch.setattr("db.query_one", mock_query)

    with pytest.raises(DatabaseError):
        await get_user(1)
```

### Level 4 (Expert):
```python
# ✅✅✅ Full coverage including edge cases, performance
import pytest
from unittest.mock import AsyncMock, patch

class TestGetUser:
    """Comprehensive test suite for get_user function."""

    @pytest.fixture
    async def sample_users(self, db):
        """Create multiple test users."""
        users = []
        for i in range(5):
            user_id = await db.execute(
                "INSERT INTO users (name) VALUES (%s) RETURNING id",
                (f"User {i}",)
            )
            users.append(user_id)
        yield users
        await db.execute("DELETE FROM users WHERE id = ANY(%s)", (users,))

    @pytest.mark.asyncio
    async def test_get_existing_user(self, sample_users):
        """Test retrieving existing user."""
        user = await get_user(sample_users[0])
        assert user.id == sample_users[0]
        assert isinstance(user, User)

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self):
        """Test retrieving non-existent user returns None."""
        user = await get_user(999999)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_deleted_user_excluded_by_default(self, db):
        """Test deleted users are excluded unless specified."""
        user_id = await db.execute(
            "INSERT INTO users (name, deleted_at) VALUES (%s, NOW()) RETURNING id",
            ("Deleted User",)
        )

        user = await get_user(user_id)
        assert user is None

        user = await get_user(user_id, include_deleted=True)
        assert user is not None

    @pytest.mark.asyncio
    async def test_caching_works(self, sample_users):
        """Test results are cached."""
        with patch("db.query_one") as mock_query:
            # First call hits database
            await get_user(sample_users[0])
            assert mock_query.called

            # Second call uses cache
            mock_query.reset_mock()
            await get_user(sample_users[0])
            assert not mock_query.called

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test automatic retry on database errors."""
        with patch("db.query_one") as mock_query:
            mock_query.side_effect = [
                DatabaseError("Temporary failure"),
                DatabaseError("Temporary failure"),
                {"id": 1, "name": "User"}  # Success on 3rd try
            ]

            user = await get_user(1)
            assert user is not None
            assert mock_query.call_count == 3

    @pytest.mark.asyncio
    async def test_performance(self, sample_users):
        """Test query performance is acceptable."""
        import time

        start = time.time()
        await get_user(sample_users[0])
        duration = time.time() - start

        assert duration < 0.1, "Query took too long"
```

---

## Documentation Quality

### Level 1 (Novice):
```markdown
# My Service

This service does stuff.

## Run
python3 src/main.py
```

### Level 2 (Competent):
```markdown
# Email Service

**Port:** 8500
**Status:** Production

## Overview
Sends automated emails to users.

## Quick Start
\`\`\`bash
pip install -r requirements.txt
python3 src/main.py
\`\`\`

## API
- POST /api/send-email - Sends email
```

### Level 3 (Proficient):
```markdown
# Email Service

**Status:** Production
**Port:** 8500
**Version:** 1.2.0
**Coverage:** 92%

## Overview
Handles all email communications including transactional emails,
marketing campaigns, and system notifications.

## Quick Start
\`\`\`bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587

# Run service
python3 src/main.py

# Access at: http://localhost:8500
\`\`\`

## API Documentation

### Send Email
**POST /api/send-email**

Request:
\`\`\`json
{
  "to": "user@example.com",
  "subject": "Welcome",
  "body": "Welcome to our service!",
  "template": "welcome"
}
\`\`\`

Response:
\`\`\`json
{
  "id": "msg_123",
  "status": "queued",
  "scheduled_at": "2025-11-15T23:00:00Z"
}
\`\`\`

## Architecture
- FastAPI for API layer
- Celery for background processing
- Redis for queue
- PostgreSQL for tracking

## Deployment
See PRODUCTION/deployment_log.md

## Monitoring
Health: http://localhost:8500/health
Metrics: http://localhost:8500/metrics
```

### Level 4 (Expert):
```markdown
# Email Service

**Status:** Production | **Port:** 8500 | **Version:** 2.0.0 | **Coverage:** 95%
**Responsible:** Session #5 | **Last Updated:** 2025-11-15

## Overview

Enterprise-grade email service handling 10K+ emails/day with:
- Template rendering with Jinja2
- Background processing with Celery
- Retry logic with exponential backoff
- Delivery tracking and analytics
- Bounce/complaint handling

## Architecture

\`\`\`
┌─────────────┐
│   FastAPI   │  Receives requests, validates input
└──────┬──────┘
       │
       v
┌─────────────┐
│   Celery    │  Background task processing
└──────┬──────┘
       │
       v
┌─────────────┐
│    SMTP     │  Actual email delivery
└─────────────┘
\`\`\`

## Quick Start

### Local Development
\`\`\`bash
# Clone and setup
cd SERVICES/email-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add SMTP credentials

# Run service
python3 src/main.py

# Run Celery worker (separate terminal)
celery -A src.tasks worker --loglevel=info

# Run tests
pytest tests/ -v --cov=src
\`\`\`

### Production Deployment
\`\`\`bash
./deploy.sh production
\`\`\`

## API Documentation

Full API docs: http://localhost:8500/docs

### Send Email
**POST /api/v2/send**

Sends email immediately or schedules for later delivery.

**Request:**
\`\`\`json
{
  "to": "user@example.com",
  "subject": "Welcome to our platform",
  "template": "welcome",
  "variables": {
    "name": "John",
    "activation_link": "https://..."
  },
  "scheduled_at": "2025-11-16T09:00:00Z"  // Optional
}
\`\`\`

**Response:**
\`\`\`json
{
  "id": "msg_7x9k2p",
  "status": "queued",
  "scheduled_at": "2025-11-16T09:00:00Z",
  "estimated_delivery": "2025-11-16T09:00:05Z"
}
\`\`\`

**Error Codes:**
- 400: Invalid email address
- 429: Rate limit exceeded
- 500: SMTP server error

**Rate Limits:**
- 100 requests/minute per API key
- 10,000 emails/day per account

### Track Delivery
**GET /api/v2/status/{message_id}**

Returns delivery status of sent email.

## Configuration

### Environment Variables
\`\`\`bash
# Required
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=SG.xxx

# Optional
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost/emails
MAX_RETRIES=3
RETRY_BACKOFF=60
\`\`\`

## Monitoring

### Health Checks
\`\`\`bash
curl http://localhost:8500/health
# Returns: {"status": "healthy", "smtp": "connected", "redis": "connected"}
\`\`\`

### Metrics
- Emails sent/hour
- Delivery success rate
- Average processing time
- Queue length

### Logs
\`\`\`bash
# On server
journalctl -u email-service -f

# Or centralized
tail -f /var/log/email-service.log
\`\`\`

## Performance

- **Throughput:** 100 emails/second
- **Latency:** <50ms API response
- **Delivery Time:** <5 seconds (average)
- **Success Rate:** 99.7%

## Dependencies

### Internal Services
- credential-vault: For SMTP credentials
- user-service: For user data

### External Services
- SendGrid: Email delivery
- Redis: Task queue
- PostgreSQL: Delivery tracking

## Troubleshooting

See [shared-knowledge/troubleshooting.md](../../docs/coordination/shared-knowledge/troubleshooting.md#email-service)

## Contributing

When modifying this service:
1. Update SPECS.md with requirement changes
2. Write tests for new features
3. Update this README
4. Run verification: `./verify.sh`
5. Deploy to staging first
6. Broadcast changes to other sessions

## Version History

### 2.0.0 (2025-11-15)
- Added template system
- Implemented scheduling
- Added delivery tracking

### 1.0.0 (2025-11-10)
- Initial release
- Basic email sending

---

**Built with ❤️ by Session #5 | Part of Full Potential AI ecosystem**
```

---

## Progression Tips

### For Level 1 → 2:
- Build consistently (1 service/week)
- Read others' code
- Ask questions
- Focus on testing

### For Level 2 → 3:
- Integrate services together
- Study security best practices
- Optimize performance
- Review code actively

### For Level 3 → 4:
- Design system architectures
- Create reusable patterns
- Mentor other sessions
- Contribute to standards

---

## Learning Resources

**By Level:**
- **Level 1:** APPRENTICE_HANDBOOK.md, ASSEMBLY_LINE_SOP.md
- **Level 2:** INTEGRATION_GUIDE.md, CODE_STANDARDS.md
- **Level 3:** VERIFICATION_PROTOCOL.md, SECURITY_REQUIREMENTS.md
- **Level 4:** shared-knowledge/, core architecture docs

**For All Levels:**
- shared-knowledge/learnings.md - Past learnings
- shared-knowledge/patterns.md - Proven patterns
- shared-knowledge/troubleshooting.md - Common issues

---

**Progress continuously → Build better → Achieve mastery**
