"""Tests for Pydantic model validation — the primary security boundary."""

import pytest
from pydantic import ValidationError

from astrolocal.models import BirthData


class TestBirthDataValidation:
    """Ensure all user input is properly validated and sanitized."""

    def test_valid_input(self):
        b = BirthData(
            name="Juan", year=1990, month=3, day=15,
            hour=14, minute=30, city="Buenos Aires", nation="AR",
        )
        assert b.name == "Juan"
        assert b.nation == "AR"

    def test_name_sanitization_strips_control_chars(self):
        b = BirthData(
            name="Juan\x00\x01Carlos", year=1990, month=1, day=1,
            hour=0, minute=0, city="Test", nation="AR",
        )
        assert b.name == "JuanCarlos"

    def test_name_sanitization_strips_excess_whitespace(self):
        b = BirthData(
            name="  Juan    Carlos  ", year=1990, month=1, day=1,
            hour=0, minute=0, city="Test", nation="AR",
        )
        assert b.name == "Juan Carlos"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="", year=1990, month=1, day=1,
                hour=0, minute=0, city="Test", nation="AR",
            )

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="A" * 101, year=1990, month=1, day=1,
                hour=0, minute=0, city="Test", nation="AR",
            )

    def test_invalid_date_feb_30(self):
        with pytest.raises(ValidationError, match="Invalid date"):
            BirthData(
                name="Test", year=1990, month=2, day=30,
                hour=0, minute=0, city="Test", nation="AR",
            )

    def test_year_too_low(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="Test", year=1799, month=1, day=1,
                hour=0, minute=0, city="Test", nation="AR",
            )

    def test_year_too_high(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="Test", year=2101, month=1, day=1,
                hour=0, minute=0, city="Test", nation="AR",
            )

    def test_invalid_nation_format(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="Test", year=1990, month=1, day=1,
                hour=0, minute=0, city="Test", nation="Argentina",
            )

    def test_nation_must_be_uppercase(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="Test", year=1990, month=1, day=1,
                hour=0, minute=0, city="Test", nation="ar",
            )

    def test_hour_out_of_range(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="Test", year=1990, month=1, day=1,
                hour=25, minute=0, city="Test", nation="AR",
            )

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="Test", year=1990, month=1, day=1,
                hour=0, minute=0, city="Test", nation="AR",
                latitude=91.0,
            )

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            BirthData(
                name="Test", year=1990, month=1, day=1,
                hour=0, minute=0, city="Test", nation="AR",
                longitude=-181.0,
            )

    def test_anonymized_id_is_deterministic(self):
        b = BirthData(
            name="Test", year=1990, month=1, day=1,
            hour=0, minute=0, city="Test", nation="AR",
        )
        assert b.anonymized_id() == b.anonymized_id()
        assert len(b.anonymized_id()) == 12

    def test_anonymized_id_no_pii(self):
        b = BirthData(
            name="Juan Secret", year=1990, month=3, day=15,
            hour=14, minute=30, city="Buenos Aires", nation="AR",
        )
        aid = b.anonymized_id()
        assert "Juan" not in aid
        assert "1990" not in aid

    def test_city_with_sql_injection_attempt(self):
        """SQL injection in city is harmless because we use parameterized queries,
        but the value should still be sanitized of control chars."""
        b = BirthData(
            name="Test", year=1990, month=1, day=1,
            hour=0, minute=0,
            city="'; DROP TABLE profiles; --",
            nation="AR",
        )
        # The city is stored as-is (minus control chars) because
        # parameterized queries prevent injection.
        assert "DROP TABLE" in b.city  # It's just a string, not executed
