# %% imports
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from .audio import transcribe_audio_files


# %% _haversine_km
def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two lat/lng points."""
    R = 6371.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# %% load_users
def load_users(dir_path: str) -> dict[str, dict]:
    """Load users.json → dict keyed by IBAN.

    Reply Mirror format: each user has first_name, last_name, birth_year,
    salary, job, iban, residence {city, lat, lng}, description.
    """
    p = Path(dir_path) / "users.json"
    if not p.exists():
        return {}
    with open(p) as f:
        users = json.load(f)
    return {u["iban"]: u for u in users}


# %% build_iban_to_biotag
def build_iban_to_biotag(dir_path: str) -> dict[str, str]:
    """Build IBAN → biotag mapping from transactions.

    In transactions, sender_id is the biotag and sender_iban is their IBAN.
    We scan all transactions to collect these pairings.
    """
    import csv
    p = Path(dir_path) / "transactions.csv"
    if not p.exists():
        return {}
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))

    mapping: dict[str, str] = {}
    for row in rows:
        iban = row.get("sender_iban", "").strip()
        biotag = row.get("sender_id", "").strip()
        if iban and biotag and "-" in biotag:
            mapping[iban] = biotag
    return mapping


# %% load_locations
def load_locations(dir_path: str) -> dict[str, dict]:
    """Load locations.json → per-biotag location summary.

    Reply Mirror format: each ping has biotag, timestamp, lat, lng, city.
    """
    p = Path(dir_path) / "locations.json"
    if not p.exists():
        return {}
    with open(p) as f:
        pings = json.load(f)

    by_user: dict[str, list[dict]] = {}
    for ping in pings:
        by_user.setdefault(ping["biotag"], []).append(ping)

    summaries: dict[str, dict] = {}
    for biotag, user_pings in by_user.items():
        user_pings.sort(key=lambda x: x["timestamp"])
        cities = [p.get("city", "unknown") for p in user_pings]
        city_counts: dict[str, int] = {}
        for c in cities:
            city_counts[c] = city_counts.get(c, 0) + 1
        home_city = max(city_counts, key=city_counts.get)

        home_pings = [p for p in user_pings if p.get("city") == home_city]
        home_lat = sum(p["lat"] for p in home_pings) / len(home_pings)
        home_lng = sum(p["lng"] for p in home_pings) / len(home_pings)

        max_dist = 0.0
        for ping in user_pings:
            d = _haversine_km(home_lat, home_lng, ping["lat"], ping["lng"])
            if d > max_dist:
                max_dist = d

        foreign_pings = [p for p in user_pings if p.get("city") != home_city]
        foreign_cities = sorted(set(p.get("city", "?") for p in foreign_pings))

        summaries[biotag] = {
            "home_city": home_city,
            "home_lat": round(home_lat, 4),
            "home_lng": round(home_lng, 4),
            "visited_cities": foreign_cities,
            "max_distance_km": round(max_dist, 1),
            "travel_pings": len(foreign_pings),
            "total_pings": len(user_pings),
            "recent_city": user_pings[-1].get("city", "unknown"),
            "pings": [
                {"ts": p["timestamp"], "lat": p["lat"], "lng": p["lng"], "city": p.get("city", "")}
                for p in user_pings
            ],
        }
    return summaries


# %% load_sms
def load_sms(dir_path: str, known_names: list[str] | None = None) -> dict[str, list[str]]:
    """Load sms.json → dict keyed by first name → list of SMS texts.

    Matches by known citizen first names appearing anywhere in the SMS.
    Falls back to regex extraction if no known names provided.
    """
    p = Path(dir_path) / "sms.json"
    if not p.exists():
        return {}
    with open(p) as f:
        messages = json.load(f)

    by_name: dict[str, list[str]] = {}
    for msg in messages:
        text = msg.get("sms", "")
        matched = False
        # Match by known names first (most reliable)
        if known_names:
            for name in known_names:
                if name in text:
                    by_name.setdefault(name, []).append(text)
                    matched = True
                    break
        if not matched:
            by_name.setdefault("_unknown", []).append(text)
    return by_name


# %% load_mails
def load_mails(dir_path: str, known_names: list[str] | None = None) -> dict[str, list[str]]:
    """Load mails.json → dict keyed by first name → list of mail texts.

    Matches by known citizen first names in To: header or body.
    """
    p = Path(dir_path) / "mails.json"
    if not p.exists():
        return {}
    with open(p) as f:
        messages = json.load(f)

    by_name: dict[str, list[str]] = {}
    for msg in messages:
        text = msg.get("mail", "")
        matched = False
        if known_names:
            for name in known_names:
                if name in text:
                    by_name.setdefault(name, []).append(text)
                    matched = True
                    break
        if not matched:
            by_name.setdefault("_unknown", []).append(text)
    return by_name


# %% _classify_comms
def _classify_comms(texts: list[str]) -> dict:
    """Quick classification of SMS/mail content for fraud signals."""
    phishing_keywords = [
        "verify your", "click here", "suspend", "urgent", "confirm your",
        "reset password", "unusual activity", "limited time", "act now",
        "security alert", "unauthorized", "locked",
    ]
    phishing_count = 0
    for text in texts:
        lower = text.lower()
        if any(kw in lower for kw in phishing_keywords):
            phishing_count += 1
    return {
        "total_messages": len(texts),
        "phishing_attempts": phishing_count,
        "phishing_ratio": phishing_count / len(texts) if texts else 0.0,
    }


# %% _classify_audio
def _classify_audio(transcripts: list[dict]) -> dict:
    """Classify audio transcripts for fraud-relevant signals."""
    texts = [t["text"] for t in transcripts]
    stress_keywords = [
        "worried", "scared", "urgent", "help me", "stolen", "hacked",
        "suspicious", "fraud", "scam", "someone called", "pretending",
        "gave them", "transferred", "told me to", "threatened",
        "account compromised", "verify", "password", "pin", "code",
    ]
    stress_count = sum(
        1 for text in texts
        if any(kw in text.lower() for kw in stress_keywords)
    )
    return {
        "total_calls": len(transcripts),
        "stress_signals": stress_count,
        "stress_ratio": stress_count / len(transcripts) if transcripts else 0.0,
    }


# %% build_citizen_profiles
def build_citizen_profiles(dir_path: str) -> dict[str, dict]:
    """Master function: load all supplementary data, merge into per-citizen profiles.

    Identity resolution: biotag (from locations/transactions) is the primary key.
    Users link via IBAN (found in transactions). SMS/mails link via first_name.

    Each citizen profile contains:
    - user: demographics from users.json
    - location: GPS summary from locations.json
    - sms: classified SMS summary
    - mails: classified mail summary
    - description: the user's narrative description (from users.json)
    - summary: compact one-line description for specialist context
    """
    if not Path(dir_path).is_dir():
        return {}

    users_by_iban = load_users(dir_path)
    iban_to_biotag = build_iban_to_biotag(dir_path)
    locations = load_locations(dir_path)

    # Collect known first names for SMS/mail matching
    known_names = [u["first_name"] for u in users_by_iban.values() if u.get("first_name")]
    sms_by_name = load_sms(dir_path, known_names)
    mails_by_name = load_mails(dir_path, known_names)

    # Audio transcripts (keyed by "firstname lastname" lowercase)
    audio_by_name = transcribe_audio_files(dir_path)

    # Build biotag → user mapping via IBAN
    users_by_biotag: dict[str, dict] = {}
    for iban, user in users_by_iban.items():
        biotag = iban_to_biotag.get(iban)
        if biotag:
            users_by_biotag[biotag] = user

    all_biotags = set(users_by_biotag) | set(locations)
    citizens: dict[str, dict] = {}

    for biotag in all_biotags:
        user = users_by_biotag.get(biotag, {})
        loc = locations.get(biotag, {})
        first_name = user.get("first_name", "")

        # Link SMS/mails by first name
        user_sms = sms_by_name.get(first_name, [])
        user_mails = mails_by_name.get(first_name, [])

        # Link audio by full name
        last_name = user.get("last_name", "")
        full_name_key = f"{first_name} {last_name}".lower().strip()
        user_audio = audio_by_name.get(full_name_key, [])

        # Year is 2087 in the challenge
        age = 2087 - user.get("birth_year", 2050) if user.get("birth_year") else None
        parts = []
        if age:
            parts.append(f"{age}yo")
        if user.get("job"):
            parts.append(user["job"])
        if user.get("salary"):
            parts.append(f"€{user['salary']:,}/yr")
        if loc.get("home_city"):
            parts.append(f"lives in {loc['home_city']}")
        if loc.get("max_distance_km", 0) < 100:
            parts.append("low mobility")
        elif loc.get("max_distance_km", 0) > 1000:
            parts.append("high mobility/travel")

        sms_summary = _classify_comms(user_sms)
        mail_summary = _classify_comms(user_mails)
        audio_summary = _classify_audio(user_audio)
        if sms_summary["phishing_ratio"] > 0.1:
            parts.append(f"phishing target ({sms_summary['phishing_attempts']} attempts)")
        if audio_summary["stress_ratio"] > 0.1:
            parts.append(f"stress in calls ({audio_summary['stress_signals']}/{audio_summary['total_calls']})")

        citizens[biotag] = {
            "user": user,
            "location": loc,
            "sms": sms_summary,
            "mails": mail_summary,
            "audio": audio_summary,
            "raw_sms": user_sms,
            "raw_mails": user_mails,
            "raw_audio": [t["text"] for t in user_audio],
            "description": user.get("description", ""),
            "summary": ", ".join(parts) if parts else "no citizen data",
        }

    return citizens
