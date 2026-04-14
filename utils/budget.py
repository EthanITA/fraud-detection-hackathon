from __future__ import annotations

from config.models import COST_PER_1K_TOKENS

BUDGET_PANIC_THRESHOLD = 0.15
DEFAULT_RATE = 0.001


class BudgetTracker:
    """
    Tracks token spend against a fixed dollar limit.
    When remaining budget drops below 15%, is_panic() returns True
    and the pipeline should skip LLM layers entirely.
    """

    def __init__(self, limit: float):
        self._limit = limit
        self._spent = 0.0

    def record(self, tokens: int, model: str) -> float:
        """Record token usage and return remaining budget in dollars."""
        cost = self._estimate_cost(tokens, model)
        self._spent += cost
        return self.remaining()

    def remaining(self) -> float:
        return max(self._limit - self._spent, 0.0)

    def is_panic(self) -> bool:
        return self.remaining() < self._limit * BUDGET_PANIC_THRESHOLD

    @staticmethod
    def _estimate_cost(tokens: int, model: str) -> float:
        rate = COST_PER_1K_TOKENS.get(model, DEFAULT_RATE)
        return tokens * rate / 1000
