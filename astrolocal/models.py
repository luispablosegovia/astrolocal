"""Validated domain models. All user input passes through these before use."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ReadingType(str, Enum):
    NATAL = "natal"
    TRANSIT = "transit"
    SYNASTRY = "synastry"
    SOLAR_RETURN = "solar_return"


class BirthData(BaseModel):
    """Validated birth data. This is the primary input boundary.

    Security notes:
    - All fields are strictly typed and bounded.
    - Name is sanitized to prevent injection.
    - Coordinates are validated to real geographic ranges.
    - Timezone is not trusted from user; computed from coordinates.
    """

    name: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1800, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)
    city: str = Field(..., min_length=1, max_length=200)
    nation: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Remove control characters and excessive whitespace."""
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        if not sanitized:
            raise ValueError("Name cannot be empty after sanitization")
        return sanitized

    @field_validator("city")
    @classmethod
    def sanitize_city(cls, v: str) -> str:
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        if not sanitized:
            raise ValueError("City cannot be empty after sanitization")
        return sanitized

    @model_validator(mode="after")
    def validate_date(self) -> BirthData:
        """Ensure the date is actually valid (e.g., no Feb 30)."""
        try:
            datetime(self.year, self.month, self.day, self.hour, self.minute)
        except ValueError as e:
            raise ValueError(f"Invalid date/time combination: {e}") from e
        return self

    def anonymized_id(self) -> str:
        """Generate a non-reversible ID for logging (no PII in logs)."""
        raw = f"{self.name}:{self.year}-{self.month}-{self.day}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def display_date(self) -> str:
        return f"{self.day:02d}/{self.month:02d}/{self.year}"

    def display_time(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"


class PlanetPosition(BaseModel):
    """A single planet's position in the chart."""

    name: str
    sign: str
    house: int = Field(ge=1, le=12)
    degree: float = Field(ge=0.0, lt=360.0)
    retrograde: bool = False


class Aspect(BaseModel):
    """An aspect between two planets."""

    planet_a: str
    planet_b: str
    aspect_type: str  # "conjunction", "opposition", "trine", etc.
    orb: float = Field(ge=0.0, le=15.0)
    applying: bool = False


class ChartData(BaseModel):
    """Structured chart data extracted from Kerykeion."""

    birth_data: BirthData
    planets: list[PlanetPosition] = Field(default_factory=list)
    houses: dict[int, dict[str, Any]] = Field(default_factory=dict)
    aspects: list[Aspect] = Field(default_factory=list)
    ascendant_sign: str = ""
    mc_sign: str = ""
    stelliums: list[dict[str, Any]] = Field(default_factory=list)
    special_patterns: list[str] = Field(default_factory=list)


class ReadingRecord(BaseModel):
    """A saved reading for persistence."""

    id: int | None = None
    profile_id: int
    reading_type: ReadingType
    raw_data: dict[str, Any]
    interpretation: str
    model_used: str
    created_at: datetime = Field(default_factory=datetime.now)


class ProfileRecord(BaseModel):
    """A saved user profile."""

    id: int | None = None
    birth_data: BirthData
    created_at: datetime = Field(default_factory=datetime.now)
