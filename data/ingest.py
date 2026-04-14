from __future__ import annotations


def parse_dataset(path: str) -> list[dict]:
    """
    Parse a JSON or CSV dataset file into a list of Transaction dicts.

    Expected keys per transaction:
      id, sender_id, receiver_id, amount, timestamp, sender_balance
    """
    raise NotImplementedError
