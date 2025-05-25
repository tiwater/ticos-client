"""Pytest configuration and fixtures for Ticos Client tests."""

import asyncio
import os
import tempfile
from typing import Generator

import pytest

from ticos_client import TicosClient


@pytest.fixture(scope="function")
def temp_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    yield f"sqlite:///{db_path}"

    # Clean up
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
async def ticos_client(temp_db: str) -> Generator[TicosClient, None, None]:
    """Create a TicosClient instance for testing."""
    from ticos_client.storage import SQLiteStorageService

    # Initialize client with test settings
    client = TicosClient(port=9999)

    # Enable local storage with test database
    storage = SQLiteStorageService(database_url=temp_db)
    client.enable_local_storage(storage)

    # Start the server
    if not client.start():
        pytest.fail("Failed to start TicosClient")

    yield client

    # Clean up
    client.stop()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
