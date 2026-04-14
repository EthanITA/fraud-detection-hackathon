# %% imports
from __future__ import annotations

from collections import defaultdict


# %% build_relationship_graph
def build_relationship_graph(txns: list[dict]) -> dict:
    """Single upfront pass. Returns {nodes: [...], edges: [...]}.

    Node: {id, in_degree, out_degree, clustering_coefficient, is_new}
    Edge: {source, target, count, total_amount, avg_amount, timestamps}
    """
    edge_data: dict[tuple[str, str], dict] = {}
    out_neighbors: dict[str, set[str]] = defaultdict(set)
    in_neighbors: dict[str, set[str]] = defaultdict(set)
    txn_counts: dict[str, int] = defaultdict(int)

    for txn in txns:
        sid, rid = txn["sender_id"], txn["receiver_id"]
        amt, ts = txn["amount"], txn["timestamp"]

        key = (sid, rid)
        if key not in edge_data:
            edge_data[key] = {"count": 0, "total_amount": 0.0, "timestamps": []}
        edge_data[key]["count"] += 1
        edge_data[key]["total_amount"] += amt
        edge_data[key]["timestamps"].append(ts)

        out_neighbors[sid].add(rid)
        in_neighbors[rid].add(sid)
        txn_counts[sid] += 1
        txn_counts[rid] += 1

    all_ids = set(out_neighbors) | set(in_neighbors)
    neighbors: dict[str, set[str]] = defaultdict(set)
    for aid in all_ids:
        neighbors[aid] = out_neighbors.get(aid, set()) | in_neighbors.get(aid, set())

    def _clustering(aid: str) -> float:
        nbrs = neighbors[aid]
        k = len(nbrs)
        if k < 2:
            return 0.0
        links = 0
        nbr_list = list(nbrs)
        for i in range(k):
            for j in range(i + 1, k):
                a, b = nbr_list[i], nbr_list[j]
                if (a, b) in edge_data or (b, a) in edge_data:
                    links += 1
        return (2 * links) / (k * (k - 1))

    nodes = []
    for aid in all_ids:
        nodes.append(
            {
                "id": aid,
                "in_degree": len(in_neighbors.get(aid, set())),
                "out_degree": len(out_neighbors.get(aid, set())),
                "clustering_coefficient": _clustering(aid),
                "is_new": txn_counts[aid] < 3,
            }
        )

    edges = []
    for (src, tgt), data in edge_data.items():
        edges.append(
            {
                "source": src,
                "target": tgt,
                "count": data["count"],
                "total_amount": data["total_amount"],
                "avg_amount": data["total_amount"] / data["count"],
                "timestamps": data["timestamps"],
            }
        )

    return {"nodes": nodes, "edges": edges}
