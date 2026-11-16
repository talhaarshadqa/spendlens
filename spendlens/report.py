"""Text and HTML reports."""

from __future__ import annotations

import base64
import html
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import analysis  # noqa: E402

PALETTE = ["#4C6EF5", "#12B886", "#FAB005", "#FA5252", "#7950F2", "#15AABF", "#FD7E14", "#82C91E", "#E64980", "#868E96"]


def money(x: float, currency: str = "") -> str:
    return f"{currency}{x:,.2f}"


def text_report(df: pd.DataFrame, currency: str = "") -> str:
    ov = analysis.overview(df)
    lines = [
        f"Period:        {ov.start:%Y-%m-%d} -> {ov.end:%Y-%m-%d}  ({ov.transactions} transactions)",
        f"Income:        {money(ov.income, currency)}",
        f"Spending:      {money(ov.spending, currency)}",
        f"Net:           {money(ov.net, currency)}  (savings rate {ov.savings_rate:.0%})",
        "",
        "Spending by category:",
    ]
    cats = analysis.by_category(df)
    total = cats.sum() or 1
    for cat, val in cats.items():
        bar = "#" * int(30 * val / cats.iloc[0])
        lines.append(f"  {cat:<14} {money(val, currency):>12}  {val / total:5.1%}  {bar}")

    subs = analysis.subscriptions(df)
    if not subs.empty:
        lines += ["", "Recurring charges:"]
        for r in subs.itertuples():
            lines.append(f"  {r.merchant:<24} {money(r.monthly, currency):>10}/mo  ~{money(r.yearly, currency)}/yr")

    anom = analysis.anomalies(df)
    if not anom.empty:
        lines += ["", "Unusual expenses:"]
        for r in anom.head(5).itertuples():
            lines.append(
                f"  {r.date:%Y-%m-%d}  {r.description[:30]:<30} {money(r.spend, currency):>10}  ({r.times_typical}x typical {r.category})"
            )
    return "\n".join(lines)


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _monthly_chart(df: pd.DataFrame) -> str:
    table = analysis.monthly(df)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    bottom = None
    for i, col in enumerate(table.columns):
        ax.bar(table.index, table[col], bottom=bottom, label=col, color=PALETTE[i % len(PALETTE)])
        bottom = table[col] if bottom is None else bottom + table[col]
    ax.set_title("Monthly spending by category", loc="left", fontsize=13)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False, ncol=1, bbox_to_anchor=(1.01, 1), loc="upper left")
    return _fig_to_b64(fig)


def _category_chart(df: pd.DataFrame) -> str:
    cats = analysis.by_category(df).sort_values()
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(cats) + 1))
    ax.barh(cats.index, cats.values, color=PALETTE[0])
    for y, v in enumerate(cats.values):
        ax.text(v, y, f"  {v:,.0f}", va="center", fontsize=9)
    ax.set_title("Total spending by category", loc="left", fontsize=13)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.set_xticks([])
    return _fig_to_b64(fig)


def _table(frame: pd.DataFrame) -> str:
    return frame.to_html(index=False, border=0, classes="tbl", float_format=lambda x: f"{x:,.2f}")


def html_report(df: pd.DataFrame, path: str | Path, currency: str = "") -> Path:
    ov = analysis.overview(df)
    subs = analysis.subscriptions(df)
    anom = analysis.anomalies(df)
    merchants = analysis.top_merchants(df).reset_index()

    cards = "".join(
        f'<div class="card"><div class="lbl">{lbl}</div><div class="val">{val}</div></div>'
        for lbl, val in [
            ("Income", money(ov.income, currency)),
            ("Spending", money(ov.spending, currency)),
            ("Net", money(ov.net, currency)),
            ("Savings rate", f"{ov.savings_rate:.0%}"),
        ]
    )
    anom_view = anom.assign(date=anom["date"].dt.strftime("%Y-%m-%d"))[
        ["date", "description", "category", "spend", "times_typical"]
    ] if not anom.empty else anom

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>spendlens report</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:1000px;margin:40px auto;padding:0 20px;color:#212529}}
h1{{margin-bottom:4px}} .sub{{color:#868e96;margin-top:0}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}
.card{{background:#f8f9fa;border-radius:10px;padding:16px}} .lbl{{color:#868e96;font-size:13px}} .val{{font-size:22px;font-weight:600}}
img{{max-width:100%}} h2{{margin-top:36px}}
.tbl{{border-collapse:collapse;width:100%;font-size:14px}} .tbl th,.tbl td{{padding:8px;border-bottom:1px solid #e9ecef;text-align:left}}
</style></head><body>
<h1>spendlens report</h1>
<p class="sub">{ov.start:%d %b %Y} to {ov.end:%d %b %Y} &middot; {ov.transactions} transactions</p>
<div class="cards">{cards}</div>
<img src="data:image/png;base64,{_monthly_chart(df)}" alt="monthly spending">
<img src="data:image/png;base64,{_category_chart(df)}" alt="spending by category">
<h2>Top merchants</h2>{_table(merchants)}
<h2>Recurring charges</h2>{_table(subs) if not subs.empty else "<p>None detected.</p>"}
<h2>Unusual expenses</h2>{_table(anom_view) if not anom.empty else "<p>None detected.</p>"}
<p class="sub" style="margin-top:40px">Generated by spendlens &middot; {html.escape(str(pd.Timestamp.now().date()))}</p>
</body></html>"""
    path = Path(path)
    path.write_text(page, encoding="utf-8")
    return path
