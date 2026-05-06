"""
Configuration management for AI Finance Analyzer.

Supports environment variables, .env files, and programmatic overrides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Auto-load .env file if it exists (project root or current directory)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; fall back to real env vars


@dataclass
class LLMConfig:
    """Configuration for the LLM backend (DeepSeek by default)."""

    provider: str = "deepseek"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 30

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        env_base = os.getenv("LLM_BASE_URL", "")
        if env_base:
            self.base_url = env_base
        env_model = os.getenv("LLM_MODEL", "")
        if env_model:
            self.model = env_model


@dataclass
class AnalyzerConfig:
    """Configuration for the analysis engine."""

    # Health score weights (must sum to 1.0)
    weight_savings_rate: float = 0.30
    weight_essential_ratio: float = 0.25
    weight_stability: float = 0.20
    weight_diversity: float = 0.15
    weight_trend: float = 0.10

    # Thresholds for risk alerts
    high_category_threshold: float = 0.35  # Alert if any category > 35%
    anomaly_std_multiplier: float = 2.0  # Flag if > 2 std deviations
    min_savings_rate: float = 0.10  # Alert if savings rate < 10%

    # Categories considered "essential"
    essential_categories: list[str] = field(
        default_factory=lambda: ["food", "housing", "transport", "utilities", "health"]
    )


@dataclass
class Config:
    """Root configuration object."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    currency: str = "CNY"
    currency_symbol: str = "¥"
    locale: str = "zh-CN"
    debug: bool = False

    @classmethod
    def from_env(cls) -> Config:
        """Create config from environment variables."""
        return cls(
            llm=LLMConfig(),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )

    @classmethod
    def default(cls) -> Config:
        """Create config with sensible defaults."""
        return cls()


# Global default config — can be overridden
_config: Config | None = None


def get_config() -> Config:
    """Get the global config, creating from env if not set."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Override the global config."""
    global _config
    _config = config
