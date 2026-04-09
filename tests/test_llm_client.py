"""Tests for LLM client input validation and rate limiting."""

import pytest

from astrolocal.config import LLMConfig
from astrolocal.llm.client import (
    LocalLLMClient,
    LLMError,
    LLMRateLimitError,
    RateLimiter,
)


class TestPromptValidation:
    def setup_method(self):
        self.client = LocalLLMClient(LLMConfig())

    def test_empty_prompt_rejected(self):
        with pytest.raises(LLMError, match="empty"):
            self.client._validate_prompt("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(LLMError, match="empty"):
            self.client._validate_prompt("   \n\t  ")

    def test_oversized_prompt_rejected(self):
        huge = "x" * (256 * 1024 + 1)
        with pytest.raises(LLMError, match="max size"):
            self.client._validate_prompt(huge)

    def test_valid_prompt_passes(self):
        result = self.client._validate_prompt("  Hello world  ")
        assert result == "Hello world"


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_requests=3, window=60.0)
        rl.check()
        rl.check()
        rl.check()

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_requests=2, window=60.0)
        rl.check()
        rl.check()
        with pytest.raises(LLMRateLimitError):
            rl.check()
