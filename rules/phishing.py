# %% imports
from __future__ import annotations

import json
import re
from datetime import datetime

from langchain.tools import tool

from ._types import RiskLevel


# %% _parse_sms_date
def _parse_sms_date(text: str) -> datetime | None:
    m = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", text)
    if m:
        try:
            return datetime.fromisoformat(m.group(1))
        except ValueError:
            pass
    return None


# %% _is_phishing
PHISHING_KEYWORDS = [
    "verify your", "click here", "suspend", "urgent", "confirm your",
    "unusual activity", "act now", "security alert", "unauthorized",
    "locked", "suspicious", "compromised", "expire",
]

def _is_phishing(text: str) -> bool:
    lower = text.lower()
    return sum(1 for kw in PHISHING_KEYWORDS if kw in lower) >= 1


# %% check_phishing_window
@tool
def check_phishing_window(txn_json: str, citizen_json: str) -> str:
    """
    Correlate transaction timing with phishing SMS/mail events targeting the sender.

    HIGH — e-commerce/withdrawal txn within 7 days after phishing AND recipient unseen
    MEDIUM — any txn within 14 days after phishing

    txn_json:     Transaction (needs: timestamp, transaction_type, sender_id)
    citizen_json: Citizen data (needs: sms.raw_messages or sms data, user.first_name)
    """
    txn = json.loads(txn_json)
    citizen = json.loads(citizen_json)

    txn_type = txn.get("transaction_type", "")
    ts = txn.get("timestamp", 0)
    if not ts:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No timestamp."})

    # Get citizen's first name for SMS matching
    user = citizen if isinstance(citizen, dict) else {}
    first_name = user.get("first_name", "") or ""
    # Also try from parent citizen object
    if not first_name:
        u = user.get("user", {})
        first_name = u.get("first_name", "") if isinstance(u, dict) else ""

    if not first_name:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No citizen identity to match."})

    # Load raw SMS messages from citizen context
    raw_sms = user.get("raw_sms", [])
    raw_mails = user.get("raw_mails", [])

    if not raw_sms and not raw_mails:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No communication data."})

    # Find phishing events targeting this citizen
    phishing_dates: list[float] = []

    for text in raw_sms:
        if first_name.lower() not in text.lower() and first_name not in text:
            continue
        if not _is_phishing(text):
            continue
        dt = _parse_sms_date(text)
        if dt:
            phishing_dates.append(dt.timestamp())

    for text in raw_mails:
        if first_name.lower() not in text.lower():
            continue
        if not _is_phishing(text):
            continue
        # Parse email date
        m = re.search(r"Date:\s*\w+,\s*(\d+\s+\w+\s+\d{4})", text)
        if m:
            try:
                dt = datetime.strptime(m.group(1), "%d %b %Y")
                phishing_dates.append(dt.timestamp())
            except ValueError:
                pass

    if not phishing_dates:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No phishing events detected for this citizen."})

    # Check if any phishing event is within 14 days BEFORE the transaction
    recent_phishing = []
    for pdt in phishing_dates:
        days_before = (ts - pdt) / 86400
        if 0 < days_before <= 14:
            recent_phishing.append(days_before)

    if not recent_phishing:
        return json.dumps({"risk": RiskLevel.LOW, "reason": f"{len(phishing_dates)} phishing events but none within 14d before this txn."})

    closest_days = min(recent_phishing)
    desc = (txn.get("description", "") or "").lower()
    is_salary = "salary" in desc
    is_rent = "rent" in desc

    # Salary/rent are routine — only flag if VERY close to phishing
    if is_salary or is_rent:
        if closest_days <= 2:
            return json.dumps({
                "risk": RiskLevel.MEDIUM,
                "reason": f"Routine {txn_type} but only {closest_days:.1f}d after phishing — possible redirect.",
            })
        return json.dumps({"risk": RiskLevel.LOW, "reason": f"Routine payment, phishing {closest_days:.1f}d before."})

    # Non-routine transaction in phishing window
    if closest_days <= 7:
        return json.dumps({
            "risk": RiskLevel.HIGH,
            "reason": f"PHISHING WINDOW: {txn_type} {closest_days:.1f}d after phishing — likely compromised account.",
        })

    if closest_days <= 14:
        return json.dumps({
            "risk": RiskLevel.MEDIUM,
            "reason": f"Phishing window: {txn_type} {closest_days:.1f}d after phishing event.",
        })

    return json.dumps({
        "risk": RiskLevel.LOW,
        "reason": f"Phishing {closest_days:.1f}d before txn — outside window.",
    })
