"""AstroLocal CLI — main entry point."""

from __future__ import annotations

import asyncio
import sys

import click

from astrolocal.config import LLMConfig, load_config
from astrolocal.llm.client import LocalLLMClient, LLMConnectionError, LLMError
from astrolocal.llm.interpreter import AstrologicalInterpreter
from astrolocal.models import BirthData, ReadingType
from astrolocal.storage.database import Database
from astrolocal.ui.cli import (
    console,
    print_banner,
    print_chart_summary,
    print_error,
    print_interpretation,
    print_profiles,
    print_success,
    print_warning,
    stream_interpretation,
)


def _run(coro):
    """Run an async function from sync Click context."""
    return asyncio.run(coro)


@click.group()
@click.option("--config", "config_path", default=None, help="Path to config.toml")
@click.pass_context
def cli(ctx: click.Context, config_path: str | None) -> None:
    """🔮 AstroLocal — Tu astrólogo personal con IA local."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)


@cli.command()
@click.argument("name")
@click.argument("year", type=int)
@click.argument("month", type=int)
@click.argument("day", type=int)
@click.argument("hour", type=int)
@click.argument("minute", type=int)
@click.argument("city")
@click.argument("nation")
@click.option("--save/--no-save", default=True, help="Guardar perfil y lectura")
@click.option("--stream/--no-stream", "use_stream", default=True, help="Streaming de respuesta")
@click.pass_context
def natal(
    ctx: click.Context,
    name: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    city: str,
    nation: str,
    save: bool,
    use_stream: bool,
) -> None:
    """Generar e interpretar una carta natal.

    Ejemplo: astrolocal natal "Juan" 1990 3 15 14 30 "Buenos Aires" AR
    """
    print_banner()
    config = ctx.obj["config"]

    try:
        birth = BirthData(
            name=name, year=year, month=month, day=day,
            hour=hour, minute=minute, city=city, nation=nation.upper(),
        )
    except Exception as e:
        print_error(f"Datos de nacimiento inválidos: {e}")
        sys.exit(1)

    async def _run_natal():
        llm = LocalLLMClient(config.llm)
        db = Database(config.app.database_path)

        try:
            # Check LLM health
            if not await llm.health_check():
                print_error(
                    f"No se pudo conectar a {config.llm.base_url}.\n"
                    "  Asegurate de que Ollama esté corriendo: ollama serve"
                )
                sys.exit(1)

            interpreter = AstrologicalInterpreter(llm)

            if use_stream:
                chart, stream = await interpreter.stream_natal(birth)
                print_chart_summary(chart)
                interpretation = await stream_interpretation(stream)
            else:
                chart, interpretation = await interpreter.interpret_natal(birth)
                print_chart_summary(chart)
                print_interpretation(interpretation)

            if save:
                await db.connect()
                profile_id = await db.add_profile(birth)
                await db.save_reading(
                    profile_id=profile_id,
                    reading_type=ReadingType.NATAL,
                    raw_data=chart.model_dump(mode="json"),
                    interpretation=interpretation,
                    model_used=config.llm.model,
                )
                print_success(f"Perfil y lectura guardados (ID: {profile_id})")

        except LLMConnectionError as e:
            print_error(str(e))
            sys.exit(1)
        except LLMError as e:
            print_error(f"Error del LLM: {e}")
            sys.exit(1)
        finally:
            await llm.close()
            await db.close()

    _run(_run_natal())


@cli.command()
@click.argument("name")
@click.option("--city", default="Buenos Aires", help="Ciudad de referencia para tránsitos")
@click.option("--nation", default="AR", help="País de referencia")
@click.pass_context
def transits(ctx: click.Context, name: str, city: str, nation: str) -> None:
    """Calcular tránsitos de hoy para un perfil guardado.

    Ejemplo: astrolocal transits "Juan"
    """
    print_banner()
    config = ctx.obj["config"]

    async def _run_transits():
        llm = LocalLLMClient(config.llm)
        db = Database(config.app.database_path)

        try:
            await db.connect()
            profile = await db.get_profile_by_name(name)
            if not profile:
                print_error(f"Perfil '{name}' no encontrado. Creálo primero con 'natal'.")
                sys.exit(1)

            if not await llm.health_check():
                print_error("Ollama no está corriendo. Iniciálo con: ollama serve")
                sys.exit(1)

            interpreter = AstrologicalInterpreter(llm)
            transit_data, interpretation = await interpreter.interpret_transits(
                profile.birth_data, city, nation.upper()
            )

            console.print(f"\n[bold]📅 Tránsitos del {transit_data['date']}[/]\n")
            print_interpretation(interpretation)

            await db.save_reading(
                profile_id=profile.id,
                reading_type=ReadingType.TRANSIT,
                raw_data=transit_data,
                interpretation=interpretation,
                model_used=config.llm.model,
            )
            print_success("Lectura guardada.")

        except LLMError as e:
            print_error(str(e))
            sys.exit(1)
        finally:
            await llm.close()
            await db.close()

    _run(_run_transits())


@cli.command()
@click.argument("name_a")
@click.argument("name_b")
@click.pass_context
def synastry(ctx: click.Context, name_a: str, name_b: str) -> None:
    """Sinastría entre dos perfiles guardados.

    Ejemplo: astrolocal synastry "Juan" "María"
    """
    print_banner()
    config = ctx.obj["config"]

    async def _run_synastry():
        llm = LocalLLMClient(config.llm)
        db = Database(config.app.database_path)

        try:
            await db.connect()
            prof_a = await db.get_profile_by_name(name_a)
            prof_b = await db.get_profile_by_name(name_b)

            if not prof_a:
                print_error(f"Perfil '{name_a}' no encontrado.")
                sys.exit(1)
            if not prof_b:
                print_error(f"Perfil '{name_b}' no encontrado.")
                sys.exit(1)

            if not await llm.health_check():
                print_error("Ollama no está corriendo.")
                sys.exit(1)

            interpreter = AstrologicalInterpreter(llm)
            syn_data, interpretation = await interpreter.interpret_synastry(
                prof_a.birth_data, prof_b.birth_data
            )

            print_interpretation(interpretation)

        except LLMError as e:
            print_error(str(e))
            sys.exit(1)
        finally:
            await llm.close()
            await db.close()

    _run(_run_synastry())


# ---- Profile Management ----

@cli.group()
def profile() -> None:
    """Gestionar perfiles guardados."""


@profile.command("list")
@click.pass_context
def profile_list(ctx: click.Context) -> None:
    """Listar todos los perfiles."""
    config = ctx.obj["config"]

    async def _list():
        db = Database(config.app.database_path)
        await db.connect()
        profiles = await db.list_profiles()
        await db.close()

        if profiles:
            print_profiles(profiles)
        else:
            print_warning("No hay perfiles guardados. Creá uno con 'astrolocal natal ...'")

    _run(_list())


@profile.command("delete")
@click.argument("profile_id", type=int)
@click.confirmation_option(prompt="¿Seguro que querés eliminar este perfil y sus lecturas?")
@click.pass_context
def profile_delete(ctx: click.Context, profile_id: int) -> None:
    """Eliminar un perfil y todas sus lecturas."""
    config = ctx.obj["config"]

    async def _delete():
        db = Database(config.app.database_path)
        await db.connect()
        deleted = await db.delete_profile(profile_id)
        await db.close()

        if deleted:
            print_success(f"Perfil {profile_id} eliminado.")
        else:
            print_error(f"Perfil {profile_id} no encontrado.")

    _run(_delete())


# ---- Health Check ----

@cli.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Verificar que todo esté funcionando."""
    print_banner()
    config = ctx.obj["config"]

    async def _check():
        llm = LocalLLMClient(config.llm)

        # Check Ollama
        console.print("Verificando Ollama...", end=" ")
        if await llm.health_check():
            console.print("[green]✓ Conectado[/]")
            models = await llm.list_models()
            for m in models:
                marker = " [green]← activo[/]" if m == config.llm.model else ""
                console.print(f"  • {m}{marker}")

            if config.llm.model not in models:
                print_warning(
                    f"Modelo '{config.llm.model}' no encontrado. "
                    f"Instalálo con: ollama pull {config.llm.model}"
                )
        else:
            print_error(
                f"No se pudo conectar a {config.llm.base_url}\n"
                "  Iniciá Ollama con: ollama serve"
            )

        # Check Kerykeion
        console.print("Verificando Kerykeion...", end=" ")
        try:
            from kerykeion import AstrologicalSubject
            test = AstrologicalSubject("Test", 2000, 1, 1, 12, 0, "London", "GB")
            console.print("[green]✓ Funcionando[/]")
        except Exception as e:
            print_error(f"Error: {e}")

        # Check DB
        console.print("Verificando base de datos...", end=" ")
        try:
            db = Database(config.app.database_path)
            await db.connect()
            profiles = await db.list_profiles(limit=1)
            total = len(profiles)
            await db.close()
            console.print(f"[green]✓ OK[/] ({config.app.database_path})")
        except Exception as e:
            print_error(f"Error: {e}")

        await llm.close()

    _run(_check())


if __name__ == "__main__":
    cli()
