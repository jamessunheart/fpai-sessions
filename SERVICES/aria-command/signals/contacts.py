#!/usr/bin/env python3
"""
Contact Management
==================
Tracks relationships and response expectations.

Relationship Types:
- inner_circle: Close friends/family, immediate priority
- professional: Work contacts, high priority
- acquaintance: Known but not close
- unknown: New contacts
"""
import sqlite3
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger("signals.contacts")


@dataclass
class Contact:
    """A known contact."""
    id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    telegram: Optional[str]
    relationship: str  # inner_circle, professional, acquaintance, unknown
    priority_level: int  # 0-4
    response_expectation: str  # immediate, same_day, whenever
    notes: str
    last_contact: Optional[str]


class ContactManager:
    """
    Manages contacts and relationships.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/signals.db"):
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create contact tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                telegram TEXT,
                relationship TEXT DEFAULT 'unknown',
                priority_level INTEGER DEFAULT 2,
                response_expectation TEXT DEFAULT 'whenever',
                notes TEXT,
                last_contact TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_interactions (
                id TEXT PRIMARY KEY,
                contact_id TEXT,
                channel TEXT,
                direction TEXT,
                summary TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            )
        """)
        
        conn.commit()
        conn.close()
    
    def find_contact(self, identifier: str) -> Optional[Contact]:
        """
        Find contact by any identifier (email, phone, telegram, name).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, email, phone, telegram, relationship, priority_level, 
                   response_expectation, notes, last_contact
            FROM contacts
            WHERE email = ? OR phone = ? OR telegram = ? OR name = ?
        """, (identifier, identifier, identifier, identifier))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Contact(
                id=row[0], name=row[1], email=row[2], phone=row[3],
                telegram=row[4], relationship=row[5], priority_level=row[6],
                response_expectation=row[7], notes=row[8], last_contact=row[9]
            )
        return None
    
    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Get contact by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, email, phone, telegram, relationship, priority_level, 
                   response_expectation, notes, last_contact
            FROM contacts WHERE id = ?
        """, (contact_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Contact(
                id=row[0], name=row[1], email=row[2], phone=row[3],
                telegram=row[4], relationship=row[5], priority_level=row[6],
                response_expectation=row[7], notes=row[8], last_contact=row[9]
            )
        return None
    
    def add_contact(
        self,
        name: str,
        email: str = None,
        phone: str = None,
        telegram: str = None,
        relationship: str = "unknown",
        priority_level: int = 2,
        response_expectation: str = "whenever",
        notes: str = ""
    ) -> Contact:
        """Add a new contact."""
        contact_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO contacts (id, name, email, phone, telegram, relationship, 
                                  priority_level, response_expectation, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (contact_id, name, email, phone, telegram, relationship,
              priority_level, response_expectation, notes))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added contact: {name}")
        return Contact(
            id=contact_id, name=name, email=email, phone=phone,
            telegram=telegram, relationship=relationship, priority_level=priority_level,
            response_expectation=response_expectation, notes=notes, last_contact=None
        )
    
    def update_contact(self, contact_id: str, **kwargs):
        """Update contact fields."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['name', 'email', 'phone', 'telegram', 'relationship', 
                       'priority_level', 'response_expectation', 'notes']:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(contact_id)
            cursor.execute(f"""
                UPDATE contacts SET {', '.join(updates)} WHERE id = ?
            """, values)
            conn.commit()
        
        conn.close()
    
    def record_interaction(self, contact_id: str, channel: str, direction: str, summary: str):
        """Record an interaction with a contact."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO contact_interactions (id, contact_id, channel, direction, summary)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), contact_id, channel, direction, summary))
        
        cursor.execute("""
            UPDATE contacts SET last_contact = datetime('now') WHERE id = ?
        """, (contact_id,))
        
        conn.commit()
        conn.close()
    
    def get_inner_circle(self) -> List[Contact]:
        """Get all inner circle contacts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, email, phone, telegram, relationship, priority_level, 
                   response_expectation, notes, last_contact
            FROM contacts WHERE relationship = 'inner_circle'
        """)
        
        contacts = [
            Contact(
                id=r[0], name=r[1], email=r[2], phone=r[3],
                telegram=r[4], relationship=r[5], priority_level=r[6],
                response_expectation=r[7], notes=r[8], last_contact=r[9]
            )
            for r in cursor.fetchall()
        ]
        
        conn.close()
        return contacts
    
    def get_contact_info_for_priority(self, identifier: str) -> Optional[Dict]:
        """Get contact info formatted for priority calculation."""
        contact = self.find_contact(identifier)
        
        if contact:
            return {
                "id": contact.id,
                "name": contact.name,
                "relationship": contact.relationship,
                "priority_level": contact.priority_level,
                "response_expectation": contact.response_expectation
            }
        return None


# Singleton
_manager: Optional[ContactManager] = None

def get_contact_manager() -> ContactManager:
    global _manager
    if _manager is None:
        _manager = ContactManager()
    return _manager


def find_contact(identifier: str) -> Optional[Contact]:
    return get_contact_manager().find_contact(identifier)


def get_contact_info(identifier: str) -> Optional[Dict]:
    return get_contact_manager().get_contact_info_for_priority(identifier)








