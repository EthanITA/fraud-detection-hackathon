# %% imports
import json
from collections import defaultdict

import numpy as np
import pandas as pd

# %% paths
TRAIN = "challenges/1. The Truman Show - train"
VALID = "challenges/1. The Truman Show - validation"

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
user_df = pd.DataFrame(users)
user_df["city"] = user_df["residence"].apply(lambda r: r["city"])
user_df["lat"] = user_df["residence"].apply(lambda r: float(r["lat"]))
user_df["lng"] = user_df["residence"].apply(lambda r: float(r["lng"]))

# Build biotag → user mapping from location data
biotags = {loc["biotag"] for loc in locations}
iban_to_name = {u["iban"]: f"{u['first_name']} {u['last_name']}" for u in users}
iban_to_city = {u["iban"]: u["residence"]["city"] for u in users}

print("\n=== Users ===")
for u in users:
    print(f"  {u['first_name']} {u['last_name']}")
    print(f"    Job: {u['job']}, Salary: €{u['salary']:,}")
    print(f"    City: {u['residence']['city']}, IBAN: {u['iban']}")
    print()

# %% biotag ↔ user mapping
# Biotags encode user identity: RGNR-LNAA = Regnier Alain, GRSC-KRLH = Girschner Karl-Hermann, etc.
biotag_to_iban = {}
for u in users:
    for b in biotags:
        # Match by checking if the IBAN appears in transactions with this biotag as sender
        mask = txns_train["sender_id"] == b
        if mask.any():
            sender_iban = txns_train.loc[mask, "sender_iban"].iloc[0]
            if sender_iban == u["iban"]:
                biotag_to_iban[b] = u["iban"]
                print(f"  {b} → {u['first_name']} {u['last_name']}")

# %% transaction type breakdown
print("\n=== Transaction Types (Train) ===")
print(txns_train["transaction_type"].value_counts().to_string())
print(f"\n=== Payment Methods ===")
print(txns_train["payment_method"].dropna().value_counts().to_string())

# %% per-user transaction summary
print("\n=== Per-User Transaction Summary (Train) ===")
for iban, name in iban_to_name.items():
    user_txns = txns_train[
        (txns_train["sender_iban"] == iban) | (txns_train["recipient_iban"] == iban)
    ]
    sent = txns_train[txns_train["sender_iban"] == iban]
    received = txns_train[txns_train["recipient_iban"] == iban]
    print(f"\n  {name} ({iban_to_city[iban]})")
    print(f"    Total transactions: {len(user_txns)}")
    print(f"    Sent: {len(sent)} (total: €{sent['amount'].sum():,.2f})")
    print(f"    Received: {len(received)} (total: €{received['amount'].sum():,.2f})")
    if len(sent) > 0:
        print(
            f"    Avg sent: €{sent['amount'].mean():,.2f}, Max: €{sent['amount'].max():,.2f}"
        )

# %% monthly spending patterns
print("\n=== Monthly Spending by User (Train) ===")
txns_train["month"] = txns_train["timestamp"].dt.to_period("M")
for iban, name in iban_to_name.items():
    sent = txns_train[txns_train["sender_iban"] == iban].copy()
    if len(sent) == 0:
        continue
    monthly = sent.groupby("month")["amount"].agg(["sum", "count", "mean"])
    print(f"\n  {name}:")
    print(monthly.to_string(float_format=lambda x: f"€{x:,.2f}"))

# %% salary analysis — regularity and amounts
print("\n=== Salary Payments ===")
salaries = txns_train[txns_train["description"].str.contains("Salary", na=False)]
for iban, name in iban_to_name.items():
    user_sal = salaries[salaries["recipient_iban"] == iban]
    if len(user_sal) == 0:
        continue
    print(f"\n  {name}: {len(user_sal)} salary payments")
    print(f"    Mean: €{user_sal['amount'].mean():,.2f}")
    print(f"    Std:  €{user_sal['amount'].std():,.2f}")
    print(
        f"    Range: €{user_sal['amount'].min():,.2f} – €{user_sal['amount'].max():,.2f}"
    )
    # Check timing regularity
    dates = user_sal["timestamp"].sort_values()
    gaps = dates.diff().dt.days.dropna()
    print(f"    Payment gap (days): mean={gaps.mean():.1f}, std={gaps.std():.1f}")

# %% rent analysis
print("\n=== Rent Payments ===")
rents = txns_train[txns_train["description"].str.contains("Rent", na=False)]
for iban, name in iban_to_name.items():
    user_rent = rents[rents["sender_iban"] == iban]
    if len(user_rent) == 0:
        continue
    print(f"\n  {name}: {len(user_rent)} rent payments")
    print(f"    Mean: €{user_rent['amount'].mean():,.2f}")
    print(f"    Std:  €{user_rent['amount'].std():,.2f}")
    print(f"    To: {user_rent['description'].iloc[0]}")

# %% balance trajectory
print("\n=== Balance Trajectory ===")
for iban, name in iban_to_name.items():
    user_txns = txns_train[txns_train["sender_iban"] == iban].sort_values("timestamp")
    if len(user_txns) == 0:
        continue
    balances = user_txns["balance_after"].values
    print(
        f"  {name}: start={balances[0]:,.2f} → end={balances[-1]:,.2f} (Δ={balances[-1]-balances[0]:+,.2f})"
    )

# %% location analysis — home vs away
print("\n=== Location Analysis ===")
loc_df = pd.DataFrame(locations)
loc_df["timestamp"] = pd.to_datetime(loc_df["timestamp"])
loc_df["hour"] = loc_df["timestamp"].dt.hour

for biotag in sorted(biotags):
    user_locs = loc_df[loc_df["biotag"] == biotag]
    city_counts = user_locs["city"].value_counts()
    home_city = city_counts.index[0]
    away_pct = (1 - city_counts.iloc[0] / len(user_locs)) * 100
    print(f"\n  {biotag} (home: {home_city})")
    print(f"    Total pings: {len(user_locs)}")
    print(f"    Cities visited: {len(city_counts)}")
    print(f"    Away from home: {away_pct:.1f}%")
    if len(city_counts) > 1:
        print(f"    Other cities: {dict(city_counts.iloc[1:])}")

# %% time-of-day location pattern (nighttime = likely home)
print("\n=== Nighttime Location (22:00–06:00) ===")
for biotag in sorted(biotags):
    night = loc_df[
        (loc_df["biotag"] == biotag) & ((loc_df["hour"] >= 22) | (loc_df["hour"] < 6))
    ]
    if len(night) > 0:
        print(f"  {biotag}: {night['city'].value_counts().to_dict()}")

# %% e-commerce & in-person purchases
print("\n=== Non-recurring Purchases (Train) ===")
purchases = txns_train[
    txns_train["transaction_type"].isin(["e-commerce", "in-person payment"])
]
for _, row in purchases.iterrows():
    sender_name = iban_to_name.get(row["sender_iban"], row["sender_id"])
    print(
        f"  {sender_name}: €{row['amount']:.2f} at {row['location']} via {row['payment_method']} ({row['timestamp']})"
    )

# %% SMS content analysis
print("\n=== SMS Summary ===")
sms_by_recipient = defaultdict(list)
for s in sms:
    text = s["sms"]
    # Extract "To:" line
    for line in text.split("\n"):
        if line.startswith("To:"):
            sms_by_recipient[line].append(text)
            break

for to, messages in sms_by_recipient.items():
    print(f"\n  {to}: {len(messages)} messages")
    # Check for suspicious patterns
    for msg in messages[:2]:
        first_line = (
            msg.split("Message:")[1].strip()[:120] if "Message:" in msg else msg[:120]
        )
        print(f"    → {first_line}")

# %% mail content summary
print("\n=== Email Summary ===")
for m in mails:
    text = m["mail"]
    subject_line = [l for l in text.split("\n") if l.startswith("Subject:")][0]
    to_line = [l for l in text.split("\n") if l.startswith("To:")][0]
    print(f"  {to_line.strip()}")
    print(f"    {subject_line.strip()}")
    print()

# %% compare train vs validation — structural differences
print("\n=== Train vs Validation Comparison ===")
print(f"Train transactions: {len(txns_train)}")
print(f"Validation transactions: {len(txns_valid)}")

# Check if same users appear
train_ibans = set(txns_train["sender_iban"].dropna()) | set(
    txns_train["recipient_iban"].dropna()
)
valid_ibans = set(txns_valid["sender_iban"].dropna()) | set(
    txns_valid["recipient_iban"].dropna()
)
print(f"\nIBANs only in train: {train_ibans - valid_ibans}")
print(f"IBANs only in validation: {valid_ibans - train_ibans}")
print(f"Shared IBANs: {len(train_ibans & valid_ibans)}")

# Transaction type distribution comparison
print("\nType distribution:")
print("  Train:", txns_train["transaction_type"].value_counts().to_dict())
print("  Valid:", txns_valid["transaction_type"].value_counts().to_dict())

# %% load validation users + locations
with open(f"{VALID}/users.json") as f:
    valid_users = json.load(f)
with open(f"{VALID}/locations.json") as f:
    valid_locs = pd.DataFrame(json.load(f))
    valid_locs["timestamp"] = pd.to_datetime(valid_locs["timestamp"])

valid_iban_to_name = {
    u["iban"]: f"{u['first_name']} {u['last_name']}" for u in valid_users
}
valid_iban_to_city = {u["iban"]: u["residence"]["city"] for u in valid_users}

print("\n=== Validation Users ===")
for u in valid_users:
    print(
        f"  {u['first_name']} {u['last_name']} — {u['job']} — {u['residence']['city']}"
    )

# %% validation per-user summary
print("\n=== Per-User Validation Summary ===")
for iban, name in valid_iban_to_name.items():
    sent = txns_valid[txns_valid["sender_iban"] == iban]
    received = txns_valid[txns_valid["recipient_iban"] == iban]
    print(f"\n  {name} ({valid_iban_to_city[iban]})")
    print(f"    Sent: {len(sent)} txns (€{sent['amount'].sum():,.2f})")
    print(f"    Received: {len(received)} txns (€{received['amount'].sum():,.2f})")
    if len(sent) > 0:
        print(f"    Types: {sent['transaction_type'].value_counts().to_dict()}")
        print(
            f"    Avg: €{sent['amount'].mean():,.2f}, Max: €{sent['amount'].max():,.2f}"
        )

# %% validation anomaly candidates — self-referential (per-user baseline from own transactions)
print("\n=== Validation: Anomaly Candidates ===")
print("(Baselines built from each validation user's own recurring patterns)")

# Build per-user baselines from validation data itself
valid_baselines = {}
for iban in valid_iban_to_name:
    sent = txns_valid[txns_valid["sender_iban"] == iban]
    if len(sent) < 3:
        continue
    # Use salary/rent transfers as baseline, flag outliers
    recurring = sent[sent["description"].str.contains("Salary|Rent", na=False)]
    non_recurring = sent[~sent["description"].str.contains("Salary|Rent", na=False)]
    valid_baselines[iban] = {
        "recurring_mean": recurring["amount"].mean() if len(recurring) > 0 else 0,
        "recurring_std": recurring["amount"].std() if len(recurring) > 1 else 0,
        "all_mean": sent["amount"].mean(),
        "all_std": sent["amount"].std(),
        "recipients": set(sent["recipient_iban"].dropna()),
        "types": set(sent["transaction_type"]),
        "non_recurring": non_recurring,
    }

# Also build a global baseline from train data patterns
train_patterns = {
    "salary_gap_days": [],
    "rent_amounts": [],
    "salary_amounts": [],
}
for iban in iban_to_name:
    sal = txns_train[
        (txns_train["recipient_iban"] == iban)
        & txns_train["description"].str.contains("Salary", na=False)
    ]
    if len(sal) > 1:
        gaps = sal["timestamp"].sort_values().diff().dt.days.dropna()
        train_patterns["salary_gap_days"].extend(gaps.tolist())
        train_patterns["salary_amounts"].extend(sal["amount"].tolist())
    rent = txns_train[
        (txns_train["sender_iban"] == iban)
        & txns_train["description"].str.contains("Rent", na=False)
    ]
    if len(rent) > 0:
        train_patterns["rent_amounts"].extend(rent["amount"].tolist())

print(
    f"\n  Train salary gap: {np.mean(train_patterns['salary_gap_days']):.1f} ± {np.std(train_patterns['salary_gap_days']):.1f} days"
)
print(
    f"  Train salary range: €{np.min(train_patterns['salary_amounts']):,.2f} – €{np.max(train_patterns['salary_amounts']):,.2f}"
)

# Flag validation transactions
for _, row in txns_valid.iterrows():
    flags = []
    iban = row["sender_iban"]

    # Check salary timing
    if pd.notna(row["description"]) and "Salary" in row["description"]:
        user_sals = txns_valid[
            (txns_valid["recipient_iban"] == row.get("recipient_iban", ""))
            & txns_valid["description"].str.contains("Salary", na=False)
        ].sort_values("timestamp")
        if len(user_sals) > 1:
            idx = (
                user_sals.index.get_loc(row.name) if row.name in user_sals.index else -1
            )
            if idx > 0:
                gap = (row["timestamp"] - user_sals.iloc[idx - 1]["timestamp"]).days
                if gap < 20 or gap > 40:
                    flags.append(f"salary gap {gap} days (expected ~30)")

    # Check for unusual transaction types per user
    if iban in valid_baselines:
        b = valid_baselines[iban]
        # Large amount relative to user's own spending
        if b["all_std"] > 0 and row["amount"] > b["all_mean"] + 2 * b["all_std"]:
            flags.append(
                f"high amount €{row['amount']:.2f} vs user avg €{b['all_mean']:.2f}±{b['all_std']:.2f}"
            )

    if flags:
        sender_name = valid_iban_to_name.get(iban, row["sender_id"])
        print(f"\n  ⚠ {row['transaction_id'][:12]}... ({sender_name})")
        print(
            f"    €{row['amount']:.2f} | {row['transaction_type']} | {row['timestamp']}"
        )
        if pd.notna(row.get("description")):
            print(f"    Desc: {row['description']}")
        for flag in flags:
            print(f"    → {flag}")

# %% location vs transaction cross-check
print("\n=== Location vs Transaction Cross-Check ===")
# For in-person payments, check if the user was actually near the payment location
in_person = txns_train[txns_train["transaction_type"] == "in-person payment"]
for _, row in in_person.iterrows():
    biotag = row["sender_id"]
    tx_time = row["timestamp"]
    # Find closest location ping
    user_locs = loc_df[loc_df["biotag"] == biotag].copy()
    user_locs["time_diff"] = abs((user_locs["timestamp"] - tx_time).dt.total_seconds())
    closest = user_locs.nsmallest(1, "time_diff")
    if len(closest) > 0:
        c = closest.iloc[0]
        print(f"  {biotag}: paid at {row['location']} ({tx_time})")
        print(f"    Closest ping: {c['city']} ({c['time_diff']/60:.0f} min away)")
        print(f"    Location: {row['location']}")

# Do same for validation
print("\n  --- Validation ---")

in_person_v = txns_valid[txns_valid["transaction_type"] == "in-person payment"]
for _, row in in_person_v.iterrows():
    biotag = row["sender_id"]
    tx_time = row["timestamp"]
    user_locs = valid_locs[valid_locs["biotag"] == biotag].copy()
    if len(user_locs) == 0:
        print(f"  ⚠ {biotag}: no location data for in-person payment!")
        continue
    user_locs["time_diff"] = abs((user_locs["timestamp"] - tx_time).dt.total_seconds())
    closest = user_locs.nsmallest(1, "time_diff")
    c = closest.iloc[0]
    print(f"  {biotag}: paid at {row['location']} ({tx_time})")
    print(f"    Closest ping: {c['city']} ({c['time_diff']/60:.0f} min away)")

# %% direct debit analysis
print("\n=== Direct Debits (Subscriptions) ===")
dd = txns_train[txns_train["transaction_type"] == "direct debit"]
for _, row in dd.iterrows():
    sender_name = iban_to_name.get(row["sender_iban"], row["sender_id"])
    print(
        f"  {sender_name}: €{row['amount']:.2f} — {row['description']} ({row['timestamp']})"
    )

dd_v = txns_valid[txns_valid["transaction_type"] == "direct debit"]
print("\n  --- Validation ---")
for _, row in dd_v.iterrows():
    sender_name = iban_to_name.get(row["sender_iban"], row["sender_id"])
    print(
        f"  {sender_name}: €{row['amount']:.2f} — {row['description']} ({row['timestamp']})"
    )
