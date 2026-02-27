"""
Managed Inference Service

Handles Bonito-managed API key proxying for providers that support it.
Tracks usage per org and applies markup pricing.
"""

import os
from typing import Optional

MANAGED_PROVIDERS = {"groq", "openai", "anthropic"}

# Markup: 33% on top of base cost
MARKUP_RATE = 0.33

# Env var names for master keys
MASTER_KEY_ENV = {
    "groq": "BONITO_GROQ_MASTER_KEY",
    "openai": "BONITO_OPENAI_MASTER_KEY",
    "anthropic": "BONITO_ANTHROPIC_MASTER_KEY",
}

# Base pricing per 1K tokens (used for managed pricing display)
BASE_PRICING = {
    "groq": {"input_per_1k": 0.00059, "output_per_1k": 0.00079},
    "openai": {"input_per_1k": 0.0025, "output_per_1k": 0.01},
    "anthropic": {"input_per_1k": 0.003, "output_per_1k": 0.015},
}


def is_managed_provider(provider_type: str) -> bool:
    """Returns True if provider supports managed mode."""
    return provider_type in MANAGED_PROVIDERS


def get_master_key(provider_type: str) -> Optional[str]:
    """Reads master key from env var, returns None if not configured."""
    env_var = MASTER_KEY_ENV.get(provider_type)
    if not env_var:
        return None
    return os.getenv(env_var)


def is_managed_available(provider_type: str) -> bool:
    """Returns True if the provider supports managed mode AND a master key is configured."""
    if not is_managed_provider(provider_type):
        return False
    return get_master_key(provider_type) is not None


def calculate_marked_up_cost(base_cost: float) -> float:
    """Applies 33% markup to base cost."""
    return round(base_cost * (1 + MARKUP_RATE), 6)


def get_managed_pricing(provider_type: str) -> dict:
    """Returns marked-up pricing for display."""
    base = BASE_PRICING.get(provider_type)
    if not base:
        return {}
    return {
        "input_per_1k": calculate_marked_up_cost(base["input_per_1k"]),
        "output_per_1k": calculate_marked_up_cost(base["output_per_1k"]),
        "markup_rate": MARKUP_RATE,
        "base_input_per_1k": base["input_per_1k"],
        "base_output_per_1k": base["output_per_1k"],
    }
