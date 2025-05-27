import json
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
from abc import ABC, abstractmethod
from .models import Message, Memory, MessageRole, MemoryType

logger = logging.getLogger(__name__)


class StorageService(ABC):
    """Interface defining storage operations for messages and memories."""

    @abstractmethod
    def set_store_root_dir(self, tf_root_dir: str) -> None:
        """
        Set the root directory for storage.

        Args:
            tf_root_dir: The root directory of the TF card
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the storage service."""
        pass

    @abstractmethod
    def save_message(self, message: Message) -> bool:
        """Save a message to storage."""
        pass

    @abstractmethod
    def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message from storage."""
        pass

    @abstractmethod
    def update_message(self, message_id: str, message: Message) -> bool:
        """Update a message in storage."""
        pass

    @abstractmethod
    def delete_message(self, message_id: str) -> bool:
        """Delete a message from storage."""
        pass

    @abstractmethod
    def get_messages(
        self, offset: int = 0, limit: int = 100, desc: bool = True
    ) -> List[Message]:
        """Get a list of messages from storage."""
        pass

    @abstractmethod
    def get_message_by_item_id(self, item_id: str) -> Optional[Message]:
        """Get a message by its item_id."""
        pass

    @abstractmethod
    def save_memory(self, memory: Memory) -> bool:
        """Save a memory to storage."""
        pass

    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory from storage."""
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from storage."""
        pass

    def get_latest_memory(self) -> Optional[Dict[str, Any]]:
        """Get the most recent memory"""
        raise NotImplementedError

    def get_memories(
        self, offset: int = 0, limit: int = 10, desc: bool = True
    ) -> List[Dict[str, Any]]:
        """Get memories with pagination"""
        raise NotImplementedError


class SQLiteStorageService(StorageService):
    """SQLite implementation of StorageService"""

    # Current database schema version
    CURRENT_DB_VERSION = 1

    def __init__(self):
        """
        Initialize SQLiteStorageService.
        """
        self.db_path = None
        self.store_root_dir = None

    def set_store_root_dir(self, tf_root_dir: str) -> None:
        """
        Set the root directory for storage.

        Args:
            tf_root_dir: The root directory of the TF card
        """
        self.store_root_dir = tf_root_dir

    def initialize(self) -> None:
        """Initialize the storage service."""
        try:
            # Create config directory if it doesn't exist
            if self.store_root_dir:
                config_dir = Path(self.store_root_dir) / ".config" / "ticos"
            else:
                config_dir = Path.home() / ".config" / "ticos"

            config_dir.mkdir(parents=True, exist_ok=True)

            # Set database path
            self.db_path = str(config_dir / "ticos.db")
            
            # Check if database exists
            db_exists = Path(self.db_path).exists()
            
            # Initialize database tables
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create version table if it doesn't exist
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS db_version (
                        id INTEGER PRIMARY KEY,
                        version INTEGER NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """
                )
                
                # Check current database version
                cursor.execute("SELECT version FROM db_version ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                current_version = row[0] if row else 0
                
                # If database is new or no version info, create latest schema directly
                if not db_exists:
                    logger.info(f"Creating new database with latest schema (version {self.CURRENT_DB_VERSION})")
                    self._create_latest_schema(conn)
                    
                    # Insert version record
                    cursor.execute(
                        """
                        INSERT INTO db_version (version, updated_at)
                        VALUES (?, ?)
                        """,
                        (self.CURRENT_DB_VERSION, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    )
                    conn.commit()
                # If database exists but needs upgrading, apply incremental migrations
                elif current_version < self.CURRENT_DB_VERSION:
                    logger.info(f"Upgrading database from version {current_version} to {self.CURRENT_DB_VERSION}")
                    self._migrate_database(conn, current_version)
                    
                    # Update database version
                    cursor.execute(
                        """
                        INSERT INTO db_version (version, updated_at)
                        VALUES (?, ?)
                        """,
                        (self.CURRENT_DB_VERSION, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    )
                    conn.commit()
                    
                logger.info(f"Storage initialized successfully (DB version: {self.CURRENT_DB_VERSION})")
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            raise

    def _create_latest_schema(self, conn):
        """Create the latest database schema from scratch"""
        cursor = conn.cursor()
        
        # Create messages table with the latest schema
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                item_id TEXT,
                user_id TEXT DEFAULT 'nobody',
                datetime TEXT NOT NULL
            )
            """
        )
        logger.info("Created messages table with latest schema")
        
        # Create memories table with the latest schema
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                user_id TEXT DEFAULT 'nobody',
                datetime TEXT NOT NULL
            )
            """
        )
        logger.info("Created memories table with latest schema")
        
        conn.commit()
    
    def _migrate_database(self, conn, current_version):
        """Perform incremental database migrations based on current version"""
        cursor = conn.cursor()
        
        # Apply migrations sequentially
        # Migration from version 0 to 1 (add user_id field)
        if current_version < 1:
            logger.info("Migrating database from version 0 to 1")
            
            # Add user_id column to messages table
            cursor.execute("PRAGMA table_info(messages)")
            columns = [column[1] for column in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE messages ADD COLUMN user_id TEXT DEFAULT 'nobody'")
                logger.info("Added user_id column to messages table")
            
            # Add user_id column to memories table
            cursor.execute("PRAGMA table_info(memories)")
            columns = [column[1] for column in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE memories ADD COLUMN user_id TEXT DEFAULT 'nobody'")
                logger.info("Added user_id column to memories table")
            
            conn.commit()
            current_version = 1
        
        # Future migrations can be added here
        # Migration from version 1 to 2
        # if current_version < 2:
        #     logger.info("Migrating database from version 1 to 2")
        #     # Add migration code here
        #     conn.commit()
        #     current_version = 2
        
        # Migration from version 2 to 3
        # if current_version < 3:
        #     logger.info("Migrating database from version 2 to 3")
        #     # Add migration code here
        #     conn.commit()
        #     current_version = 3
    
    def _get_connection(self):
        """Get a new database connection"""
        return sqlite3.connect(self.db_path)

    def save_message(self, message: Message) -> bool:
        """Save a message to storage"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO messages (id, role, content, item_id, user_id, datetime)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.id,
                        message.role.value,
                        message.content,
                        message.item_id,
                        message.user_id,
                        message.datetime,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False

    def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, role, content, item_id, user_id, datetime FROM messages WHERE id = ?",
                    (message_id,),
                )
                row = cursor.fetchone()
                if row:
                    return Message(
                        id=row[0],
                        role=MessageRole(row[1]),
                        content=row[2],
                        item_id=row[3],
                        user_id=row[4],
                        datetime=row[5],
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None

    def update_message(self, message_id: str, message: Message) -> bool:
        """Update an existing message"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE messages SET role = ?, content = ?, item_id = ?, user_id = ?, datetime = ?
                    WHERE id = ?
                    """,
                    (
                        message.role.value,
                        message.content,
                        message.item_id,
                        message.user_id,
                        message.datetime,
                        message_id,
                    ),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update message: {e}")
            return False

    def delete_message(self, message_id: str) -> bool:
        """Delete a message by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    def get_messages(
        self, offset: int = 0, limit: int = 10, desc: bool = True
    ) -> List[Message]:
        """Get messages with pagination"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                order = "DESC" if desc else "ASC"
                cursor.execute(
                    f"SELECT id, role, content, item_id, user_id, datetime FROM messages ORDER BY datetime {order} LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                return [
                    Message(
                        id=row[0],
                        role=MessageRole(row[1]),
                        content=row[2],
                        item_id=row[3],
                        user_id=row[4],
                        datetime=row[5],
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    def get_message_by_item_id(self, item_id: str) -> Optional[Message]:
        """Get a message by its item_id"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, role, content, item_id, user_id, datetime FROM messages WHERE item_id = ?",
                    (item_id,),
                )
                row = cursor.fetchone()
                if row:
                    return Message(
                        id=row[0],
                        role=MessageRole(row[1]),
                        content=row[2],
                        item_id=row[3],
                        user_id=row[4],
                        datetime=row[5],
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get message by item_id: {e}")
            return None

    def save_memory(self, memory: Memory) -> bool:
        """Save a memory to storage"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO memories (type, content, user_id, datetime)
                    VALUES (?, ?, ?, ?)
                    """,
                    (memory.type.value, memory.content, memory.user_id, memory.datetime),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False

    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, type, content, user_id, datetime FROM memories WHERE id = ?",
                    (memory_id,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2],
                        "user_id": row[3],
                        "datetime": row[4],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get memory: {e}")
            return None

    def update_memory(self, memory_id: int, memory: Memory) -> bool:
        """Update an existing memory"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE memories SET type = ?, content = ?, user_id = ?, datetime = ?
                    WHERE id = ?
                    """,
                    (memory.type.value, memory.content, memory.user_id, memory.datetime, memory_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    def get_latest_memory(self) -> Optional[Dict[str, Any]]:
        """Get the most recent memory"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, type, content, user_id, datetime FROM memories ORDER BY datetime DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2],
                        "user_id": row[3],
                        "datetime": row[4],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get latest memory: {e}")
            return None

    def get_memories(
        self, offset: int = 0, limit: int = 10, desc: bool = True
    ) -> List[Dict[str, Any]]:
        """Get memories with pagination"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                order = "DESC" if desc else "ASC"
                cursor.execute(
                    f"SELECT id, type, content, user_id, datetime FROM memories ORDER BY datetime {order} LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                return [
                    {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2],
                        "user_id": row[3],
                        "datetime": row[4],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []
