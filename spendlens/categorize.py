"""Rule-based transaction categorization."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

DEFAULT_RULES: dict[str, list[str]] = {
    "Groceries": ["grocery", "supermarket", "tesco", "walmart", "aldi", "lidl", "whole foods", "carrefour"],
    "Dining": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "kfc", "pizza", "burger", "foodpanda", "uber eats", "doordash"],
    "Transport": ["uber", "careem", "lyft", "fuel", "petrol", "shell", "metro", "parking", "airline"],
    "Subscriptions": ["netflix", "spotify", "youtube", "icloud", "apple.com", "github", "chatgpt", "claude", "prime video", "disney"],
    "Shopping": ["amazon", "daraz", "ebay", "ikea", "zara", "nike", "aliexpress"],
    "Utilities": ["electric", "water", "gas bill", "internet", "mobile", "telecom", "ptcl", "jazz", "zong"],
    "Housing": ["rent", "mortgage", "landlord"],
    "Health": ["pharmacy", "clinic", "hospital", "doctor", "gym", "fitness"],
    "Entertainment": ["cinema", "steam", "playstation", "concert", "ticket"],
    "Income": ["salary", "payroll", "invoice", "refund", "transfer in", "dividend"],
}


def load_rules(path: str | Path | None) -> dict[str, list[str]]:
    """Load rules from a TOML file like:

        [rules]
        Groceries = ["tesco", "aldi"]
        Coffee = ["starbucks"]

    Custom rules are checked before the defaults.
    """
    if path is None:
        return DEFAULT_RULES
    with open(path, "rb") as fh:
        custom = tomllib.load(fh).get("rules", {})
    merged = {k: [s.lower() for s in v] for k, v in custom.items()}
    for cat, words in DEFAULT_RULES.items():
        merged.setdefault(cat, words)
    return merged


def categorize_one(description: str, amount: float, rules: dict[str, list[str]]) -> str:
    text = description.lower()
    for category, keywords in rules.items():
        if any(k in text for k in keywords):
            if category == "Income" and amount < 0:
                continue
            return category
    return "Income" if amount > 0 else "Other"


def categorize(df: pd.DataFrame, rules: dict[str, list[str]] | None = None) -> pd.DataFrame:
    rules = rules or DEFAULT_RULES
    out = df.copy()
    out["category"] = [
        categorize_one(d, a, rules) for d, a in zip(out["description"], out["amount"])
    ]
    return out
