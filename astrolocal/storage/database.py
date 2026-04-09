"""SQLite storage with security hardening.

Security features:
- All queries use parameterized statements (no string interpolation)
- WAL mode for safe concurrent reads
- Foreign keys enforced
- Database path validated against traversal
- Automatic schema migrations
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from astrolocal.config import _safe_resolve
from astrolocal.models import BirthData, ProfileRecord, ReadingRecord, ReadingType

logger = logging.getLogger("astrolocal.storage.database")

SCHEMA_VERSION = 1

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    birth_year INTEGER NOT NULL,
    birth_month INTEGER NOT NULL,
    birth_day INTEGER NOT NULL,
    birth_hour INTEGER NOT NULL,
    birth_minute INTEGER NOT NULL,
    city TEXT NOT NULL,
    nation TEXT NOT NULL CHECK(length(nation) = 2),
    latitude REAL,
    longitude REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    reading_type TEXT NOT NULL CHECK(reading_type IN ('natal','transit','synastry','solar_return')),
    raw_data TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    model_used TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_readings_profile ON readings(profile_id);
CREATE INDEX IF NOT EXISTS idx_readings_type ON readings(reading_type);
CREATE INDEX IF NOT EXISTS idx_readings_created ON readings(created_at DESC);
"""


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, db_path: str | Path):
        self._path = _safe_resolve(db_path)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open database connection with security settings."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(str(self._path))
        self._db.row_factory = aiosqlite.Row

        # Security & performance pragmas
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.execute("PRAGMA secure_delete=ON")
        await self._db.execute("PRAGMA busy_timeout=5000")

        await self._initialize_schema()
        logger.info("Database connected: %s", self._path.name)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def _initialize_schema(self) -> None:
        assert self._db is not None
        await self._db.executescript(SCHEMA_SQL)
        # Track schema version
        await self._db.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        await self._db.commit()

    # ---- Profiles ----

    async def add_profile(self, birth: BirthData) -> int:
        """Insert a profile. Returns the new profile ID."""
        assert self._db is not None
        cursor = await self._db.execute(
            """INSERT INTO profiles
               (name, birth_year, birth_month, birth_day, birth_hour, birth_minute,
                city, nation, latitude, longitude)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                birth.name, birth.year, birth.month, birth.day,
                birth.hour, birth.minute, birth.city, birth.nation,
                birth.latitude, birth.longitude,
            ),
        )
        await self._db.commit()
        assert cursor.lastrowid is not None
        logger.info("Profile added: id=%d", cursor.lastrowid)
        return cursor.lastrowid

    async def get_profile(self, profile_id: int) -> ProfileRecord | None:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM profiles WHERE id = ?", (profile_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    async def get_profile_by_name(self, name: str) -> ProfileRecord | None:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM profiles WHERE LOWER(name) = LOWER(?) LIMIT 1", (name,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    async def list_profiles(self, limit: int = 50) -> list[ProfileRecord]:
        assert self._db is not None
        limit = min(max(1, limit), 200)  # Clamp
        cursor = await self._db.execute(
            "SELECT * FROM profiles ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_profile(r) for r in rows]

    async def delete_profile(self, profile_id: int) -> bool:
        """Delete a profile and cascade to readings."""
        assert self._db is not None
        cursor = await self._db.execute(
            "DELETE FROM profiles WHERE id = ?", (profile_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    # ---- Readings ----

    async def save_reading(
        self,
        profile_id: int,
        reading_type: ReadingType,
        raw_data: dict[str, Any],
        interpretation: str,
        model_used: str,
    ) -> int:
        assert self._db is not None
        cursor = await self._db.execute(
            """INSERT INTO readings
               (profile_id, reading_type, raw_data, interpretation, model_used)
               VALUES (?, ?, ?, ?, ?)""",
            (
                profile_id,
                reading_type.value,
                json.dumps(raw_data, default=str, ensure_ascii=False),
                interpretation,
                model_used,
            ),
        )
        await self._db.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    async def get_readings(
        self,
        profile_id: int,
        reading_type: ReadingType | None = None,
        limit: int = 20,
    ) -> list[ReadingRecord]:
        assert self._db is not None
        limit = min(max(1, limit), 100)

        if reading_type:
            cursor = await self._db.execute(
                """SELECT * FROM readings
                   WHERE profile_id = ? AND reading_type = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (profile_id, reading_type.value, limit),
            )
        else:
            cursor = await self._db.execute(
                """SELECT * FROM readings
                   WHERE profile_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (profile_id, limit),
            )

        rows = await cursor.fetchall()
        return [self._row_to_reading(r) for r in rows]

    # ---- Helpers ----

    @staticmethod
    def _row_to_profile(row: aiosqlite.Row) -> ProfileRecord:
        return ProfileRecord(
            id=row["id"],
            birth_data=BirthData(
                name=row["name"],
                year=row["birth_year"],
                month=row["birth_month"],
                day=row["birth_day"],
                hour=row["birth_hour"],
                minute=row["birth_minute"],
                city=row["city"],
                nation=row["nation"],
                latitude=row["latitude"],
                longitude=row["longitude"],
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_reading(row: aiosqlite.Row) -> ReadingRecord:
        return ReadingRecord(
            id=row["id"],
            profile_id=row["profile_id"],
            reading_type=ReadingType(row["reading_type"]),
            raw_data=json.loads(row["raw_data"]),
            interpretation=row["interpretation"],
            model_used=row["model_used"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
