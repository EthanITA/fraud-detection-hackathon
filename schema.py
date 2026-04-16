"""Shared type definitions for all challenges (1–3).

All three challenges share the same structured data schema:
  users.json, locations.json, sms.json, mails.json, transactions.csv

Challenge 3 adds an audio/ directory with MP3 voice recordings.
"""

from __future__ import annotations

from typing import Literal, TypedDict


# ── users.json ──────────────────────────────────────────────


class Residence(TypedDict):
    city: str
    lat: str  # string in JSON, e.g. "47.4836"
    lng: str  # string in JSON, e.g. "6.8403"


class User(TypedDict):
    first_name: str
    last_name: str
    birth_year: int
    salary: int  # annual
    job: str
    iban: str  # some users transact from additional IBANs not listed here
    residence: Residence
    description: str  # free-text biography


# ── locations.json ──────────────────────────────────────────


class LocationPing(TypedDict):
    biotag: str  # format: SURNAME[4]-FIRSTNAME[4]-HEX-CITY[3]-N
    timestamp: str  # ISO 8601
    lat: float
    lng: float
    city: str


# ── sms.json ────────────────────────────────────────────────


class SmsEntry(TypedDict):
    sms: str  # raw text with From/To/Date/Message fields


# ── mails.json ──────────────────────────────────────────────


class MailEntry(TypedDict):
    mail: str  # raw MIME-formatted email with HTML body


# ── transactions.csv ────────────────────────────────────────

TransactionType = Literal[
    # stay withing the system
    "transfer",
    "direct debit",
    # lose of tracking
    "e-commerce",
    "in-person payment",
    # cash out
    "withdrawal",
]

PaymentMethod = Literal[
    "debit card",
    "Google Pay",
    "mobile phone",
    "PayPal",
    "smartwatch",
]


class Transaction(TypedDict):
    transaction_id: str  # UUID
    sender_id: str  # biotag or EMP-prefixed employer ID
    recipient_id: str  # merchant/entity ID, empty for withdrawals/some in-person
    transaction_type: TransactionType
    amount: float
    location: str  # "{city} - {venue}", empty for transfers/direct debits
    payment_method: PaymentMethod | str  # empty for transfers/direct debits
    sender_iban: str
    recipient_iban: str  # empty for withdrawals/in-person
    balance_after: float
    description: str  # empty for e-commerce/in-person/withdrawals
    timestamp: str  # ISO 8601


# ── audio files (challenge 3 only) ─────────────────────────
# Filename format: YYYYMMDD_HHMMSS-firstname_lastname.mp3
# e.g. "20870117_010505-guido_döhn.mp3"
# 48 files per split (train/validation), one recording per citizen encounter.

AudioFilename = str


# ── top-level file shapes ──────────────────────────────────

UsersFile = list[User]
LocationsFile = list[LocationPing]
SmsFile = list[SmsEntry]
MailsFile = list[MailEntry]
