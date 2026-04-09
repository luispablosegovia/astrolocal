"""Synastry — compatibility analysis between two charts."""

from __future__ import annotations

import logging
from typing import Any

from astrolocal.core.chart import ASPECT_NAMES, ASPECT_ORBS
from astrolocal.models import ChartData, PlanetPosition

logger = logging.getLogger("astrolocal.core.synastry")


def calculate_synastry_aspects(
    chart_a: ChartData,
    chart_b: ChartData,
) -> list[dict[str, Any]]:
    """Calculate inter-chart aspects between two people."""
    aspects: list[dict[str, Any]] = []

    for pa in chart_a.planets:
        for pb in chart_b.planets:
            diff = abs(pa.degree - pb.degree)
            if diff > 180:
                diff = 360 - diff

            for target_angle, aspect_name in ASPECT_NAMES.items():
                orb = abs(diff - target_angle)
                max_orb = ASPECT_ORBS.get(aspect_name, 8.0)
                if orb <= max_orb:
                    aspects.append({
                        "person_a_planet": pa.name,
                        "person_a_sign": pa.sign,
                        "person_b_planet": pb.name,
                        "person_b_sign": pb.sign,
                        "aspect": aspect_name,
                        "orb": round(orb, 2),
                    })
                    break

    return aspects


def analyze_synastry(chart_a: ChartData, chart_b: ChartData) -> dict[str, Any]:
    """Full synastry analysis between two charts."""
    aspects = calculate_synastry_aspects(chart_a, chart_b)

    # Categorize
    harmonious = [a for a in aspects if a["aspect"] in ("trine", "sextile", "conjunction")]
    challenging = [a for a in aspects if a["aspect"] in ("square", "opposition")]

    # Element compatibility
    element_a = _dominant_element(chart_a.planets)
    element_b = _dominant_element(chart_b.planets)

    logger.info(
        "Synastry: %d aspects (%d harmonious, %d challenging)",
        len(aspects), len(harmonious), len(challenging),
    )

    return {
        "person_a": chart_a.birth_data.name,
        "person_b": chart_b.birth_data.name,
        "all_aspects": aspects,
        "harmonious_aspects": harmonious,
        "challenging_aspects": challenging,
        "element_compatibility": {
            "person_a_dominant": element_a,
            "person_b_dominant": element_b,
        },
    }


SIGN_ELEMENTS = {
    "Ari": "fuego", "Tau": "tierra", "Gem": "aire", "Can": "agua",
    "Leo": "fuego", "Vir": "tierra", "Lib": "aire", "Sco": "agua",
    "Sag": "fuego", "Cap": "tierra", "Aqu": "aire", "Pis": "agua",
    # Full names (Kerykeion may return either)
    "Aries": "fuego", "Taurus": "tierra", "Gemini": "aire", "Cancer": "agua",
    "Leo": "fuego", "Virgo": "tierra", "Libra": "aire", "Scorpio": "agua",
    "Sagittarius": "fuego", "Capricorn": "tierra", "Aquarius": "aire", "Pisces": "agua",
}


def _dominant_element(planets: list[PlanetPosition]) -> str:
    from collections import Counter

    elements = [SIGN_ELEMENTS.get(p.sign, "unknown") for p in planets]
    counts = Counter(elements)
    if counts:
        return counts.most_common(1)[0][0]
    return "unknown"
