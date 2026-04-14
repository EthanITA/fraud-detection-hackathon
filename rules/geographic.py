# %% imports
from __future__ import annotations

import json
import math

from langchain.tools import tool

from ._types import (
    IMPOSSIBLE_TRAVEL_DISTANCE_HIGH,
    IMPOSSIBLE_TRAVEL_DISTANCE_MEDIUM,
    RiskLevel,
)


# %% _haversine_km
def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# %% check_impossible_travel
@tool
def check_impossible_travel(txn_json: str, citizen_json: str) -> str:
    """
    Detect transactions from locations inconsistent with the citizen's known location history.
      HIGH   — transaction location > 5000km from citizen's home AND citizen has low mobility
      MEDIUM — transaction location > 2000km from citizen's home

    txn_json:     Transaction (needs: lat/lng or location fields if available)
    citizen_json: Citizen location summary (needs: home_lat, home_lng, max_distance_km, visited_cities)
    """
    txn = json.loads(txn_json)
    citizen = json.loads(citizen_json)

    # Need both transaction location and citizen home location
    home_lat = citizen.get("home_lat")
    home_lng = citizen.get("home_lng")
    if home_lat is None or home_lng is None:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No citizen location data."})

    # Try to get transaction location (field names may vary on challenge day)
    txn_lat = txn.get("lat") or txn.get("latitude") or txn.get("merchant_lat")
    txn_lng = txn.get("lng") or txn.get("longitude") or txn.get("merchant_lng")

    if txn_lat is None or txn_lng is None:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No transaction location data."})

    txn_lat, txn_lng = float(txn_lat), float(txn_lng)
    distance = _haversine_km(home_lat, home_lng, txn_lat, txn_lng)
    max_known = citizen.get("max_distance_km", 0)

    # High: far from home AND farther than anything in their history
    if distance > IMPOSSIBLE_TRAVEL_DISTANCE_HIGH and distance > max_known * 1.5:
        return json.dumps({
            "risk": RiskLevel.HIGH,
            "reason": f"Transaction {distance:.0f}km from home (max known travel: {max_known:.0f}km).",
        })

    if distance > IMPOSSIBLE_TRAVEL_DISTANCE_MEDIUM:
        return json.dumps({
            "risk": RiskLevel.MEDIUM,
            "reason": f"Transaction {distance:.0f}km from home.",
        })

    return json.dumps({"risk": RiskLevel.LOW, "reason": f"Transaction {distance:.0f}km from home — within normal range."})
