"""Tests for configuration validation."""

import pytest
from pydantic import ValidationError

from astrolocal.config import AstroLocalConfig, LLMConfig


class TestLLMConfig:
    def test_default_is_localhost(self):
        c = LLMConfig()
        assert "localhost" in c.base_url

    def test_rejects_external_url(self):
        with pytest.raises(ValidationError, match="localhost or private"):
            LLMConfig(base_url="https://api.openai.com/v1")

    def test_allows_private_network(self):
        c = LLMConfig(base_url="http://192.168.1.100:11434")
        assert "192.168" in c.base_url

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValidationError, match="http"):
            LLMConfig(base_url="ftp://localhost:11434")

    def test_temperature_bounds(self):
        with pytest.raises(ValidationError):
            LLMConfig(temperature=3.0)
        with pytest.raises(ValidationError):
            LLMConfig(temperature=-1.0)

    def test_provider_validation(self):
        with pytest.raises(ValidationError):
            LLMConfig(provider="gpt4all")

    def test_model_max_length(self):
        with pytest.raises(ValidationError):
            LLMConfig(model="a" * 129)


class TestFullConfig:
    def test_default_config_is_valid(self):
        c = AstroLocalConfig()
        assert c.llm.provider == "ollama"
        assert c.app.language == "es-AR"
        assert c.output.redact_birth_data_in_logs is True
