"""Natal chart generation — wrapper around Kerykeion with security hardening."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from kerykeion import AstrologicalSubject

from astrolocal.models import Aspect, BirthData, ChartData, PlanetPosition

logger = logging.getLogger("astrolocal.core.chart")

# Planets we extract (Kerykeion attribute names)
PLANET_ATTRS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]

PLANET_DISPLAY = {
    "sun": "Sol", "moon": "Luna", "mercury": "Mercurio", "venus": "Venus",
    "mars": "Marte", "jupiter": "Júpiter", "saturn": "Saturno",
    "uranus": "Urano", "neptune": "Neptuno", "pluto": "Plutón",
}

ASPECT_NAMES = {
    0: "conjunction", 60: "sextile", 90: "square",
    120: "trine", 180: "opposition",
}

ASPECT_ORBS = {
    "conjunction": 8.0, "sextile": 6.0, "square": 7.0,
    "trine": 8.0, "opposition": 8.0,
}

ASPECT_DISPLAY = {
    "conjunction": "Conjunción", "sextile": "Sextil", "square": "Cuadratura",
    "trine": "Trígono", "opposition": "Oposición",
}


def create_subject(birth: BirthData) -> AstrologicalSubject:
    """Create a Kerykeion subject from validated birth data.

    BirthData is already validated by Pydantic, so we trust the values here.
    """
    logger.info("Creating chart for subject_id=%s", birth.anonymized_id())

    kwargs: dict[str, Any] = {
        "name": birth.name,
        "year": birth.year,
        "month": birth.month,
        "day": birth.day,
        "hour": birth.hour,
        "minute": birth.minute,
        "city": birth.city,
        "nation": birth.nation,
    }
    if birth.latitude is not None and birth.longitude is not None:
        kwargs["lng"] = birth.longitude
        kwargs["lat"] = birth.latitude

    return AstrologicalSubject(**kwargs)


def extract_planet(subject: AstrologicalSubject, attr: str) -> PlanetPosition:
    """Extract a single planet's data safely."""
    planet_data = getattr(subject, attr, None)
    if planet_data is None:
        raise ValueError(f"Planet attribute '{attr}' not found in subject")

    # Kerykeion returns dicts or objects depending on version
    if isinstance(planet_data, dict):
        return PlanetPosition(
            name=PLANET_DISPLAY.get(attr, attr.capitalize()),
            sign=str(planet_data.get("sign", "Unknown")),
            house=int(planet_data.get("house", 1)),
            degree=float(planet_data.get("position", 0.0)) % 360,
            retrograde=bool(planet_data.get("retrograde", False)),
        )
    else:
        return PlanetPosition(
            name=PLANET_DISPLAY.get(attr, attr.capitalize()),
            sign=str(getattr(planet_data, "sign", "Unknown")),
            house=int(getattr(planet_data, "house", 1)),
            degree=float(getattr(planet_data, "position", 0.0)) % 360,
            retrograde=bool(getattr(planet_data, "retrograde", False)),
        )


def extract_houses(subject: AstrologicalSubject) -> dict[int, dict[str, Any]]:
    """Extract house cusps."""
    houses: dict[int, dict[str, Any]] = {}
    for i in range(1, 13):
        attr = f"{"first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth".split()[i - 1]}_house"
        house_data = getattr(subject, attr, None)
        if house_data is not None:
            if isinstance(house_data, dict):
                houses[i] = {
                    "sign": str(house_data.get("sign", "")),
                    "degree": float(house_data.get("position", 0.0)),
                }
            else:
                houses[i] = {
                    "sign": str(getattr(house_data, "sign", "")),
                    "degree": float(getattr(house_data, "position", 0.0)),
                }
    return houses


def calculate_aspects(planets: list[PlanetPosition]) -> list[Aspect]:
    """Calculate aspects between planets using degree positions."""
    aspects: list[Aspect] = []
    for i, p1 in enumerate(planets):
        for p2 in planets[i + 1 :]:
            diff = abs(p1.degree - p2.degree)
            if diff > 180:
                diff = 360 - diff

            for target_angle, aspect_name in ASPECT_NAMES.items():
                orb = abs(diff - target_angle)
                max_orb = ASPECT_ORBS.get(aspect_name, 8.0)
                if orb <= max_orb:
                    aspects.append(
                        Aspect(
                            planet_a=p1.name,
                            planet_b=p2.name,
                            aspect_type=aspect_name,
                            orb=round(orb, 2),
                            applying=diff < target_angle,
                        )
                    )
                    break  # Only closest aspect per pair
    return aspects


def detect_stelliums(planets: list[PlanetPosition]) -> list[dict[str, Any]]:
    """Detect stelliums (3+ planets in same sign or house)."""
    stelliums: list[dict[str, Any]] = []

    # By sign
    sign_groups: dict[str, list[str]] = {}
    for p in planets:
        sign_groups.setdefault(p.sign, []).append(p.name)
    for sign, names in sign_groups.items():
        if len(names) >= 3:
            stelliums.append({"type": "sign", "location": sign, "planets": names})

    # By house
    house_groups: dict[int, list[str]] = {}
    for p in planets:
        house_groups.setdefault(p.house, []).append(p.name)
    for house, names in house_groups.items():
        if len(names) >= 3:
            stelliums.append({"type": "house", "location": str(house), "planets": names})

    return stelliums


def detect_special_patterns(
    planets: list[PlanetPosition], aspects: list[Aspect]
) -> list[str]:
    """Detect special chart patterns like Grand Trine, T-Square, etc."""
    patterns: list[str] = []

    # Grand Trine: three planets mutually in trine
    trines = [a for a in aspects if a.aspect_type == "trine"]
    trine_partners: dict[str, set[str]] = {}
    for t in trines:
        trine_partners.setdefault(t.planet_a, set()).add(t.planet_b)
        trine_partners.setdefault(t.planet_b, set()).add(t.planet_a)

    checked: set[frozenset[str]] = set()
    for p1, partners1 in trine_partners.items():
        for p2 in partners1:
            for p3 in trine_partners.get(p2, set()):
                if p3 in partners1 and p3 != p1:
                    trio = frozenset({p1, p2, p3})
                    if trio not in checked:
                        checked.add(trio)
                        patterns.append(f"Gran Trígono: {', '.join(sorted(trio))}")

    # T-Square: two planets in opposition, both square a third
    oppositions = [a for a in aspects if a.aspect_type == "opposition"]
    squares = [a for a in aspects if a.aspect_type == "square"]
    square_map: dict[str, set[str]] = {}
    for s in squares:
        square_map.setdefault(s.planet_a, set()).add(s.planet_b)
        square_map.setdefault(s.planet_b, set()).add(s.planet_a)

    for opp in oppositions:
        for apex in square_map.get(opp.planet_a, set()):
            if apex in square_map.get(opp.planet_b, set()):
                patterns.append(
                    f"T-Cuadrada: {opp.planet_a}-{opp.planet_b} con ápice en {apex}"
                )

    return patterns


def generate_chart(birth: BirthData) -> ChartData:
    """Generate a complete chart from validated birth data."""
    subject = create_subject(birth)

    planets = [extract_planet(subject, attr) for attr in PLANET_ATTRS]
    houses = extract_houses(subject)
    aspects = calculate_aspects(planets)
    stelliums = detect_stelliums(planets)
    special = detect_special_patterns(planets, aspects)

    asc_sign = houses.get(1, {}).get("sign", "")
    mc_sign = houses.get(10, {}).get("sign", "")

    chart = ChartData(
        birth_data=birth,
        planets=planets,
        houses=houses,
        aspects=aspects,
        ascendant_sign=asc_sign,
        mc_sign=mc_sign,
        stelliums=stelliums,
        special_patterns=special,
    )

    logger.info(
        "Chart generated: %d planets, %d aspects, %d stelliums, %d patterns",
        len(planets), len(aspects), len(stelliums), len(special),
    )
    return chart


def generate_svg(birth: BirthData) -> str:
    """Generate an SVG chart image."""
    subject = create_subject(birth)
    try:
        from kerykeion import AstrologicalChart
        chart_obj = AstrologicalChart(subject)
        return chart_obj.makeSVG()
    except ImportError:
        logger.warning("AstrologicalChart not available, SVG generation skipped")
        return ""
