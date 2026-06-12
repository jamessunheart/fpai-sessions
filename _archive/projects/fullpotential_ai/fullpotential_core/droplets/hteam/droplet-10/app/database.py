"""
Database Connection Management
AsyncPG connection pooling and session management
"""
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import structlog

from app.config import settings

log = structlog.get_logger()

# ============================================================================
# CONNECTION POOL
# ============================================================================

class Database:
    """Database connection pool manager"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Initialize database connection pool"""
        if self.pool is not None:
            log.warning("database_already_connected")
            return
        
        try:
            # Extract connection parameters from DATABASE_URL
            # Format: postgresql+asyncpg://user:pass@host:port/dbname
            url = settings.database_url.replace('postgresql+asyncpg://', 'postgresql://')
            
            self.pool = await asyncpg.create_pool(
                url,
                min_size=5,
                max_size=settings.db_pool_size,
                max_inactive_connection_lifetime=300,
                command_timeout=settings.db_pool_timeout,
                timeout=settings.db_pool_timeout
            )
            
            log.info(
                "database_connected",
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                log.info("database_version", version=version[:50])
                
        except Exception as e:
            log.error("database_connection_failed", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close database connection pool"""
        if self.pool is None:
            return
        
        try:
            await self.pool.close()
            self.pool = None
            log.info("database_disconnected")
        except Exception as e:
            log.error("database_disconnection_failed", error=str(e))
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Acquire a database connection from the pool
        
        Usage:
            async with db.acquire() as conn:
                result = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args) -> str:
        """
        Execute a query that doesn't return data (INSERT, UPDATE, DELETE)
        Returns the status string from the query execution
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        """
        Execute a query and return all results
        Returns a list of Record objects
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Execute a query and return the first row
        Returns None if no results
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args, column: int = 0) -> Optional[any]:
        """
        Execute a query and return a single value
        Returns the first column of the first row
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, column=column)
    
    async def executemany(self, query: str, args: list) -> None:
        """
        Execute a query multiple times with different parameters
        Useful for bulk inserts
        """
        async with self.acquire() as conn:
            await conn.executemany(query, args)


# ============================================================================
# GLOBAL DATABASE INSTANCE
# ============================================================================

db = Database()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def init_db() -> None:
    """Initialize database connection (called on startup)"""
    await db.connect()


async def close_db() -> None:
    """Close database connection (called on shutdown)"""
    await db.disconnect()


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Get a database connection for dependency injection
    
    Usage in FastAPI:
        @app.get("/tasks/{task_id}")
        async def get_task(task_id: int, conn = Depends(get_db_connection)):
            return await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
    """
    async with db.acquire() as connection:
        yield connection


# ============================================================================
# TRANSACTION CONTEXT MANAGER
# ============================================================================

@asynccontextmanager
async def transaction():
    """
    Execute multiple queries in a transaction
    
    Usage:
        async with transaction() as conn:
            await conn.execute("INSERT INTO tasks ...")
            await conn.execute("INSERT INTO task_state_history ...")
            # Commits automatically if no exception
            # Rolls back automatically on exception
    """
    async with db.acquire() as conn:
        async with conn.transaction():
            yield conn


# ============================================================================
# DATABASE UTILITIES
# ============================================================================

async def record_to_dict(record: Optional[asyncpg.Record]) -> Optional[dict]:
    """Convert asyncpg Record to dictionary"""
    if record is None:
        return None
    return dict(record)


async def records_to_dicts(records: list[asyncpg.Record]) -> list[dict]:
    """Convert list of asyncpg Records to list of dictionaries"""
    return [dict(record) for record in records]


async def check_database_health() -> bool:
    """
    Check if database is healthy
    Returns True if database is accessible, False otherwise
    """
    try:
        async with db.acquire() as conn:
            await conn.fetchval('SELECT 1')
        return True
    except Exception as e:
        log.error("database_health_check_failed", error=str(e))
        return False


async def cleanup_old_heartbeats() -> int:
    """
    Remove old heartbeat records (keep only last 24 hours)
    Returns number of deleted records
    """
    try:
        result = await db.fetchval(
            """
            WITH deleted AS (
                DELETE FROM heartbeats
                WHERE received_at < NOW() - INTERVAL '24 hours'
                RETURNING *
            )
            SELECT COUNT(*) FROM deleted
            """
        )
        
        if result and result > 0:
            log.info("heartbeats_cleaned_up", deleted_count=result)
        
        return result or 0
        
    except Exception as e:
        log.error("heartbeat_cleanup_failed", error=str(e))
        return 0


async def get_database_stats() -> dict:
    """
    Get database statistics
    Returns dict with table sizes and row counts
    """
    try:
        stats = {}
        
        # Get row counts for each table
        tables = ['droplets', 'tasks', 'task_state_history', 'heartbeats', 'orchestrator_metrics']
        
        for table in tables:
            count = await db.fetchval(f'SELECT COUNT(*) FROM {table}')
            stats[f'{table}_count'] = count
        
        # Get active tasks count
        active_tasks = await db.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('pending', 'assigned', 'in_progress')"
        )
        stats['active_tasks_count'] = active_tasks
        
        # Get active droplets count
        active_droplets = await db.fetchval(
            "SELECT COUNT(*) FROM droplets WHERE status = 'active'"
        )
        stats['active_droplets_count'] = active_droplets
        
        return stats
        
    except Exception as e:
        log.error("database_stats_failed", error=str(e))
        return {}


# ============================================================================
# STARTUP/SHUTDOWN HELPERS
# ============================================================================

async def verify_database_schema() -> bool:
    """
    Verify that all required tables exist
    Returns True if schema is valid, False otherwise
    """
    required_tables = [
        'droplets',
        'tasks',
        'task_state_history',
        'heartbeats',
        'orchestrator_metrics',
        'schema_version'
    ]
    
    try:
        async with db.acquire() as conn:
            for table in required_tables:
                exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = $1
                    )
                    """,
                    table
                )
                
                if not exists:
                    log.error("missing_database_table", table=table)
                    return False
        
        log.info("database_schema_verified", tables_count=len(required_tables))
        return True
        
    except Exception as e:
        log.error("database_schema_verification_failed", error=str(e))
        return False
    