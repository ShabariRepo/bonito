"""Static pricing data for AWS Bedrock models.

Prices are per 1M tokens (input/output).
Updated manually — check AWS pricing page for latest.
"""

from typing import Optional, Tuple

# model_id_prefix -> (input_price_per_1M, output_price_per_1M, context_window)
BEDROCK_PRICING: dict[str, Tuple[float, float, int]] = {
    # Anthropic
    "anthropic.claude-3-5-sonnet": (3.00, 15.00, 200_000),
    "anthropic.claude-3-5-haiku": (1.00, 5.00, 200_000),
    "anthropic.claude-3-opus": (15.00, 75.00, 200_000),
    "anthropic.claude-3-sonnet": (3.00, 15.00, 200_000),
    "anthropic.claude-3-haiku": (0.25, 1.25, 200_000),
    "anthropic.claude-v2": (8.00, 24.00, 100_000),
    "anthropic.claude-instant": (0.80, 2.40, 100_000),
    # Meta Llama
    "meta.llama3-1-405b": (5.32, 16.00, 128_000),
    "meta.llama3-1-70b": (2.65, 3.50, 128_000),
    "meta.llama3-1-8b": (0.30, 0.60, 128_000),
    "meta.llama3-2-90b": (2.00, 2.00, 128_000),
    "meta.llama3-2-11b": (0.35, 0.35, 128_000),
    "meta.llama3-2-3b": (0.15, 0.15, 128_000),
    "meta.llama3-2-1b": (0.10, 0.10, 128_000),
    "meta.llama3-70b": (2.65, 3.50, 8_000),
    "meta.llama3-8b": (0.30, 0.60, 8_000),
    # Amazon Titan
    "amazon.titan-text-premier": (0.50, 1.50, 32_000),
    "amazon.titan-text-express": (0.20, 0.60, 8_000),
    "amazon.titan-text-lite": (0.15, 0.20, 4_000),
    "amazon.titan-embed-text-v2": (0.02, 0.00, 8_192),
    "amazon.titan-embed-text": (0.01, 0.00, 8_192),
    "amazon.titan-embed-image": (0.80, 0.00, 128),
    # Cohere
    "cohere.command-r-plus": (3.00, 15.00, 128_000),
    "cohere.command-r": (0.50, 1.50, 128_000),
    "cohere.command-text": (1.50, 2.00, 4_096),
    "cohere.command-light-text": (0.30, 0.60, 4_096),
    "cohere.embed-english": (0.10, 0.00, 512),
    "cohere.embed-multilingual": (0.10, 0.00, 512),
    # Mistral
    "mistral.mistral-large": (4.00, 12.00, 128_000),
    "mistral.mistral-small": (1.00, 3.00, 32_000),
    "mistral.mixtral-8x7b": (0.45, 0.70, 32_000),
    "mistral.mistral-7b": (0.15, 0.20, 32_000),
    # AI21
    "ai21.jamba-1-5-large": (2.00, 8.00, 256_000),
    "ai21.jamba-1-5-mini": (0.20, 0.40, 256_000),
    "ai21.j2-ultra": (18.80, 18.80, 8_191),
    "ai21.j2-mid": (12.50, 12.50, 8_191),
    # Stability
    "stability.stable-diffusion-xl": (0.0, 0.0, 0),  # per-image pricing
}


def _match_model(model_id: str) -> Optional[str]:
    """Find the best matching pricing key for a model ID."""
    for prefix in sorted(BEDROCK_PRICING.keys(), key=len, reverse=True):
        if model_id.startswith(prefix):
            return prefix
    return None


def get_pricing(model_id: str) -> Tuple[float, float]:
    """Return (input_price_per_1M, output_price_per_1M) for a model."""
    key = _match_model(model_id)
    if key:
        return BEDROCK_PRICING[key][0], BEDROCK_PRICING[key][1]
    return 0.0, 0.0


def get_context_window(model_id: str) -> int:
    """Return context window size for a model."""
    key = _match_model(model_id)
    if key:
        return BEDROCK_PRICING[key][2]
    return 0


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given token count."""
    inp_price, out_price = get_pricing(model_id)
    return (input_tokens * inp_price / 1_000_000) + (output_tokens * out_price / 1_000_000)
