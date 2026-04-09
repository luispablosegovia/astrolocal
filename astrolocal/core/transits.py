"""Transit calculations — current planetary positions vs natal chart."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from kerykeion import AstrologicalSubject

from astrolocal.core.chart import (
    ASPECT_NAMES,
    ASPECT_ORBS,
    PLANET_ATTRS,
    PLANET_DISPLAY,
    extract_planet,
)
from astrolocal.models import Aspect, BirthData, ChartData, PlanetPosition

logger = logging.getLogger("astrolocal.core.transits")


def get_current_positions(
    reference_city: str = "Buenos Aires",
    reference_nation: str = "AR",
) -> list[PlanetPosition]:
    """Get current planetary positions using Kerykeion."""
    now = datetime.now()
    transit_subject = AstrologicalSubject(
        name="Transit",
        year=now.year,
        month=now.month,
        day=now.day,
        hour=now.hour,
        minute=now.minute,
        city=reference_city,
        nation=reference_nation,
    )
    return [extract_planet(transit_subject, attr) for attr in PLANET_ATTRS]


def calculate_transit_aspects(
    natal_planets: list[PlanetPosition],
    transit_planets: list[PlanetPosition],
    orb_reduction: float = 0.75,
) -> list[dict[str, Any]]:
    """Calculate aspects between transit planets and natal planets.

    Transit orbs are typically tighter than natal orbs, hence the reduction.
    """
    transit_aspects: list[dict[str, Any]] = []

    for tp in transit_planets:
        for np in natal_planets:
            diff = abs(tp.degree - np.degree)
            if diff > 180:
                diff = 360 - diff

            for target_angle, aspect_name in ASPECT_NAMES.items():
                orb = abs(diff - target_angle)
                max_orb = ASPECT_ORBS.get(aspect_name, 8.0) * orb_reduction
                if orb <= max_orb:
                    transit_aspects.append({
                        "transit_planet": tp.name,
                        "transit_sign": tp.sign,
                        "natal_planet": np.name,
                        "natal_sign": np.sign,
                        "natal_house": np.house,
                        "aspect": aspect_name,
                        "orb": round(orb, 2),
                        "applying": diff < target_angle,
                    })
                    break

    return transit_aspects


def get_daily_transits(
    natal_chart: ChartData,
    reference_city: str = "Buenos Aires",
    reference_nation: str = "AR",
) -> dict[str, Any]:
    """Generate a full transit report for today."""
    current = get_current_positions(reference_city, reference_nation)
    aspects = calculate_transit_aspects(natal_chart.planets, current)

    # Categorize by intensity
    major = [a for a in aspects if a["aspect"] in ("conjunction", "opposition", "square")]
    harmonious = [a for a in aspects if a["aspect"] in ("trine", "sextile")]

    logger.info(
        "Transit report: %d total aspects (%d major, %d harmonious)",
        len(aspects), len(major), len(harmonious),
    )

    return {
        "date": datetime.now().strftime("%d/%m/%Y"),
        "current_positions": [p.model_dump() for p in current],
        "all_aspects": aspects,
        "major_aspects": major,
        "harmonious_aspects": harmonious,
    }
