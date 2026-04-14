from __future__ import annotations


def build_relationship_graph(txns: list[dict]) -> dict:
    """
    Build a serializable relationship graph from transactions.

    Returns: {
      nodes: [{id, in_degree, out_degree, clustering_coefficient, is_new}],
      edges: [{source, target, count, total_amount, avg_amount, timestamps}]
    }
    """
    raise NotImplementedError
