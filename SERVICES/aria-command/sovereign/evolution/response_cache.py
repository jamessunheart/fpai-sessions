#!/usr/bin/env python3
"""
ARIA RESPONSE CACHE
====================

Intelligent caching of successful responses for instant retrieval.

Features:
- Query similarity matching (not just exact match)
- TTL based on query type (facts vs dynamic data)
- Success-weighted caching (higher success = longer TTL)
- Cost savings tracking
- Auto-invalidation on correction

This enables:
- Instant responses for repeated queries
- Zero API cost for cached responses
- Learning from successful patterns
"""

import os
import json
import sqlite3
import hashlib
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from collections import OrderedDict

logger = logging.getLogger("aria.evolution.cache")

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")

# ============================================================================
# TTL CONFIGURATION BY QUERY TYPE
# ============================================================================

# TTL in hours based on query intent
TTL_CONFIG = {
    "factual": 24,       # Facts don't change often
    "help": 168,         # Help/docs rarely change (1 week)
    "server_status": 1,  # Server status changes frequently
    "trading": 0.5,      # Trading data is very dynamic (30 min)
    "conversation": 4,   # Casual chat can be cached for a bit
    "build": 2,          # Code-related might change
    "default": 4         # Default 4 hours
}

# Query type detection patterns
QUERY_TYPE_PATTERNS = {
    "factual": [r'\bwhat\s+is\b', r'\bwho\s+is\b', r'\bdefine\b', r'\bexplain\b'],
    "help": [r'\bhow\s+to\b', r'\bhelp\b', r'/help', r'/commands'],
    "server_status": [r'\bserver\s+status\b', r'\bservice\s+status\b', r'/servers', r'/memory'],
    "trading": [r'\btrade\b', r'\bposition\b', r'\bsignal\b', r'\bbtc\b', r'\beth\b', r'\bsol\b'],
    "build": [r'\bcreate\b', r'\bedit\b', r'\bfile\b', r'\bbuild\b', r'\bcode\b'],
    "conversation": [r'\bhello\b', r'\bhi\b', r'\bhow\s+are\s+you\b']
}


@dataclass
class CachedResponse:
    """A cached response entry."""
    id: Optional[int] = None
    query_hash: str = ""
    query_pattern: str = ""  # Normalized query
    query_type: str = "default"
    
    # Cached content
    response: str = ""
    response_summary: str = ""  # Short summary for quick display
    tools_used: List[str] = field(default_factory=list)
    
    # Quality metrics
    success_count: int = 1  # Times this was successful
    total_uses: int = 1     # Total times used
    success_rate: float = 1.0
    avg_original_time_ms: float = 0  # How long original took
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    
    # Cost tracking
    original_cost_usd: float = 0.0  # Cost of original response
    cost_saved_usd: float = 0.0     # Total cost saved by cache hits


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

CACHE_SCHEMA = """
-- Response cache
CREATE TABLE IF NOT EXISTS response_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    query_pattern TEXT NOT NULL,
    query_type TEXT DEFAULT 'default',
    response TEXT NOT NULL,
    response_summary TEXT,
    tools_used TEXT,
    success_count INTEGER DEFAULT 1,
    total_uses INTEGER DEFAULT 1,
    success_rate REAL DEFAULT 1.0,
    avg_original_time_ms REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_used TEXT NOT NULL,
    original_cost_usd REAL DEFAULT 0,
    cost_saved_usd REAL DEFAULT 0,
    user_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_cache_hash ON response_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON response_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_success ON response_cache(success_rate DESC);

-- Cache statistics
CREATE TABLE IF NOT EXISTS cache_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    hits INTEGER DEFAULT 0,
    misses INTEGER DEFAULT 0,
    cost_saved_usd REAL DEFAULT 0,
    time_saved_ms REAL DEFAULT 0,
    UNIQUE(date)
);

CREATE INDEX IF NOT EXISTS idx_cache_stats_date ON cache_stats(date DESC);

-- Similar query mappings (for fuzzy matching)
CREATE TABLE IF NOT EXISTS similar_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL,
    similar_hash TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    verified INTEGER DEFAULT 0,
    UNIQUE(query_hash, similar_hash)
);

CREATE INDEX IF NOT EXISTS idx_similar_hash ON similar_queries(query_hash);
"""


# ============================================================================
# RESPONSE CACHE
# ============================================================================

class ResponseCache:
    """
    Intelligent response caching with TTL and similarity matching.
    
    Workflow:
    1. Before processing: check_cache(query) - returns cached response if valid
    2. After successful response: cache_response(query, response, ...)
    3. On correction: invalidate(query) - remove bad cached responses
    4. Periodic: cleanup_expired() - remove stale entries
    """
    
    def __init__(self, db_path: str = DB_PATH, max_memory_items: int = 200):
        self.db_path = db_path
        self._local = threading.local()
        self.max_memory_items = max_memory_items
        
        # LRU cache in memory for fastest access
        self._memory_cache: OrderedDict[str, CachedResponse] = OrderedDict()
        
        self._init_db()
        self._load_hot_cache()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get cursor with auto-commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """Initialize database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._cursor() as cursor:
            cursor.executescript(CACHE_SCHEMA)
        logger.info("Response cache initialized")
    
    def _load_hot_cache(self):
        """Load frequently used responses into memory."""
        try:
            with self._cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM response_cache
                    WHERE expires_at >= ? AND success_rate >= 0.7
                    ORDER BY total_uses DESC
                    LIMIT ?
                """, (datetime.now().isoformat(), self.max_memory_items))
                
                for row in cursor.fetchall():
                    entry = CachedResponse(
                        id=row["id"],
                        query_hash=row["query_hash"],
                        query_pattern=row["query_pattern"],
                        query_type=row["query_type"],
                        response=row["response"],
                        response_summary=row["response_summary"],
                        tools_used=json.loads(row["tools_used"] or "[]"),
                        success_count=row["success_count"],
                        total_uses=row["total_uses"],
                        success_rate=row["success_rate"],
                        avg_original_time_ms=row["avg_original_time_ms"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        expires_at=datetime.fromisoformat(row["expires_at"]),
                        last_used=datetime.fromisoformat(row["last_used"]),
                        original_cost_usd=row["original_cost_usd"],
                        cost_saved_usd=row["cost_saved_usd"]
                    )
                    self._memory_cache[entry.query_hash] = entry
                
                logger.info(f"Loaded {len(self._memory_cache)} responses into hot cache")
                
        except Exception as e:
            logger.warning(f"Hot cache load error: {e}")
    
    def _normalize_query(self, query: str) -> str:
        """Normalize a query for consistent hashing."""
        # Lowercase
        normalized = query.lower()
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        # Remove punctuation except key chars
        normalized = re.sub(r'[^\w\s?]', '', normalized)
        return normalized
    
    def _hash_query(self, query: str) -> str:
        """Generate hash from normalized query."""
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _detect_query_type(self, query: str) -> str:
        """Detect the type of query for TTL assignment."""
        query_lower = query.lower()
        
        for query_type, patterns in QUERY_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return query_type
        
        return "default"
    
    def _calculate_ttl(self, query_type: str, success_rate: float = 1.0) -> timedelta:
        """Calculate TTL based on query type and success rate."""
        base_hours = TTL_CONFIG.get(query_type, TTL_CONFIG["default"])
        
        # Higher success rate = longer TTL
        adjusted_hours = base_hours * (0.5 + 0.5 * success_rate)
        
        return timedelta(hours=adjusted_hours)
    
    # ========================================================================
    # CACHE OPERATIONS
    # ========================================================================
    
    def check_cache(self, query: str) -> Optional[CachedResponse]:
        """
        Check if we have a valid cached response for this query.
        
        Returns:
            CachedResponse if found and valid, None otherwise
        """
        query_hash = self._hash_query(query)
        
        # 1. Check memory cache first (fastest)
        if query_hash in self._memory_cache:
            entry = self._memory_cache[query_hash]
            if entry.expires_at > datetime.now():
                # Move to end (LRU)
                self._memory_cache.move_to_end(query_hash)
                self._record_hit(entry)
                return entry
            else:
                # Expired, remove
                del self._memory_cache[query_hash]
        
        # 2. Check database
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM response_cache
                WHERE query_hash = ? AND expires_at >= ?
            """, (query_hash, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                entry = CachedResponse(
                    id=row["id"],
                    query_hash=row["query_hash"],
                    query_pattern=row["query_pattern"],
                    query_type=row["query_type"],
                    response=row["response"],
                    response_summary=row["response_summary"],
                    tools_used=json.loads(row["tools_used"] or "[]"),
                    success_count=row["success_count"],
                    total_uses=row["total_uses"],
                    success_rate=row["success_rate"],
                    avg_original_time_ms=row["avg_original_time_ms"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]),
                    last_used=datetime.fromisoformat(row["last_used"]),
                    original_cost_usd=row["original_cost_usd"],
                    cost_saved_usd=row["cost_saved_usd"]
                )
                
                # Add to memory cache
                self._add_to_memory_cache(entry)
                self._record_hit(entry)
                return entry
        
        # 3. Check for similar queries
        similar = self._find_similar_cached(query_hash)
        if similar:
            self._record_hit(similar)
            return similar
        
        # Cache miss
        self._record_miss()
        return None
    
    def cache_response(
        self,
        query: str,
        response: str,
        tools_used: List[str] = None,
        response_time_ms: float = 0,
        cost_usd: float = 0,
        user_id: str = None
    ) -> CachedResponse:
        """
        Cache a successful response.
        
        Call this after a successful interaction that should be cached.
        """
        query_hash = self._hash_query(query)
        query_type = self._detect_query_type(query)
        ttl = self._calculate_ttl(query_type)
        
        entry = CachedResponse(
            query_hash=query_hash,
            query_pattern=self._normalize_query(query),
            query_type=query_type,
            response=response,
            response_summary=response[:200] if len(response) > 200 else response,
            tools_used=tools_used or [],
            success_count=1,
            total_uses=1,
            success_rate=1.0,
            avg_original_time_ms=response_time_ms,
            created_at=datetime.now(),
            expires_at=datetime.now() + ttl,
            last_used=datetime.now(),
            original_cost_usd=cost_usd,
            cost_saved_usd=0
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO response_cache (
                    query_hash, query_pattern, query_type, response, response_summary,
                    tools_used, success_count, total_uses, success_rate,
                    avg_original_time_ms, created_at, expires_at, last_used,
                    original_cost_usd, cost_saved_usd, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(query_hash) DO UPDATE SET
                    response = excluded.response,
                    response_summary = excluded.response_summary,
                    tools_used = excluded.tools_used,
                    success_count = success_count + 1,
                    total_uses = total_uses + 1,
                    success_rate = (success_rate * total_uses + 1.0) / (total_uses + 1),
                    avg_original_time_ms = (avg_original_time_ms * total_uses + excluded.avg_original_time_ms) / (total_uses + 1),
                    expires_at = excluded.expires_at,
                    last_used = excluded.last_used
            """, (
                entry.query_hash,
                entry.query_pattern,
                entry.query_type,
                entry.response[:10000],  # Truncate very long responses
                entry.response_summary,
                json.dumps(entry.tools_used),
                1, 1, 1.0,
                response_time_ms,
                entry.created_at.isoformat(),
                entry.expires_at.isoformat(),
                entry.last_used.isoformat(),
                cost_usd, 0, user_id
            ))
            entry.id = cursor.lastrowid
        
        # Add to memory cache
        self._add_to_memory_cache(entry)
        
        logger.debug(f"Cached response for: {query[:50]}... (TTL: {ttl})")
        
        return entry
    
    def record_success(self, query: str):
        """Record that a cached response was successful (user happy)."""
        query_hash = self._hash_query(query)
        
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE response_cache
                SET success_count = success_count + 1,
                    success_rate = (success_rate * total_uses + 1.0) / (total_uses + 1),
                    total_uses = total_uses + 1,
                    expires_at = datetime(expires_at, '+1 hour')
                WHERE query_hash = ?
            """, (query_hash,))
        
        # Update memory cache
        if query_hash in self._memory_cache:
            entry = self._memory_cache[query_hash]
            entry.success_count += 1
            entry.total_uses += 1
            entry.success_rate = entry.success_count / entry.total_uses
            entry.expires_at += timedelta(hours=1)
    
    def invalidate(self, query: str, reason: str = "correction"):
        """
        Invalidate a cached response (e.g., after a correction).
        
        Doesn't delete, just marks as expired for analysis.
        """
        query_hash = self._hash_query(query)
        
        # Remove from memory cache
        if query_hash in self._memory_cache:
            del self._memory_cache[query_hash]
        
        # Mark as expired in DB
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE response_cache
                SET expires_at = ?,
                    success_rate = success_rate * 0.5
                WHERE query_hash = ?
            """, (datetime.now().isoformat(), query_hash))
        
        logger.info(f"Invalidated cache for query due to: {reason}")
    
    def _add_to_memory_cache(self, entry: CachedResponse):
        """Add entry to memory cache with LRU eviction."""
        if len(self._memory_cache) >= self.max_memory_items:
            # Remove oldest
            self._memory_cache.popitem(last=False)
        
        self._memory_cache[entry.query_hash] = entry
    
    def _find_similar_cached(self, query_hash: str) -> Optional[CachedResponse]:
        """Find a similar cached query."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT rc.* FROM similar_queries sq
                JOIN response_cache rc ON sq.similar_hash = rc.query_hash
                WHERE sq.query_hash = ? AND rc.expires_at >= ? AND sq.verified = 1
                ORDER BY sq.similarity_score DESC
                LIMIT 1
            """, (query_hash, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                return CachedResponse(
                    id=row["id"],
                    query_hash=row["query_hash"],
                    query_pattern=row["query_pattern"],
                    query_type=row["query_type"],
                    response=row["response"],
                    response_summary=row["response_summary"],
                    tools_used=json.loads(row["tools_used"] or "[]"),
                    success_count=row["success_count"],
                    total_uses=row["total_uses"],
                    success_rate=row["success_rate"],
                    expires_at=datetime.fromisoformat(row["expires_at"])
                )
        
        return None
    
    def _record_hit(self, entry: CachedResponse):
        """Record a cache hit."""
        today = datetime.now().strftime("%Y-%m-%d")
        cost_saved = entry.original_cost_usd
        time_saved = entry.avg_original_time_ms
        
        with self._cursor() as cursor:
            # Update cache entry
            cursor.execute("""
                UPDATE response_cache
                SET total_uses = total_uses + 1,
                    last_used = ?,
                    cost_saved_usd = cost_saved_usd + ?
                WHERE id = ?
            """, (datetime.now().isoformat(), cost_saved, entry.id))
            
            # Update daily stats
            cursor.execute("""
                INSERT INTO cache_stats (date, hits, misses, cost_saved_usd, time_saved_ms)
                VALUES (?, 1, 0, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    hits = hits + 1,
                    cost_saved_usd = cost_saved_usd + excluded.cost_saved_usd,
                    time_saved_ms = time_saved_ms + excluded.time_saved_ms
            """, (today, cost_saved, time_saved))
    
    def _record_miss(self):
        """Record a cache miss."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO cache_stats (date, hits, misses, cost_saved_usd, time_saved_ms)
                VALUES (?, 0, 1, 0, 0)
                ON CONFLICT(date) DO UPDATE SET
                    misses = misses + 1
            """, (today,))
    
    # ========================================================================
    # MAINTENANCE
    # ========================================================================
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns count removed."""
        with self._cursor() as cursor:
            cursor.execute("""
                DELETE FROM response_cache
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            removed = cursor.rowcount
        
        # Clean memory cache
        expired_keys = [
            k for k, v in self._memory_cache.items()
            if v.expires_at < datetime.now()
        ]
        for key in expired_keys:
            del self._memory_cache[key]
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")
        
        return removed
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get cache statistics."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self._cursor() as cursor:
            # Daily stats
            cursor.execute("""
                SELECT date, hits, misses, cost_saved_usd, time_saved_ms
                FROM cache_stats
                WHERE date >= ?
                ORDER BY date
            """, (since,))
            daily = [dict(row) for row in cursor.fetchall()]
            
            # Totals
            cursor.execute("""
                SELECT 
                    SUM(hits) as total_hits,
                    SUM(misses) as total_misses,
                    SUM(cost_saved_usd) as total_cost_saved,
                    SUM(time_saved_ms) as total_time_saved
                FROM cache_stats
                WHERE date >= ?
            """, (since,))
            totals = dict(cursor.fetchone())
            
            # Cache size
            cursor.execute("SELECT COUNT(*) as count FROM response_cache")
            cache_size = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM response_cache
                WHERE expires_at >= ?
            """, (datetime.now().isoformat(),))
            valid_entries = cursor.fetchone()["count"]
        
        total_hits = totals.get("total_hits") or 0
        total_misses = totals.get("total_misses") or 0
        total_requests = total_hits + total_misses
        
        return {
            "period_days": days,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate": total_hits / total_requests if total_requests > 0 else 0,
            "total_cost_saved_usd": totals.get("total_cost_saved") or 0,
            "total_time_saved_ms": totals.get("total_time_saved") or 0,
            "cache_size": cache_size,
            "valid_entries": valid_entries,
            "memory_cache_size": len(self._memory_cache),
            "daily_stats": daily
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_cache: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    """Get or create global response cache."""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache


def check_cache(query: str) -> Optional[CachedResponse]:
    """Check for cached response."""
    return get_response_cache().check_cache(query)


def cache_response(
    query: str,
    response: str,
    **kwargs
) -> CachedResponse:
    """Cache a successful response."""
    return get_response_cache().cache_response(query, response, **kwargs)


def invalidate_cache(query: str, reason: str = "correction"):
    """Invalidate a cached response."""
    get_response_cache().invalidate(query, reason)


