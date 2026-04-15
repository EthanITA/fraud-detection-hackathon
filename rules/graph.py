# %% imports
from __future__ import annotations

import json
from collections import defaultdict, deque

from langchain.tools import tool

from ._types import (
    CIRCULAR_MAX_HOPS,
    FAN_IN_HIGH,
    FAN_IN_MEDIUM,
    FAN_OUT_HIGH,
    FAN_OUT_MEDIUM,
    MULE_FORWARD_HIGH,
    MULE_FORWARD_MEDIUM,
    MULE_WINDOW_HIGH,
    MULE_WINDOW_MEDIUM,
    RiskLevel,
)


# %% check_fan_in
@tool
def check_fan_in(txn_json: str, graph_json: str) -> str:
    """
    Detect a money-mule aggregation node: many distinct senders converging
    on one receiver account.
      HIGH   — receiver has >10 distinct senders
      MEDIUM — receiver has >5 distinct senders

    txn_json:   Transaction (needs: receiver_id)
    graph_json: subgraph {nodes: [{id, in_degree, ...}], edges: [...]}
    """
    txn = json.loads(txn_json)
    graph = json.loads(graph_json)
    receiver_id = txn["receiver_id"]

    node = next((n for n in graph.get("nodes", []) if n["id"] == receiver_id), None)
    if not node:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Receiver not found in graph"})

    in_deg = node["in_degree"]
    if in_deg > FAN_IN_HIGH:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Receiver has {in_deg} distinct senders (>{FAN_IN_HIGH})"})
    if in_deg > FAN_IN_MEDIUM:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Receiver has {in_deg} distinct senders (>{FAN_IN_MEDIUM})"})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "Normal fan-in"})


# %% check_fan_out
@tool
def check_fan_out(txn_json: str, graph_json: str) -> str:
    """
    Detect rapid distribution from one account to many recipients
    (money-mule payout node).
      HIGH   — sender has >10 distinct recipients
      MEDIUM — sender has >5 distinct recipients

    txn_json:   Transaction (needs: sender_id)
    graph_json: subgraph {nodes: [{id, out_degree, ...}], edges: [...]}
    """
    txn = json.loads(txn_json)
    graph = json.loads(graph_json)
    sender_id = txn["sender_id"]

    node = next((n for n in graph.get("nodes", []) if n["id"] == sender_id), None)
    if not node:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Sender not found in graph"})

    out_deg = node["out_degree"]
    if out_deg > FAN_OUT_HIGH:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Sender has {out_deg} distinct recipients (>{FAN_OUT_HIGH})"})
    if out_deg > FAN_OUT_MEDIUM:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Sender has {out_deg} distinct recipients (>{FAN_OUT_MEDIUM})"})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "Normal fan-out"})


# %% check_mule_chain
@tool
def check_mule_chain(txn_json: str, graph_json: str) -> str:
    """
    Detect a mule-chain hop: A→B→C where the intermediate node B forwarded
    funds within a short window after receiving them.
      HIGH   — receiver forwarded ≥70% of received amount within 30min
      MEDIUM — receiver forwarded ≥50% within 2h

    txn_json:   Transaction (needs: receiver_id, amount, timestamp)
    graph_json: 2-hop subgraph with edge timestamps and amounts
    """
    txn = json.loads(txn_json)
    graph = json.loads(graph_json)
    receiver_id = txn["receiver_id"]
    txn_ts = txn["timestamp"]
    txn_amount = txn["amount"]

    if not txn_amount:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Zero transaction amount"})

    outgoing = [e for e in graph.get("edges", []) if e["source"] == receiver_id]
    if not outgoing:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No outgoing edges from receiver"})

    # Sum amounts forwarded within each time window
    fwd_high = 0.0
    fwd_medium = 0.0
    for edge in outgoing:
        for ts in edge["timestamps"]:
            delta = ts - txn_ts
            if delta <= 0:
                continue
            if delta <= MULE_WINDOW_HIGH:
                fwd_high += edge.get("avg_amount", edge["total_amount"] / edge["count"])
                fwd_medium += edge.get("avg_amount", edge["total_amount"] / edge["count"])
            elif delta <= MULE_WINDOW_MEDIUM:
                fwd_medium += edge.get("avg_amount", edge["total_amount"] / edge["count"])

    ratio_high = fwd_high / txn_amount
    ratio_medium = fwd_medium / txn_amount

    if ratio_high >= MULE_FORWARD_HIGH:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Receiver forwarded {ratio_high:.0%} of amount within 30min"})
    if ratio_medium >= MULE_FORWARD_MEDIUM:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Receiver forwarded {ratio_medium:.0%} of amount within 2h"})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "No significant rapid forwarding detected"})


# %% check_circular_flow
@tool
def check_circular_flow(txn_json: str, graph_json: str) -> str:
    """
    Detect circular money flow where funds return to the origin account
    (wash trading / network testing).
      HIGH — path from receiver back to sender within ≤3 hops

    txn_json:   Transaction (needs: sender_id, receiver_id)
    graph_json: 3-hop subgraph as adjacency list
    """
    txn = json.loads(txn_json)
    graph = json.loads(graph_json)
    sender_id = txn["sender_id"]
    receiver_id = txn["receiver_id"]

    if sender_id == receiver_id:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": "Self-loop: sender and receiver are the same"})

    adj: dict[str, set[str]] = defaultdict(set)
    for edge in graph.get("edges", []):
        adj[edge["source"]].add(edge["target"])

    # BFS from receiver_id, looking for sender_id within max hops
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(receiver_id, 0)])
    visited.add(receiver_id)

    while queue:
        node, depth = queue.popleft()
        if depth >= CIRCULAR_MAX_HOPS:
            continue
        for neighbor in adj.get(node, []):
            if neighbor == sender_id:
                return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Circular flow: path from receiver back to sender within {depth + 1} hops"})
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))

    return json.dumps({"risk": RiskLevel.LOW, "reason": "No circular flow detected"})
