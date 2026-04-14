# %% imports
from __future__ import annotations

import json

from langchain.tools import tool

from ._types import RiskLevel


# %% check_fan_in
@tool
def check_fan_in(txn_json: str, graph_json: str) -> str:
    """
    Detect a money-mule aggregation node: many distinct senders converging
    on one receiver account.
      HIGH   — receiver.in_degree > 10
      MEDIUM — receiver.in_degree > 5

    txn_json:   Transaction (needs: receiver_id)
    graph_json: subgraph {nodes: [{id, in_degree, ...}], edges: [...]}
    """
    # TODO: parse txn_json/graph_json, find receiver node in graph,
    #   HIGH if in_degree > FAN_IN_HIGH, MEDIUM if > FAN_IN_MEDIUM
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


# %% check_fan_out
@tool
def check_fan_out(txn_json: str, graph_json: str) -> str:
    """
    Detect rapid distribution from one account to many recipients
    (money-mule payout node).
      HIGH   — sender.out_degree > 10 in last 24h
      MEDIUM — sender.out_degree > 5

    txn_json:   Transaction (needs: sender_id)
    graph_json: subgraph {nodes: [{id, out_degree, ...}], edges: [...]}
    """
    # TODO: parse txn_json/graph_json, find sender node in graph,
    #   HIGH if out_degree > FAN_OUT_HIGH, MEDIUM if > FAN_OUT_MEDIUM
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


# %% check_mule_chain
@tool
def check_mule_chain(txn_json: str, graph_json: str) -> str:
    """
    Detect a mule-chain hop: A→B→C where the intermediate node B forwarded
    funds within a short window after receiving them.
      HIGH   — receiver forwarded ≥ 70% of received amount within 30 min
      MEDIUM — receiver forwarded ≥ 50% within 2h

    txn_json:   Transaction (needs: receiver_id, amount, timestamp)
    graph_json: 2-hop subgraph with edge timestamps and amounts
    """
    # TODO: parse txn_json/graph_json, find outgoing edges from receiver,
    #   compute forward_ratio = outgoing_amount / incoming_amount within time window.
    #   HIGH if forward_ratio > MULE_FORWARD_HIGH and window < MULE_WINDOW_HIGH,
    #   MEDIUM if forward_ratio > MULE_FORWARD_MEDIUM and window < MULE_WINDOW_MEDIUM
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


# %% check_circular_flow
@tool
def check_circular_flow(txn_json: str, graph_json: str) -> str:
    """
    Detect circular money flow where funds return to the origin account
    (wash trading / network testing).
      HIGH — a path from receiver back to sender exists within 3 hops

    txn_json:   Transaction (needs: sender_id, receiver_id)
    graph_json: 3-hop subgraph as adjacency list
    """
    # TODO: parse txn_json/graph_json, BFS/DFS from receiver_id looking for
    #   a path back to sender_id within CIRCULAR_MAX_HOPS. HIGH if found.
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})
