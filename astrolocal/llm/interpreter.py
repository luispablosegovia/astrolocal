"""Interpreter — orchestrates chart data → prompt → LLM → interpretation."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from astrolocal.core.chart import generate_chart
from astrolocal.core.synastry import analyze_synastry
from astrolocal.core.transits import get_daily_transits
from astrolocal.llm.client import LocalLLMClient
from astrolocal.llm.prompts import (
    SYSTEM_PROMPT,
    build_natal_prompt,
    build_synastry_prompt,
    build_transit_prompt,
)
from astrolocal.models import BirthData, ChartData

logger = logging.getLogger("astrolocal.llm.interpreter")


class AstrologicalInterpreter:
    """Main interpreter that ties chart generation to LLM interpretation."""

    def __init__(self, llm: LocalLLMClient):
        self.llm = llm

    async def interpret_natal(self, birth: BirthData) -> tuple[ChartData, str]:
        """Generate and interpret a natal chart. Returns (chart_data, interpretation)."""
        chart = generate_chart(birth)
        prompt = build_natal_prompt(chart)

        logger.info("Generating natal interpretation for %s", birth.anonymized_id())
        interpretation = await self.llm.generate(prompt, system=SYSTEM_PROMPT)

        return chart, interpretation

    async def stream_natal(self, birth: BirthData) -> tuple[ChartData, AsyncIterator[str]]:
        """Generate chart and stream natal interpretation."""
        chart = generate_chart(birth)
        prompt = build_natal_prompt(chart)

        logger.info("Streaming natal interpretation for %s", birth.anonymized_id())
        stream = self.llm.stream(prompt, system=SYSTEM_PROMPT)

        return chart, stream

    async def interpret_transits(
        self,
        birth: BirthData,
        reference_city: str = "Buenos Aires",
        reference_nation: str = "AR",
    ) -> tuple[dict[str, Any], str]:
        """Calculate and interpret today's transits."""
        chart = generate_chart(birth)
        transit_data = get_daily_transits(chart, reference_city, reference_nation)
        prompt = build_transit_prompt(chart, transit_data)

        logger.info("Generating transit interpretation for %s", birth.anonymized_id())
        interpretation = await self.llm.generate(prompt, system=SYSTEM_PROMPT)

        return transit_data, interpretation

    async def interpret_synastry(
        self,
        birth_a: BirthData,
        birth_b: BirthData,
    ) -> tuple[dict[str, Any], str]:
        """Calculate and interpret synastry between two people."""
        chart_a = generate_chart(birth_a)
        chart_b = generate_chart(birth_b)
        synastry_data = analyze_synastry(chart_a, chart_b)
        prompt = build_synastry_prompt(chart_a, chart_b, synastry_data)

        logger.info(
            "Generating synastry for %s and %s",
            birth_a.anonymized_id(),
            birth_b.anonymized_id(),
        )
        interpretation = await self.llm.generate(prompt, system=SYSTEM_PROMPT)

        return synastry_data, interpretation
