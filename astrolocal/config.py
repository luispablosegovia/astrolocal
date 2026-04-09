"""Configuration management with validation and secure defaults."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Paths — resolved once, validated for traversal
# ---------------------------------------------------------------------------

def _safe_resolve(path: str | Path) -> Path:
    """Resolve a path and ensure it stays within the user's home directory."""
    resolved = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    if not str(resolved).startswith(str(home)):
        raise ValueError(f"Path escapes home directory: {resolved}")
    return resolved


DEFAULT_DATA_DIR = Path.home() / ".astrolocal"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "astrolocal.db"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "config.toml"


# ---------------------------------------------------------------------------
# Pydantic models — every external value is validated before use
# ---------------------------------------------------------------------------

class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = Field(default="ollama", pattern=r"^(ollama|mlx|openai_compat)$")
    model: str = Field(default="qwen2.5:14b", max_length=128)
    base_url: str = Field(default="http://localhost:11434")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=64, le=32768)
    context_window: int = Field(default=8192, ge=1024, le=131072)
    timeout_seconds: int = Field(default=300, ge=10, le=1800)
    fallback_model: str | None = Field(default="llama3.2:8b", max_length=128)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Only allow localhost or private network URLs."""
        from urllib.parse import urlparse

        parsed = urlparse(v)
        host = parsed.hostname or ""
        allowed_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
        is_private = host.startswith(("10.", "172.", "192.168."))

        if host not in allowed_hosts and not is_private:
            raise ValueError(
                f"LLM base_url must point to localhost or private network, got: {host}"
            )
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"LLM base_url must use http(s), got: {parsed.scheme}")
        return v


class AppConfig(BaseModel):
    """Application-level settings."""

    language: str = Field(default="es-AR", pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    database_path: str = Field(default=str(DEFAULT_DB_PATH))
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_file: str | None = None
    cache_charts: bool = True
    max_profiles: int = Field(default=100, ge=1, le=10000)
    max_readings_per_profile: int = Field(default=1000, ge=1, le=100000)

    @field_validator("database_path")
    @classmethod
    def validate_db_path(cls, v: str) -> str:
        resolved = _safe_resolve(v)
        return str(resolved)


class OutputConfig(BaseModel):
    """Output formatting settings."""

    format: str = Field(default="rich", pattern=r"^(rich|markdown|html|json)$")
    save_readings: bool = True
    show_raw_data: bool = False
    redact_birth_data_in_logs: bool = True


class AstroLocalConfig(BaseModel):
    """Root configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: str | Path | None = None) -> AstroLocalConfig:
    """Load configuration from TOML file, falling back to defaults.

    Environment variables override file settings:
        ASTROLOCAL_LLM_MODEL, ASTROLOCAL_LLM_BASE_URL, etc.
    """
    data: dict[str, Any] = {}

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

    # Environment variable overrides (flat mapping)
    env_overrides = {
        "ASTROLOCAL_LLM_MODEL": ("llm", "model"),
        "ASTROLOCAL_LLM_BASE_URL": ("llm", "base_url"),
        "ASTROLOCAL_LLM_PROVIDER": ("llm", "provider"),
        "ASTROLOCAL_DB_PATH": ("app", "database_path"),
        "ASTROLOCAL_LOG_LEVEL": ("app", "log_level"),
    }

    for env_key, (section, field) in env_overrides.items():
        val = os.environ.get(env_key)
        if val is not None:
            data.setdefault(section, {})[field] = val

    return AstroLocalConfig(**data)
