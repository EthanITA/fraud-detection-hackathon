# %% imports
import json
import csv
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

# %% paths
TRAIN = "challenges/2. Brave New World - train"
VALID = "challenges/2. Brave New World - validation"

# %% load data
with open(f"{TRAIN}/users.json") as f:
    users = json.load(f)

with open(f"{TRAIN}/locations.json") as f:
    locations = json.load(f)

with open(f"{TRAIN}/sms.json") as f:
    sms = json.load(f)

with open(f"{TRAIN}/mails.json") as f:
    mails = json.load(f)

txns_train = pd.read_csv(f"{TRAIN}/transactions.csv", parse_dates=["timestamp"])
txns_valid = pd.read_csv(f"{VALID}/transactions.csv", parse_dates=["timestamp"])

print(f"Users: {len(users)}")
print(f"Train transactions: {len(txns_train)}")
print(f"Validation transactions: {len(txns_valid)}")
print(f"Location pings: {len(locations)}")
print(f"SMS messages: {len(sms)}")
print(f"Emails: {len(mails)}")

# %% user profiles
iban_to_name = {u["iban"]: f"{u['first_name']} {u['last_name']}" for u in users}
iban_to_city = {u["iban"]: u["residence"]["city"] for u in users}
iban_to_user = {u["iban"]: u for u in users}

print("\n=== Users (7) ===")
for u in users:
    print(f"  {u['first_name']} {u['last_name']} (age ~{2087 - u['birth_year']})")
    print(f"    Job: {u['job']}, Salary: €{u['salary']:,}")
    print(f"    City: {u['residence']['city']}, IBAN: {u['iban']}")
    print()

# %% biotag mapping
loc_df = pd.DataFrame(locations)
loc_df["timestamp"] = pd.to_datetime(loc_df["timestamp"])
loc_df["hour"] = loc_df["timestamp"].dt.hour

biotags = sorted(loc_df["biotag"].unique())
biotag_to_iban = {}
all_user_ibans = set(iban_to_name.keys())
# Biotag format: SURNAME[4]-FIRSTNAME[4]-HEX-CITY[3]-N
# e.g. RTZO-JMIX-7D1-GAU-0 = Ortiz Jim (Gautier)
for b in biotags:
    mask = txns_train["sender_id"] == b
    if mask.any():
        # Some users have multiple IBANs — pick the one that matches users.json
        sender_ibans = set(txns_train.loc[mask, "sender_iban"].unique())
        match = sender_ibans & all_user_ibans
        if match:
            biotag_to_iban[b] = match.pop()
        else:
            biotag_to_iban[b] = txns_train.loc[mask, "sender_iban"].iloc[0]
    name = iban_to_name.get(biotag_to_iban.get(b), "?")
    # Note extra IBANs (potential fraud signal)
    if mask.any():
        extra = set(txns_train.loc[mask, "sender_iban"].unique()) - {biotag_to_iban[b]}
        extra_note = f" (also uses: {extra})" if extra else ""
    else:
        extra_note = ""
    print(f"  {b} → {name}{extra_note}")

# %% transaction type breakdown
print("\n=== Transaction Types ===")
print("Train:")
print(txns_train["transaction_type"].value_counts().to_string())
print("\nValidation:")
print(txns_valid["transaction_type"].value_counts().to_string())

print(f"\n=== Payment Methods ===")
print("Train:", txns_train["payment_method"].dropna().value_counts().to_dict())
print("Valid:", txns_valid["payment_method"].dropna().value_counts().to_dict())

# %% per-user transaction summary
print("\n=== Per-User Transaction Summary (Train) ===")
for iban, name in iban_to_name.items():
    sent = txns_train[txns_train["sender_iban"] == iban]
    received = txns_train[txns_train["recipient_iban"] == iban]
    city = iban_to_city[iban]
    salary = iban_to_user[iban]["salary"]
    monthly_salary = salary / 12
    total_sent = sent["amount"].sum()
    total_received = received["amount"].sum()

    print(f"\n  {name} ({city}) — salary €{salary:,}/yr (€{monthly_salary:,.0f}/mo)")
    print(f"    Sent: {len(sent)} txns (€{total_sent:,.2f})")
    print(f"    Received: {len(received)} txns (€{total_received:,.2f})")
    if len(sent) > 0:
        print(f"    Avg sent: €{sent['amount'].mean():,.2f}, Max: €{sent['amount'].max():,.2f}")
        # Spending types
        print(f"    Types: {sent['transaction_type'].value_counts().to_dict()}")

# %% monthly spending per user
print("\n=== Monthly Spending by User ===")
txns_train["month"] = txns_train["timestamp"].dt.to_period("M")

for iban, name in iban_to_name.items():
    sent = txns_train[txns_train["sender_iban"] == iban].copy()
    if len(sent) == 0:
        continue
    monthly = sent.groupby("month")["amount"].agg(["sum", "count", "mean"])
    print(f"\n  {name}:")
    print(monthly.to_string(float_format=lambda x: f"€{x:,.2f}"))

# %% salary regularity analysis
print("\n=== Salary Payments ===")
salaries = txns_train[txns_train["description"].str.contains("Salary", na=False)]
for iban, name in iban_to_name.items():
    user_sal = salaries[salaries["recipient_iban"] == iban]
    if len(user_sal) == 0:
        continue
    print(f"\n  {name}: {len(user_sal)} salary payments")
    print(f"    Mean: €{user_sal['amount'].mean():,.2f}, Std: €{user_sal['amount'].std():,.2f}")
    print(f"    Range: €{user_sal['amount'].min():,.2f} – €{user_sal['amount'].max():,.2f}")
    dates = user_sal["timestamp"].sort_values()
    gaps = dates.diff().dt.days.dropna()
    if len(gaps) > 0:
        print(f"    Gap (days): mean={gaps.mean():.1f}, std={gaps.std():.1f}")
    # Expected vs actual
    expected_monthly = iban_to_user[iban]["salary"] / 12
    print(f"    Expected monthly: €{expected_monthly:,.2f}")

# %% rent analysis
print("\n=== Rent Payments ===")
rents = txns_train[txns_train["description"].str.contains("Rent", na=False)]
for iban, name in iban_to_name.items():
    user_rent = rents[rents["sender_iban"] == iban]
    if len(user_rent) == 0:
        continue
    print(f"\n  {name}: {len(user_rent)} rent payments")
    print(f"    Mean: €{user_rent['amount'].mean():,.2f}, Std: €{user_rent['amount'].std():,.2f}")
    descs = user_rent["description"].unique()
    for d in descs:
        print(f"    → {d}")

# %% balance trajectory
print("\n=== Balance Trajectory ===")
for iban, name in iban_to_name.items():
    user_txns = txns_train[txns_train["sender_iban"] == iban].sort_values("timestamp")
    if len(user_txns) == 0:
        continue
    balances = user_txns["balance_after"].values
    print(f"  {name}: {balances[0]:,.2f} → {balances[-1]:,.2f} (Δ={balances[-1]-balances[0]:+,.2f})")

# %% location analysis — home vs away per user
print("\n=== Location Analysis ===")
for biotag in biotags:
    iban = biotag_to_iban.get(biotag)
    name = iban_to_name.get(iban, biotag) if iban else biotag

    user_locs = loc_df[loc_df["biotag"] == biotag]
    city_counts = user_locs["city"].value_counts()
    home_city = city_counts.index[0]
    away_pct = (1 - city_counts.iloc[0] / len(user_locs)) * 100

    print(f"\n  {name} (biotag: {biotag})")
    print(f"    Home city: {home_city}")
    print(f"    Total pings: {len(user_locs)}, away: {away_pct:.1f}%")
    if len(city_counts) > 1:
        others = city_counts.iloc[1:].head(5)
        print(f"    Other cities: {dict(others)}")

# %% haversine distance utility
def haversine(lat1, lng1, lat2, lng2):
    """Distance in km between two (lat, lng) points."""
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))

# %% travel speed analysis — detect impossible movements
print("\n=== Travel Speed Analysis (potential teleportation) ===")
for biotag in biotags:
    user_locs = loc_df[loc_df["biotag"] == biotag].sort_values("timestamp").reset_index(drop=True)
    if len(user_locs) < 2:
        continue

    suspicious = []
    for i in range(1, len(user_locs)):
        prev = user_locs.iloc[i - 1]
        curr = user_locs.iloc[i]
        dist = haversine(prev["lat"], prev["lng"], curr["lat"], curr["lng"])
        time_h = (curr["timestamp"] - prev["timestamp"]).total_seconds() / 3600
        if time_h > 0 and dist > 10:  # >10km movement
            speed = dist / time_h
            if speed > 500:  # >500 km/h = suspicious
                suspicious.append((prev["timestamp"], curr["timestamp"], dist, speed, prev["city"], curr["city"]))

    if suspicious:
        name = iban_to_name.get(biotag_to_iban.get(biotag), biotag)
        print(f"\n  {name} ({biotag}): {len(suspicious)} suspicious movements")
        for s in suspicious[:5]:
            print(f"    {s[4]} → {s[5]}: {s[2]:.0f}km in {s[2]/s[3]*60:.0f}min ({s[3]:.0f} km/h)")

# %% e-commerce and in-person purchases
print("\n=== Discretionary Purchases (Train) ===")
purchases = txns_train[txns_train["transaction_type"].isin(["e-commerce", "in-person payment"])]
for _, row in purchases.iterrows():
    sender_name = iban_to_name.get(row["sender_iban"], row["sender_id"])
    loc = row["location"] if pd.notna(row["location"]) else "online"
    method = row["payment_method"] if pd.notna(row["payment_method"]) else ""
    print(f"  {sender_name}: €{row['amount']:.2f} at {loc} via {method}")

# %% direct debits / subscriptions
print("\n=== Direct Debits / Subscriptions (Train) ===")
dd = txns_train[txns_train["transaction_type"] == "direct debit"]
for iban, name in iban_to_name.items():
    user_dd = dd[dd["sender_iban"] == iban]
    if len(user_dd) == 0:
        continue
    print(f"\n  {name}: {len(user_dd)} direct debits")
    for _, row in user_dd.iterrows():
        print(f"    €{row['amount']:.2f} — {row['description']} ({row['timestamp'].strftime('%Y-%m')})")

# %% withdrawals
print("\n=== Withdrawals (Train) ===")
withdrawals = txns_train[txns_train["transaction_type"] == "withdrawal"]
if len(withdrawals) > 0:
    for _, row in withdrawals.iterrows():
        sender_name = iban_to_name.get(row["sender_iban"], row["sender_id"])
        print(f"  {sender_name}: €{row['amount']:.2f} at {row['location']} ({row['timestamp']})")
else:
    print("  No withdrawals in training data")

# Check validation
withdrawals_v = txns_valid[txns_valid["transaction_type"] == "withdrawal"]
if len(withdrawals_v) > 0:
    print(f"\n  Validation withdrawals: {len(withdrawals_v)}")
    for _, row in withdrawals_v.iterrows():
        sender_name = iban_to_name.get(row["sender_iban"], row["sender_id"])
        print(f"  {sender_name}: €{row['amount']:.2f} at {row['location']} ({row['timestamp']})")

# %% SMS analysis per user
print("\n=== SMS Summary ===")
sms_by_phone = defaultdict(list)
for s in sms:
    text = s["sms"]
    for line in text.split("\n"):
        if line.startswith("To:"):
            sms_by_phone[line.strip()].append(text)
            break

for phone, messages in sms_by_phone.items():
    print(f"\n  {phone}: {len(messages)} messages")
    # Categorize
    categories = Counter()
    for msg in messages:
        body = msg.split("Message:")[-1].strip().lower() if "Message:" in msg else msg.lower()
        if any(w in body for w in ["alert", "warning", "urgent", "suspicious"]):
            categories["alert"] += 1
        elif any(w in body for w in ["reminder", "appointment", "scheduled"]):
            categories["reminder"] += 1
        elif any(w in body for w in ["delivery", "shipped", "package"]):
            categories["delivery"] += 1
        else:
            categories["other"] += 1
    print(f"    Categories: {dict(categories)}")
    # Show first 2
    for msg in messages[:2]:
        body = msg.split("Message:")[-1].strip()[:120] if "Message:" in msg else msg[:120]
        print(f"    → {body}")

# %% email analysis
print("\n=== Email Summary ===")
for m in mails:
    text = m["mail"]
    subject = next((l for l in text.split("\n") if l.startswith("Subject:")), "")
    to = next((l for l in text.split("\n") if l.startswith("To:")), "")
    print(f"  {to.strip()}")
    print(f"    {subject.strip()}")

# %% train vs validation structural comparison
print("\n=== Train vs Validation Comparison ===")
train_senders = set(txns_train["sender_id"].unique())
valid_senders = set(txns_valid["sender_id"].unique())
train_ibans = set(txns_train["sender_iban"].dropna()) | set(txns_train["recipient_iban"].dropna())
valid_ibans = set(txns_valid["sender_iban"].dropna()) | set(txns_valid["recipient_iban"].dropna())

print(f"Senders only in validation: {valid_senders - train_senders}")
print(f"New IBANs in validation: {len(valid_ibans - train_ibans)}")
print(f"Shared IBANs: {len(train_ibans & valid_ibans)}")

# Type distribution comparison
print("\nType distribution:")
for t in sorted(set(txns_train["transaction_type"]) | set(txns_valid["transaction_type"])):
    tc = len(txns_train[txns_train["transaction_type"] == t])
    vc = len(txns_valid[txns_valid["transaction_type"] == t])
    print(f"  {t}: train={tc}, valid={vc}")

# %% anomaly scoring — build baselines from train, flag validation outliers
print("\n=== Validation Anomaly Candidates ===")

# Build per-user baselines
baselines = {}
for iban in iban_to_name:
    sent = txns_train[txns_train["sender_iban"] == iban]
    if len(sent) == 0:
        continue
    by_type = {}
    for t, group in sent.groupby("transaction_type"):
        by_type[t] = {
            "mean": group["amount"].mean(),
            "std": group["amount"].std(),
            "max": group["amount"].max(),
            "recipients": set(group["recipient_iban"].dropna()),
        }
    baselines[iban] = {
        "overall_mean": sent["amount"].mean(),
        "overall_std": sent["amount"].std(),
        "overall_max": sent["amount"].max(),
        "by_type": by_type,
        "known_recipients": set(sent["recipient_iban"].dropna()),
        "known_types": set(sent["transaction_type"]),
        "known_locations": set(sent["location"].dropna()),
    }

flagged = []
for _, row in txns_valid.iterrows():
    iban = row["sender_iban"]
    if iban not in baselines:
        continue

    b = baselines[iban]
    flags = []

    # Amount anomaly (> 2σ from mean, per-type)
    tx_type = row["transaction_type"]
    if tx_type in b["by_type"]:
        tb = b["by_type"][tx_type]
        if tb["std"] > 0 and abs(row["amount"] - tb["mean"]) > 2 * tb["std"]:
            flags.append(f"amount €{row['amount']:.2f} vs type-baseline €{tb['mean']:.2f}±{tb['std']:.2f}")
    elif b["overall_std"] > 0 and abs(row["amount"] - b["overall_mean"]) > 2 * b["overall_std"]:
        flags.append(f"amount €{row['amount']:.2f} vs overall-baseline €{b['overall_mean']:.2f}±{b['overall_std']:.2f}")

    # New recipient
    if pd.notna(row["recipient_iban"]) and row["recipient_iban"] not in b["known_recipients"]:
        flags.append(f"new recipient: {row['recipient_iban'][:20]}...")

    # New transaction type
    if tx_type not in b["known_types"]:
        flags.append(f"new transaction type: {tx_type}")

    # New location
    if pd.notna(row["location"]) and row["location"] not in b["known_locations"]:
        flags.append(f"new location: {row['location']}")

    if flags:
        name = iban_to_name.get(iban, row["sender_id"])
        flagged.append((row["transaction_id"], name, row["amount"], tx_type, len(flags), flags))
        print(f"\n  ⚠ {row['transaction_id'][:12]}... ({name})")
        print(f"    €{row['amount']:.2f} | {tx_type} | {row['timestamp']}")
        if pd.notna(row["description"]):
            print(f"    Desc: {row['description']}")
        for flag in flags:
            print(f"    → {flag}")

print(f"\n  Total flagged: {len(flagged)} / {len(txns_valid)} validation transactions")

# %% location vs in-person payment cross-check (validation)
print("\n=== Location vs In-Person Payment Cross-Check (Validation) ===")
with open(f"{VALID}/locations.json") as f:
    valid_locs = pd.DataFrame(json.load(f))
    valid_locs["timestamp"] = pd.to_datetime(valid_locs["timestamp"])

in_person_v = txns_valid[txns_valid["transaction_type"] == "in-person payment"]
for _, row in in_person_v.iterrows():
    biotag = row["sender_id"]
    tx_time = row["timestamp"]
    iban = row["sender_iban"]
    name = iban_to_name.get(iban, biotag)

    user_locs = valid_locs[valid_locs["biotag"] == biotag].copy()
    if len(user_locs) == 0:
        print(f"  ⚠ {name}: NO location data for in-person payment at {row['location']}!")
        continue

    user_locs["time_diff"] = abs((user_locs["timestamp"] - tx_time).dt.total_seconds())
    closest = user_locs.nsmallest(1, "time_diff").iloc[0]

    # Check city match with payment location
    payment_loc = row["location"] if pd.notna(row["location"]) else "?"
    city_match = closest["city"].lower() in payment_loc.lower() if pd.notna(row["location"]) else None

    status = "✓" if city_match else "⚠" if city_match is False else "?"
    print(f"  {status} {name}: paid at {payment_loc}")
    print(f"    Closest ping: {closest['city']} ({closest['time_diff']/60:.0f}min gap)")
    if not city_match and city_match is not None:
        # Calculate distance between home and payment location
        home = iban_to_user[iban]["residence"]
        dist = haversine(float(home["lat"]), float(home["lng"]), closest["lat"], closest["lng"])
        print(f"    ⚠ City mismatch! Ping {dist:.0f}km from home")

# %% recipient network analysis
print("\n=== Recipient Network ===")
for iban, name in iban_to_name.items():
    sent = txns_train[txns_train["sender_iban"] == iban]
    recipients = sent.groupby("recipient_iban")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False)
    print(f"\n  {name} sends to {len(recipients)} recipients:")
    for r_iban, row in recipients.iterrows():
        r_name = iban_to_name.get(r_iban, r_iban[:20] + "...")
        desc = sent[sent["recipient_iban"] == r_iban]["description"].dropna().iloc[0] if len(sent[sent["recipient_iban"] == r_iban]["description"].dropna()) > 0 else ""
        print(f"    {r_name}: {int(row['count'])}x = €{row['sum']:,.2f} ({desc})")
