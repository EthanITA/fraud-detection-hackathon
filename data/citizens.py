# %% imports
from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path


# %% load_users
def load_users(dir_path: str) -> dict[str, dict]:
    """Load users.json → dict keyed by user_id."""
    p = Path(dir_path) / "users.json"
    if not p.exists():
        return {}
    with open(p) as f:
        users = json.load(f)
    return {u["user_id"]: u for u in users}


# %% load_personas
def load_personas(dir_path: str) -> dict[str, str]:
    """Load personas.md → dict keyed by user_id → full persona text."""
    p = Path(dir_path) / "personas.md"
    if not p.exists():
        return {}
    text = p.read_text()

    personas: dict[str, str] = {}
    # Split on ## USER_ID - Name headers
    blocks = re.split(r"\n## ", text)
    for block in blocks:
        # Match "USER_ID - Name" or "USER_ID — Name" at start of block
        match = re.match(r"([A-Z0-9]{6,12})\s", block)
        if match:
            uid = match.group(1)
            personas[uid] = block.strip()
    return personas


# %% _haversine_km
def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two lat/lng points."""
    R = 6371.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# %% load_locations
def load_locations(dir_path: str) -> dict[str, dict]:
    """Load locations.json → per-user location summary.

    Summary keys: home_city, home_lat, home_lng, visited_cities,
    max_distance_km, travel_frequency, recent_city, total_pings
    """
    p = Path(dir_path) / "locations.json"
    if not p.exists():
        return {}
    with open(p) as f:
        pings = json.load(f)

    by_user: dict[str, list[dict]] = {}
    for ping in pings:
        by_user.setdefault(ping["user_id"], []).append(ping)

    summaries: dict[str, dict] = {}
    for uid, user_pings in by_user.items():
        user_pings.sort(key=lambda x: x["timestamp"])
        cities = [p.get("city", "unknown") for p in user_pings]
        # Home city = most frequent city
        city_counts: dict[str, int] = {}
        for c in cities:
            city_counts[c] = city_counts.get(c, 0) + 1
        home_city = max(city_counts, key=city_counts.get)

        # Home coordinates = average of pings in home city
        home_pings = [p for p in user_pings if p.get("city") == home_city]
        home_lat = sum(p["lat"] for p in home_pings) / len(home_pings)
        home_lng = sum(p["lng"] for p in home_pings) / len(home_pings)

        # Max distance from home
        max_dist = 0.0
        for ping in user_pings:
            d = _haversine_km(home_lat, home_lng, ping["lat"], ping["lng"])
            if d > max_dist:
                max_dist = d

        # Travel = pings outside home city
        foreign_pings = [p for p in user_pings if p.get("city") != home_city]
        foreign_cities = sorted(set(p.get("city", "?") for p in foreign_pings))

        summaries[uid] = {
            "home_city": home_city,
            "home_lat": round(home_lat, 4),
            "home_lng": round(home_lng, 4),
            "visited_cities": foreign_cities,
            "max_distance_km": round(max_dist, 1),
            "travel_pings": len(foreign_pings),
            "total_pings": len(user_pings),
            "recent_city": user_pings[-1].get("city", "unknown"),
        }
    return summaries


# %% load_statuses
def load_statuses(dir_path: str) -> dict[str, dict]:
    """Load status.csv → per-user health/wellness summary.

    Summary keys: event_count, event_types, avg_activity, avg_sleep,
    avg_exposure, activity_trend, sleep_trend, exposure_trend,
    has_specialist_visits, last_event_type, last_event_date
    """
    p = Path(dir_path) / "status.csv"
    if not p.exists():
        return {}
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))

    by_user: dict[str, list[dict]] = {}
    for row in rows:
        uid = row["CitizenID"]
        by_user.setdefault(uid, []).append(row)

    summaries: dict[str, dict] = {}
    for uid, events in by_user.items():
        events.sort(key=lambda x: x["Timestamp"])
        activities = [float(e["PhysicalActivityIndex"]) for e in events]
        sleeps = [float(e["SleepQualityIndex"]) for e in events]
        exposures = [float(e["EnvironmentalExposureLevel"]) for e in events]
        types = set(e["EventType"] for e in events)

        # Trend: compare first half avg to second half avg
        def _trend(vals: list[float]) -> str:
            if len(vals) < 4:
                return "stable"
            mid = len(vals) // 2
            first = sum(vals[:mid]) / mid
            second = sum(vals[mid:]) / (len(vals) - mid)
            diff = (second - first) / (first + 0.01)
            if diff > 0.15:
                return "increasing"
            elif diff < -0.15:
                return "declining"
            return "stable"

        summaries[uid] = {
            "event_count": len(events),
            "event_types": sorted(types),
            "avg_activity": round(sum(activities) / len(activities), 1),
            "avg_sleep": round(sum(sleeps) / len(sleeps), 1),
            "avg_exposure": round(sum(exposures) / len(exposures), 1),
            "activity_trend": _trend(activities),
            "sleep_trend": _trend(sleeps),
            "exposure_trend": _trend(exposures),
            "has_specialist_visits": "specialist consultation" in types,
            "last_event_type": events[-1]["EventType"],
            "last_event_date": events[-1]["Timestamp"],
        }
    return summaries


# %% build_citizen_profiles
def build_citizen_profiles(dir_path: str) -> dict[str, dict]:
    """Master function: load all supplementary data, merge into per-citizen profiles.

    Accepts a directory path. If given a file path, returns empty dict.

    Each citizen profile contains:
    - user: demographics from users.json
    - location: summary from locations.json
    - status: health/wellness summary from status.csv
    - persona: full text from personas.md
    - summary: compact one-line description for specialist context
    """
    if not Path(dir_path).is_dir():
        return {}
    users = load_users(dir_path)
    locations = load_locations(dir_path)
    statuses = load_statuses(dir_path)
    personas = load_personas(dir_path)

    all_ids = set(users) | set(locations) | set(statuses) | set(personas)
    citizens: dict[str, dict] = {}

    for uid in all_ids:
        user = users.get(uid, {})
        loc = locations.get(uid, {})
        status = statuses.get(uid, {})
        persona = personas.get(uid, "")

        # Compact summary for all specialists
        age = 2026 - user.get("birth_year", 2000) if user.get("birth_year") else None
        parts = []
        if age:
            parts.append(f"{age}yo")
        if user.get("job"):
            parts.append(user["job"])
        if loc.get("home_city"):
            parts.append(f"lives in {loc['home_city']}")
        if loc.get("max_distance_km", 0) < 100:
            parts.append("low mobility")
        elif loc.get("max_distance_km", 0) > 1000:
            parts.append("high mobility/travel")
        if status.get("activity_trend") == "declining":
            parts.append("declining health")

        citizens[uid] = {
            "user": user,
            "location": loc,
            "status": status,
            "persona": persona,
            "summary": ", ".join(parts) if parts else "no citizen data",
        }

    return citizens
