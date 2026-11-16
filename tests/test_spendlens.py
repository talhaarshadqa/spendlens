import pandas as pd
import pytest

from spendlens import analysis
from spendlens.categorize import categorize, categorize_one, load_rules
from spendlens.cli import main
from spendlens.loader import LoadError, clean_merchant, load_transactions


def frame(rows):
    return pd.DataFrame(rows, columns=["Date", "Description", "Amount"])


@pytest.fixture
def df():
    rows = []
    for month in range(1, 7):
        rows += [
            (f"2026-{month:02d}-01", "PAYROLL ACME", "3000"),
            (f"2026-{month:02d}-02", "RENT PAYMENT", "-1000"),
            (f"2026-{month:02d}-05", "NETFLIX.COM", "-15.49"),
            (f"2026-{month:02d}-10", "TESCO STORE 12", "-50"),
            (f"2026-{month:02d}-20", "TESCO STORE 12", "-55"),
        ]
    rows.append(("2026-06-25", "TESCO STORE 12", "-900"))
    return categorize(load_transactions(frame(rows)))


def test_clean_merchant():
    assert clean_merchant("AMAZON MKTPL*2K4 SEATTLE") == "AMAZON MKTPL"
    assert clean_merchant("Starbucks #2231") == "STARBUCKS"
    assert clean_merchant("SHELL FUEL 0091") == "SHELL FUEL"


def test_load_debit_credit_columns():
    raw = pd.DataFrame(
        {"Transaction Date": ["2026-01-01", "2026-01-02"], "Details": ["Salary", "Coffee"],
         "Debit": ["", "4.50"], "Credit": ["1,000.00", ""]}
    )
    out = load_transactions(raw)
    assert out["amount"].tolist() == [1000.0, -4.5]


def test_load_parentheses_negative():
    out = load_transactions(frame([("2026-01-01", "x", "(12.50)")]))
    assert out["amount"].iloc[0] == -12.5


def test_load_errors():
    with pytest.raises(LoadError):
        load_transactions(pd.DataFrame({"foo": [1]}))
    with pytest.raises(LoadError):
        load_transactions(pd.DataFrame({"date": ["2026-01-01"], "description": ["x"]}))


def test_categorize_rules(tmp_path):
    assert categorize_one("NETFLIX.COM", -15, load_rules(None)) == "Subscriptions"
    assert categorize_one("Mystery Co", -15, load_rules(None)) == "Other"
    assert categorize_one("Mystery Co", 15, load_rules(None)) == "Income"
    assert categorize_one("REFUND fee", -5, load_rules(None)) == "Other"  # income word on a debit
    toml = tmp_path / "r.toml"
    toml.write_text('[rules]\nCoffee = ["Starbucks"]\n')
    assert categorize_one("STARBUCKS #1", -4, load_rules(toml)) == "Coffee"


def test_overview(df):
    ov = analysis.overview(df)
    assert ov.income == 18000
    assert ov.spending == pytest.approx(6 * (1000 + 15.49 + 105) + 900)
    assert 0 < ov.savings_rate < 1


def test_monthly_and_categories(df):
    table = analysis.monthly(df)
    assert list(table.index) == [f"2026-{m:02d}" for m in range(1, 7)]
    assert table.columns[0] == "Housing"
    assert analysis.by_category(df)["Groceries"] == pytest.approx(6 * 105 + 900)


def test_subscriptions(df):
    subs = analysis.subscriptions(df)
    assert set(subs["merchant"]) == {"RENT PAYMENT", "NETFLIX.COM"}
    assert subs.iloc[0]["yearly"] == 12000


def test_anomalies(df):
    anom = analysis.anomalies(df)
    assert len(anom) == 1
    assert anom.iloc[0]["spend"] == 900


def test_cli(tmp_path, capsys):
    csv = tmp_path / "t.csv"
    csv.write_text("Date,Description,Amount\n2026-01-01,SALARY,100\n2026-01-02,TESCO,-20\n")
    html = tmp_path / "r.html"
    export = tmp_path / "out.csv"
    assert main([str(csv), "-o", str(html), "--export", str(export), "-c", "$"]) == 0
    assert "Groceries" in capsys.readouterr().out
    assert "<img" in html.read_text()
    assert "category" in export.read_text()
    assert main([str(tmp_path / "missing.csv")]) == 2
