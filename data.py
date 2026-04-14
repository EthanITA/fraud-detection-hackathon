"""
Layer 0 — Data ingestion.

Parses datasets, builds account profiles, and constructs the relationship graph.
All outputs are plain dicts (JSON-serializable) so rule tools can consume them.
"""

from __future__ import annotations


def parse_dataset(path: str) -> list[dict]:
    """
    Parse a JSON or CSV dataset file into a list of Transaction dicts.

    Expected keys per transaction:
      id, sender_id, receiver_id, amount, timestamp, sender_balance
    """
    raise NotImplementedError


def compute_account_profiles(txns: list[dict]) -> dict[str, dict]:
    """
    Build an AccountProfile for each unique account_id.

    Profile keys:
      txn_count, avg_amount, std_amount, min_amount, max_amount, balance,
      avg_time_between_txns, unique_counterparties, known_counterparties,
      total_sent, total_received, first_seen, last_seen, is_new
    """
    raise NotImplementedError


def build_relationship_graph(txns: list[dict]) -> dict:
    """
    Build a serializable relationship graph from transactions.

    Returns: {
      nodes: [{id, in_degree, out_degree, clustering_coefficient, is_new}],
      edges: [{source, target, count, total_amount, avg_amount, timestamps}]
    }
    """
    raise NotImplementedError


def get_account_context(
    account_id: str, txns: list[dict], n: int = 20
) -> list[dict]:
    """Return the last `n` transactions where `account_id` is the sender."""
    raise NotImplementedError
