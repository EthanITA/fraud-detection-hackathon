# %% sample transactions
# Covers: normal, burst, balance drain, round/threshold, fan-in, off-hours, first-large

SAMPLE_TXNS: list[dict] = [
    # --- Normal pair (A001 → A002, regular amounts) ---
    {
        "id": "T001",
        "sender_id": "A001",
        "receiver_id": "A002",
        "amount": 150.0,
        "timestamp": 1700000000.0,
        "sender_balance": 5000.0,
    },
    {
        "id": "T002",
        "sender_id": "A001",
        "receiver_id": "A002",
        "amount": 200.0,
        "timestamp": 1700086400.0,
        "sender_balance": 4800.0,
    },
    # --- Burst: A003 sends 3 txns in 60s ---
    {
        "id": "T003",
        "sender_id": "A003",
        "receiver_id": "A004",
        "amount": 500.0,
        "timestamp": 1700100000.0,
        "sender_balance": 20000.0,
    },
    {
        "id": "T004",
        "sender_id": "A003",
        "receiver_id": "A005",
        "amount": 600.0,
        "timestamp": 1700100030.0,
        "sender_balance": 19500.0,
    },
    {
        "id": "T005",
        "sender_id": "A003",
        "receiver_id": "A006",
        "amount": 550.0,
        "timestamp": 1700100060.0,
        "sender_balance": 18900.0,
    },
    # --- Balance drain: A007 sends 95% of balance ---
    {
        "id": "T006",
        "sender_id": "A007",
        "receiver_id": "A008",
        "amount": 9500.0,
        "timestamp": 1700200000.0,
        "sender_balance": 10000.0,
    },
    # --- Structuring: just below €5k threshold ---
    {
        "id": "T007",
        "sender_id": "A009",
        "receiver_id": "A010",
        "amount": 4999.0,
        "timestamp": 1700300000.0,
        "sender_balance": 50000.0,
    },
    # --- Fan-in: 3 different senders → A011 ---
    {
        "id": "T008",
        "sender_id": "A012",
        "receiver_id": "A011",
        "amount": 1000.0,
        "timestamp": 1700400000.0,
        "sender_balance": 5000.0,
    },
    {
        "id": "T009",
        "sender_id": "A013",
        "receiver_id": "A011",
        "amount": 1500.0,
        "timestamp": 1700400100.0,
        "sender_balance": 8000.0,
    },
    {
        "id": "T010",
        "sender_id": "A014",
        "receiver_id": "A011",
        "amount": 2000.0,
        "timestamp": 1700400200.0,
        "sender_balance": 10000.0,
    },
    # --- Off-hours: 3:00 UTC ---
    {
        "id": "T011",
        "sender_id": "A001",
        "receiver_id": "A015",
        "amount": 3000.0,
        "timestamp": 1700010800.0,
        "sender_balance": 4600.0,
    },
    # --- First-large: A016 normally sends €25-30, then €5000 ---
    {
        "id": "T012",
        "sender_id": "A016",
        "receiver_id": "A017",
        "amount": 25.0,
        "timestamp": 1700500000.0,
        "sender_balance": 6000.0,
    },
    {
        "id": "T013",
        "sender_id": "A016",
        "receiver_id": "A017",
        "amount": 30.0,
        "timestamp": 1700586400.0,
        "sender_balance": 5975.0,
    },
    {
        "id": "T014",
        "sender_id": "A016",
        "receiver_id": "A018",
        "amount": 5000.0,
        "timestamp": 1700672800.0,
        "sender_balance": 5945.0,
    },
    # --- Mule-chain candidate: A019→A020→A021 fast forwarding ---
    {
        "id": "T015",
        "sender_id": "A019",
        "receiver_id": "A020",
        "amount": 8000.0,
        "timestamp": 1700700000.0,
        "sender_balance": 15000.0,
    },
    {
        "id": "T016",
        "sender_id": "A020",
        "receiver_id": "A021",
        "amount": 7500.0,
        "timestamp": 1700701200.0,
        "sender_balance": 8000.0,
    },
]
