"""Tests for database layer — verifying parameterized queries and constraints."""

import pytest

from astrolocal.models import BirthData, ReadingType
from astrolocal.storage.database import Database


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db = Database(tmp_path / "test.db")
    await db.connect()
    yield db
    await db.close()


@pytest.mark.asyncio
async def test_add_and_retrieve_profile(db):
    birth = BirthData(
        name="Test User", year=1990, month=3, day=15,
        hour=14, minute=30, city="Buenos Aires", nation="AR",
    )
    pid = await db.add_profile(birth)
    assert pid > 0

    profile = await db.get_profile(pid)
    assert profile is not None
    assert profile.birth_data.name == "Test User"
    assert profile.birth_data.city == "Buenos Aires"


@pytest.mark.asyncio
async def test_get_profile_by_name(db):
    birth = BirthData(
        name="María", year=1985, month=7, day=22,
        hour=8, minute=0, city="Córdoba", nation="AR",
    )
    await db.add_profile(birth)
    profile = await db.get_profile_by_name("maría")  # case insensitive
    assert profile is not None
    assert profile.birth_data.name == "María"


@pytest.mark.asyncio
async def test_profile_not_found(db):
    profile = await db.get_profile(9999)
    assert profile is None


@pytest.mark.asyncio
async def test_save_and_retrieve_reading(db):
    birth = BirthData(
        name="Test", year=2000, month=1, day=1,
        hour=12, minute=0, city="London", nation="GB",
    )
    pid = await db.add_profile(birth)
    rid = await db.save_reading(
        profile_id=pid,
        reading_type=ReadingType.NATAL,
        raw_data={"sun": "Capricorn"},
        interpretation="Test interpretation",
        model_used="test-model",
    )
    assert rid > 0

    readings = await db.get_readings(pid)
    assert len(readings) == 1
    assert readings[0].interpretation == "Test interpretation"


@pytest.mark.asyncio
async def test_delete_profile_cascades(db):
    birth = BirthData(
        name="ToDelete", year=1990, month=1, day=1,
        hour=0, minute=0, city="Test", nation="AR",
    )
    pid = await db.add_profile(birth)
    await db.save_reading(pid, ReadingType.NATAL, {}, "test", "model")

    deleted = await db.delete_profile(pid)
    assert deleted is True

    readings = await db.get_readings(pid)
    assert len(readings) == 0


@pytest.mark.asyncio
async def test_sql_injection_in_name_is_harmless(db):
    """Parameterized queries make injection impossible."""
    birth = BirthData(
        name="'; DROP TABLE profiles; --", year=1990, month=1, day=1,
        hour=0, minute=0, city="Test", nation="AR",
    )
    pid = await db.add_profile(birth)

    # Table still exists and profile was stored as-is
    profiles = await db.list_profiles()
    assert any(p.birth_data.name == "'; DROP TABLE profiles; --" for p in profiles)
