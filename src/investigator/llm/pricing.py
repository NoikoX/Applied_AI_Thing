"""Token prices from config/pricing.yaml."""

import logging
from pathlib import Path

import yaml

from investigator.config import PROJECT_ROOT

logger = logging.getLogger(__name__)
DEFAULT_PRICING_PATH = PROJECT_ROOT / "config" / "pricing.yaml"


class Pricing:
    def __init__(self, prices: dict[str, dict[str, float]]):
        self.prices = prices

    @classmethod
    def load(cls, path: Path = DEFAULT_PRICING_PATH) -> "Pricing":
        return cls(yaml.safe_load(path.read_text(encoding="utf-8")) or {})

    def cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """USD for one call; None (and a warning) for a model with no listed price."""
        price = self.prices.get(model)
        if price is None:
            logger.warning("No price for model %s in pricing.yaml", model)
            return None
        return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
