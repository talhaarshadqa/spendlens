"""Generate a realistic 12-month sample statement: python examples/generate_sample.py"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)
rows = []
start = date(2025, 11, 1)

for m in range(12):
    month = date(start.year + (start.month - 1 + m) // 12, (start.month - 1 + m) % 12 + 1, 1)
    def d(day, month=month):
        return month + timedelta(days=day - 1)
    rows += [
        (d(1), "PAYROLL ACME SOFTWARE LTD", 4200.00),
        (d(2), "RENT PAYMENT LANDLORD", -1350.00),
        (d(5), "NETFLIX.COM", -15.49),
        (d(7), "SPOTIFY P1234", -10.99),
        (d(9), "GITHUB INC", -4.00),
        (d(12), "INTERNET SERVICE PROVIDER", -45.00),
        (d(15), "ELECTRIC COMPANY BILL", -round(random.uniform(60, 140), 2)),
        (d(20), "GYM FITNESS CLUB", -39.99),
    ]
    for _ in range(random.randint(6, 9)):
        rows.append((d(random.randint(1, 28)), random.choice(["WHOLE FOODS #102", "ALDI STORE 4471", "WALMART SUPERCENTER"]), -round(random.uniform(25, 140), 2)))
    for _ in range(random.randint(8, 14)):
        rows.append((d(random.randint(1, 28)), random.choice(["STARBUCKS #2231", "PIZZA HUT 881", "THAI RESTAURANT", "UBER EATS*ORDER"]), -round(random.uniform(5, 45), 2)))
    for _ in range(random.randint(4, 8)):
        rows.append((d(random.randint(1, 28)), random.choice(["UBER *TRIP", "SHELL FUEL 0091", "CITY PARKING"]), -round(random.uniform(8, 60), 2)))
    for _ in range(random.randint(2, 5)):
        rows.append((d(random.randint(1, 28)), random.choice(["AMAZON MKTPL*2K4", "IKEA STORE", "NIKE.COM"]), -round(random.uniform(15, 120), 2)))
    if m == 7:
        rows.append((d(18), "AMAZON MKTPL*LAPTOP", -1499.00))
    if m == 3:
        rows.append((d(22), "FREELANCE INVOICE 0042", 900.00))

rows.sort()
out = Path(__file__).with_name("sample_transactions.csv")
with open(out, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["Date", "Description", "Amount"])
    w.writerows((r[0].isoformat(), r[1], f"{r[2]:.2f}") for r in rows)
print(f"wrote {len(rows)} rows to {out}")
