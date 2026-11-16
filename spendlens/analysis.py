"""Analysis on categorized transactions."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Overview:
    start: pd.Timestamp
    end: pd.Timestamp
    income: float
    spending: float
    transactions: int

    @property
    def net(self) -> float:
        return self.income - self.spending

    @property
    def savings_rate(self) -> float:
        return self.net / self.income if self.income else 0.0


def expenses(df: pd.DataFrame) -> pd.DataFrame:
    out = df[df["amount"] < 0].copy()
    out["spend"] = -out["amount"]
    return out


def overview(df: pd.DataFrame) -> Overview:
    return Overview(
        start=df["date"].min(),
        end=df["date"].max(),
        income=float(df.loc[df["amount"] > 0, "amount"].sum()),
        spending=float(-df.loc[df["amount"] < 0, "amount"].sum()),
        transactions=len(df),
    )


def by_category(df: pd.DataFrame) -> pd.Series:
    return expenses(df).groupby("category")["spend"].sum().sort_values(ascending=False)


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Months x categories table of spending."""
    exp = expenses(df)
    exp["month"] = exp["date"].dt.to_period("M").astype(str)
    table = exp.pivot_table(index="month", columns="category", values="spend", aggfunc="sum", fill_value=0)
    return table[table.sum().sort_values(ascending=False).index]


def top_merchants(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    exp = expenses(df)
    agg = exp.groupby("merchant").agg(total=("spend", "sum"), count=("spend", "size"))
    return agg.sort_values("total", ascending=False).head(n)


def subscriptions(df: pd.DataFrame, min_months: int = 3, tolerance: float = 0.1) -> pd.DataFrame:
    """Merchants charging a near-constant amount in at least `min_months` months."""
    exp = expenses(df)
    exp["month"] = exp["date"].dt.to_period("M")
    rows = []
    for merchant, grp in exp.groupby("merchant"):
        months = grp["month"].nunique()
        if months < min_months or len(grp) > months * 1.5:
            continue
        mean = grp["spend"].mean()
        if mean and grp["spend"].std(ddof=0) / mean <= tolerance:
            rows.append(
                {"merchant": merchant, "monthly": round(mean, 2), "months": months, "yearly": round(mean * 12, 2)}
            )
    cols = ["merchant", "monthly", "months", "yearly"]
    return pd.DataFrame(rows, columns=cols).sort_values("yearly", ascending=False).reset_index(drop=True)


def anomalies(df: pd.DataFrame, z: float = 2.5, min_count: int = 5) -> pd.DataFrame:
    """Unusually large expenses compared with their own category."""
    exp = expenses(df)
    stats = exp.groupby("category")["spend"].agg(["mean", "std", "count"])
    exp = exp.join(stats, on="category")
    mask = (exp["count"] >= min_count) & (exp["std"] > 0) & (exp["spend"] > exp["mean"] + z * exp["std"])
    flagged = exp.loc[mask, ["date", "description", "category", "spend", "mean"]].copy()
    flagged["times_typical"] = (flagged["spend"] / flagged["mean"]).round(1)
    return flagged.sort_values("spend", ascending=False).reset_index(drop=True)
