"""Load bank-statement CSVs with flexible column names."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

DATE_COLS = ["date", "transaction date", "posted date", "posting date", "value date"]
DESC_COLS = ["description", "details", "merchant", "payee", "narrative", "memo"]
AMOUNT_COLS = ["amount", "value", "transaction amount"]
DEBIT_COLS = ["debit", "withdrawal", "money out", "paid out"]
CREDIT_COLS = ["credit", "deposit", "money in", "paid in"]


class LoadError(ValueError):
    pass


def _find(columns: dict[str, str], options: list[str]) -> str | None:
    for opt in options:
        if opt in columns:
            return columns[opt]
    return None


def _to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(r"[,\s$£€]", "", regex=True)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)  # (12.50) -> -12.50
        .replace({"": "0", "nan": "0", "None": "0"})
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def clean_merchant(description: str) -> str:
    """'AMAZON MKTPL*2K4 #8812 SEATTLE' -> 'AMAZON MKTPL'."""
    text = description.upper()
    text = re.split(r"[*#]", text)[0]
    text = re.sub(r"\b\d[\d\-/]*\b", " ", text)  # card numbers, dates, refs
    text = re.sub(r"\s+", " ", text).strip()
    return text or description.upper().strip()


def load_transactions(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with columns: date, description, merchant, amount.

    Expenses are negative and income is positive. Accepts either a single
    signed `amount` column or separate debit/credit columns.
    """
    raw = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source)
    columns = {c.strip().lower(): c for c in raw.columns}

    date_col = _find(columns, DATE_COLS)
    desc_col = _find(columns, DESC_COLS)
    if not date_col or not desc_col:
        raise LoadError(f"need a date and description column, got {list(raw.columns)}")

    amount_col = _find(columns, AMOUNT_COLS)
    if amount_col:
        amount = _to_number(raw[amount_col])
    else:
        debit, credit = _find(columns, DEBIT_COLS), _find(columns, CREDIT_COLS)
        if not debit and not credit:
            raise LoadError("need an amount column or debit/credit columns")
        amount = pd.Series(0.0, index=raw.index)
        if credit:
            amount = amount + _to_number(raw[credit]).abs()
        if debit:
            amount = amount - _to_number(raw[debit]).abs()

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(raw[date_col], errors="coerce"),
            "description": raw[desc_col].astype(str).str.strip(),
            "amount": amount.astype(float),
        }
    )
    df = df.dropna(subset=["date"])
    df["merchant"] = df["description"].map(clean_merchant)
    return df.sort_values("date").reset_index(drop=True)
