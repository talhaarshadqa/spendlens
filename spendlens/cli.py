"""Command-line interface."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .categorize import categorize, load_rules
from .loader import LoadError, load_transactions
from .report import html_report, text_report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spendlens", description="Analyze a bank-statement CSV.")
    p.add_argument("csv", help="transactions CSV file")
    p.add_argument("-o", "--html", metavar="FILE", help="also write an HTML report with charts")
    p.add_argument("-r", "--rules", metavar="TOML", help="custom categorization rules")
    p.add_argument("-c", "--currency", default="", help="currency symbol, e.g. '$' or 'Rs '")
    p.add_argument("--export", metavar="FILE", help="write categorized transactions to CSV")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    try:
        df = categorize(load_transactions(args.csv), load_rules(args.rules))
    except (OSError, LoadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if df.empty:
        print("error: no transactions found", file=sys.stderr)
        return 2

    print(text_report(df, args.currency))
    if args.html:
        print(f"\nHTML report written to {html_report(df, args.html, args.currency)}")
    if args.export:
        df.to_csv(args.export, index=False)
        print(f"Categorized CSV written to {args.export}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
