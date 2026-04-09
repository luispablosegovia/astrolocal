"""Rich terminal UI for AstroLocal."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from astrolocal.models import ChartData, ProfileRecord

console = Console()


def print_banner() -> None:
    console.print(
        Panel(
            "[bold magenta]🔮 AstroLocal[/] — Tu astrólogo personal con IA local\n"
            "[dim]100% privado · 100% offline · 0% nube[/]",
            border_style="magenta",
        )
    )


def print_chart_summary(chart: ChartData) -> None:
    """Print a compact chart summary."""
    table = Table(title="Posiciones Planetarias", border_style="blue")
    table.add_column("Planeta", style="cyan")
    table.add_column("Signo", style="yellow")
    table.add_column("Casa", style="green")
    table.add_column("Grado", style="dim")
    table.add_column("", style="red")

    for p in chart.planets:
        retro = "℞" if p.retrograde else ""
        table.add_row(p.name, p.sign, str(p.house), f"{p.degree:.1f}°", retro)

    console.print(table)
    console.print(f"  ⬆️  Ascendente: [yellow]{chart.ascendant_sign}[/]")
    console.print(f"  🎯 Medio Cielo: [yellow]{chart.mc_sign}[/]")

    if chart.stelliums:
        for s in chart.stelliums:
            planets = ", ".join(s["planets"])
            console.print(f"  ✨ Stellium en {s['location']}: [cyan]{planets}[/]")

    if chart.special_patterns:
        for p in chart.special_patterns:
            console.print(f"  🔺 {p}")

    console.print()


def print_interpretation(text: str) -> None:
    """Print a full interpretation as rendered Markdown."""
    console.print(Panel(Markdown(text), title="Interpretación", border_style="magenta"))


async def stream_interpretation(stream: AsyncIterator[str]) -> str:
    """Stream interpretation to terminal, returning full text."""
    full_text = ""
    console.print(Panel("[dim]Generando interpretación...[/]", border_style="magenta"))

    with Live(Text(""), console=console, refresh_per_second=8) as live:
        async for token in stream:
            full_text += token
            live.update(Markdown(full_text))

    return full_text


def print_profiles(profiles: list[ProfileRecord]) -> None:
    table = Table(title="Perfiles Guardados", border_style="blue")
    table.add_column("ID", style="dim")
    table.add_column("Nombre", style="cyan")
    table.add_column("Nacimiento", style="yellow")
    table.add_column("Ciudad", style="green")
    table.add_column("Creado", style="dim")

    for p in profiles:
        b = p.birth_data
        table.add_row(
            str(p.id),
            b.name,
            f"{b.display_date()} {b.display_time()}",
            f"{b.city}, {b.nation}",
            p.created_at.strftime("%Y-%m-%d"),
        )

    console.print(table)


def print_error(msg: str) -> None:
    console.print(f"[bold red]Error:[/] {msg}")


def print_success(msg: str) -> None:
    console.print(f"[bold green]✓[/] {msg}")


def print_warning(msg: str) -> None:
    console.print(f"[bold yellow]⚠[/] {msg}")
