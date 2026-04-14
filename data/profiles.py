from __future__ import annotations


def compute_account_profiles(txns: list[dict]) -> dict[str, dict]:
    """
    Build an AccountProfile for each unique account_id.

    Profile keys:
      txn_count, avg_amount, std_amount, min_amount, max_amount, balance,
      avg_time_between_txns, unique_counterparties, known_counterparties,
      total_sent, total_received, first_seen, last_seen, is_new
    """
    raise NotImplementedError


def get_account_context(
    account_id: str, txns: list[dict], n: int = 20
) -> list[dict]:
    """Return the last `n` transactions where `account_id` is the sender."""
    raise NotImplementedError
