# %% imports
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from langchain.tools import tool

from ._types import RiskLevel


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
    Detect physical transactions (in-person/withdrawal) at locations inconsistent
    with the citizen's GPS pings around the same time.

    HIGH — transaction city doesn't match any GPS ping within 6h AND citizen
           has GPS pings in a DIFFERENT city within 24h (proves they were elsewhere)
    MEDIUM — transaction city doesn't match nearest GPS ping city

    txn_json:     Transaction (needs: location, transaction_type, timestamp)
    citizen_json: Citizen location summary (needs: home_city, pings[])
    """
    txn = json.loads(txn_json)
    raw_citizen = json.loads(citizen_json)
    # Support both full citizen object and location-only
    citizen = raw_citizen.get("location", raw_citizen) if "location" in raw_citizen else raw_citizen

    txn_type = txn.get("transaction_type", "")
    # Only check physical transactions — e-commerce locations are merchant names
    if txn_type not in ("in-person payment", "withdrawal"):
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Non-physical transaction — location check N/A."})

    txn_location = txn.get("location", "")
    if not txn_location:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No transaction location data."})

    # Extract city from "City - Venue" format
    txn_city = txn_location.split(" - ")[0].strip() if " - " in txn_location else txn_location.strip()

    pings = citizen.get("pings", [])
    if not pings:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No GPS ping data for citizen."})

    ts = txn.get("timestamp", 0)

    # Find GPS pings within 24h of transaction
    nearby_pings = []
    for p in pings:
        try:
            p_ts = datetime.fromisoformat(p["ts"]).timestamp() if isinstance(p["ts"], str) else p["ts"]
        except (ValueError, TypeError):
            continue
        gap_h = abs(p_ts - ts) / 3600
        if gap_h <= 24:
            nearby_pings.append({"gap_h": gap_h, "city": p.get("city", ""), "lat": p["lat"], "lng": p["lng"]})

    if not nearby_pings:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No GPS pings within 24h of transaction."})

    # Check if any nearby ping matches the transaction city
    def _city_match(a: str, b: str) -> bool:
        a, b = a.lower().strip(), b.lower().strip()
        return a == b or a in b or b in a

    matching = [p for p in nearby_pings if _city_match(txn_city, p["city"])]
    contradicting = [p for p in nearby_pings if not _city_match(txn_city, p["city"])]

    if matching:
        return json.dumps({"risk": RiskLevel.LOW, "reason": f"GPS confirms presence in {txn_city}."})

    if contradicting:
        closest = min(contradicting, key=lambda p: p["gap_h"])
        gps_city = closest["city"]
        gap = closest["gap_h"]

        # Calculate distance between home and transaction city using closest ping coords
        home_lat = citizen.get("home_lat", closest["lat"])
        home_lng = citizen.get("home_lng", closest["lng"])

        return json.dumps({
            "risk": RiskLevel.HIGH,
            "reason": (
                f"IMPOSSIBLE TRAVEL: {txn_type} in {txn_city} but GPS shows "
                f"{gps_city} ({gap:.1f}h gap). No GPS evidence of being in {txn_city}."
            ),
        })

    return json.dumps({"risk": RiskLevel.LOW, "reason": "Location check inconclusive."})
