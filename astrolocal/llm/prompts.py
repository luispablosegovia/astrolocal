"""Prompt templates for astrological interpretations.

Security: All dynamic values are pre-validated by Pydantic models
before reaching these templates. No raw user input is interpolated.
"""

from __future__ import annotations

from typing import Any

from astrolocal.core.chart import ASPECT_DISPLAY
from astrolocal.models import ChartData

SYSTEM_PROMPT = """\
Sos un astrólogo profesional con décadas de experiencia en astrología humanista.
Tu estilo es profundo pero accesible: explicás con claridad, sin jerga innecesaria,
pero sin simplificar de más. Hablás en español rioplatense (argentino).
No hacés predicciones deterministas. Presentás la carta como un mapa de
potencialidades, no como un destino fijo. Sos empático, respetuoso y honesto.\
"""

NATAL_CHART_TEMPLATE = """\
## Carta Natal de {name}
Nacimiento: {date} a las {time} en {city}, {country}.

### Posiciones Planetarias
{planet_positions}

### Casas
{houses}

### Aspectos Principales
{aspects}

### Configuraciones Especiales
{special}

## Tarea

Generá una interpretación completa y personalizada de esta carta natal.

Estructura:
1. **Esencia Solar** — Sol en {sun_sign} en Casa {sun_house}.
   Integrá casa, aspectos y el contexto general del chart.

2. **Mundo Emocional** — Luna en {moon_sign} en Casa {moon_house}.
   Cómo procesa emociones, qué necesita para sentirse seguro/a.

3. **Máscara y Primera Impresión** — Ascendente en {asc_sign}.
   Cómo lo/la perciben vs. quién es realmente.

4. **Tensiones y Desafíos** — Cuadraturas y oposiciones principales.
   Presentálas como áreas de crecimiento, no como "problemas".

5. **Dones y Flujos** — Trígonos y sextiles relevantes.

6. **Propósito** — Medio Cielo en {mc_sign} y dirección evolutiva.

7. **Síntesis** — El tema central de esta carta en un párrafo integrador.

Sé específico. Usá las posiciones exactas. Si hay stelliums, Gran Trígono,
T-Cuadrada u otras configuraciones, explicá qué significan para esta persona.\
"""

TRANSIT_TEMPLATE = """\
## Tránsitos para {name} — {date}

### Carta Natal (resumen)
{natal_summary}

### Posiciones Planetarias Actuales
{current_positions}

### Aspectos Tránsito-Natal
{transit_aspects}

## Tarea

Generá un reporte de tránsitos para hoy. Estructura:

1. **Clima general del día** — Resumen de la energía predominante.

2. **Tránsitos más importantes** — Los aspectos más significativos
   y cómo afectan a esta persona en particular (no genéricos).

3. **Áreas de atención** — Cuadraturas y oposiciones activas.

4. **Oportunidades** — Trígonos y sextiles que se pueden aprovechar.

5. **Consejo del día** — Un mensaje práctico y concreto.

Sé específico para ESTA carta natal. No des horóscopo genérico.\
"""

SYNASTRY_TEMPLATE = """\
## Sinastría: {name_a} y {name_b}

### Carta de {name_a} (resumen)
{summary_a}

### Carta de {name_b} (resumen)
{summary_b}

### Aspectos Inter-Carta
{synastry_aspects}

### Compatibilidad Elemental
{element_compat}

## Tarea

Analizá la compatibilidad entre estas dos personas. Estructura:

1. **Primera impresión** — Cómo se perciben mutuamente (Ascendentes).

2. **Conexión emocional** — Interacción entre Lunas y Venus.

3. **Comunicación** — Mercurios y aspectos relevantes.

4. **Atracción y pasión** — Venus-Marte y aspectos afines.

5. **Desafíos** — Cuadraturas y oposiciones inter-carta.

6. **Potencial de crecimiento** — Qué puede aprender cada uno del otro.

7. **Síntesis** — ¿Qué tipo de relación favorece esta sinastría?

Sé honesto y equilibrado. No idealices ni dramatices.\
"""


def format_planets(chart: ChartData) -> str:
    lines: list[str] = []
    for p in chart.planets:
        retro = " (R)" if p.retrograde else ""
        lines.append(f"- {p.name}: {p.sign} {p.degree:.1f}°, Casa {p.house}{retro}")
    return "\n".join(lines)


def format_houses(chart: ChartData) -> str:
    lines: list[str] = []
    for num in sorted(chart.houses.keys()):
        h = chart.houses[num]
        lines.append(f"- Casa {num}: {h.get('sign', '?')} {h.get('degree', 0):.1f}°")
    return "\n".join(lines)


def format_aspects(chart: ChartData) -> str:
    lines: list[str] = []
    for a in chart.aspects:
        display = ASPECT_DISPLAY.get(a.aspect_type, a.aspect_type)
        lines.append(f"- {a.planet_a} {display} {a.planet_b} (orbe: {a.orb}°)")
    return "\n".join(lines) if lines else "Ningún aspecto mayor detectado."


def format_special(chart: ChartData) -> str:
    parts: list[str] = []
    if chart.stelliums:
        for s in chart.stelliums:
            planets = ", ".join(s["planets"])
            parts.append(f"- Stellium en {s['type']} {s['location']}: {planets}")
    if chart.special_patterns:
        for p in chart.special_patterns:
            parts.append(f"- {p}")
    return "\n".join(parts) if parts else "Sin configuraciones especiales detectadas."


def _find_planet(chart: ChartData, name: str) -> dict[str, Any]:
    for p in chart.planets:
        if p.name.lower() == name.lower():
            return {"sign": p.sign, "house": p.house}
    return {"sign": "?", "house": "?"}


def build_natal_prompt(chart: ChartData) -> str:
    sun = _find_planet(chart, "Sol")
    moon = _find_planet(chart, "Luna")
    return NATAL_CHART_TEMPLATE.format(
        name=chart.birth_data.name,
        date=chart.birth_data.display_date(),
        time=chart.birth_data.display_time(),
        city=chart.birth_data.city,
        country=chart.birth_data.nation,
        planet_positions=format_planets(chart),
        houses=format_houses(chart),
        aspects=format_aspects(chart),
        special=format_special(chart),
        sun_sign=sun["sign"],
        sun_house=sun["house"],
        moon_sign=moon["sign"],
        moon_house=moon["house"],
        asc_sign=chart.ascendant_sign,
        mc_sign=chart.mc_sign,
    )


def build_transit_prompt(chart: ChartData, transit_data: dict[str, Any]) -> str:
    current_lines: list[str] = []
    for p in transit_data.get("current_positions", []):
        current_lines.append(f"- {p['name']}: {p['sign']} {p['degree']:.1f}°")

    aspect_lines: list[str] = []
    for a in transit_data.get("all_aspects", []):
        display = ASPECT_DISPLAY.get(a["aspect"], a["aspect"])
        aspect_lines.append(
            f"- {a['transit_planet']} en {a['transit_sign']} "
            f"{display} {a['natal_planet']} natal en {a['natal_sign']} "
            f"(Casa {a['natal_house']}, orbe: {a['orb']}°)"
        )

    return TRANSIT_TEMPLATE.format(
        name=chart.birth_data.name,
        date=transit_data.get("date", "hoy"),
        natal_summary=format_planets(chart),
        current_positions="\n".join(current_lines),
        transit_aspects="\n".join(aspect_lines) if aspect_lines else "Sin aspectos mayores hoy.",
    )


def build_synastry_prompt(
    chart_a: ChartData,
    chart_b: ChartData,
    synastry_data: dict[str, Any],
) -> str:
    aspect_lines: list[str] = []
    for a in synastry_data.get("all_aspects", []):
        display = ASPECT_DISPLAY.get(a["aspect"], a["aspect"])
        aspect_lines.append(
            f"- {a['person_a_planet']} de {chart_a.birth_data.name} "
            f"{display} {a['person_b_planet']} de {chart_b.birth_data.name} "
            f"(orbe: {a['orb']}°)"
        )

    ec = synastry_data.get("element_compatibility", {})
    compat = (
        f"- {chart_a.birth_data.name}: elemento dominante {ec.get('person_a_dominant', '?')}\n"
        f"- {chart_b.birth_data.name}: elemento dominante {ec.get('person_b_dominant', '?')}"
    )

    return SYNASTRY_TEMPLATE.format(
        name_a=chart_a.birth_data.name,
        name_b=chart_b.birth_data.name,
        summary_a=format_planets(chart_a),
        summary_b=format_planets(chart_b),
        synastry_aspects="\n".join(aspect_lines) if aspect_lines else "Sin aspectos inter-carta.",
        element_compat=compat,
    )
