from __future__ import annotations

BUDGET_PANIC_THRESHOLD = 0.15


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
        # rough $/1k-token estimates for OpenRouter
        rates = {
            "openai/gpt-4o-mini": 0.00015,
            "openai/gpt-4o": 0.005,
        }
        per_token = rates.get(model, 0.001) / 1000
        return tokens * per_token
