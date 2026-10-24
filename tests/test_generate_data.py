import csv
from collections import defaultdict
from datetime import date

import pytest

from src.config import Config
from src.generate_data import generate
from src.gl_parser import parse_gl

MONTHS = [date(2024, 12, 1), date(2025, 12, 1), date(2026, 10, 1)]


@pytest.fixture(scope="module")
def landing(tmp_path_factory):
    cfg = Config(root=tmp_path_factory.mktemp("gen"))
    generate(cfg, MONTHS)
    return cfg


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def gl(cfg, label):
    return parse_gl(cfg.landing_dir / label / "gl.xlsx")


def test_one_folder_per_month_with_three_files_and_a_budget(landing):
    for label in ("2024-12", "2025-12", "2026-10"):
        for name in ("gl.xlsx", "platform_bills.csv", "ap_bill_lines.csv"):
            assert (landing.landing_dir / label / name).exists()
    assert landing.budget_path.exists()


def test_generation_is_deterministic(landing, tmp_path):
    other = Config(root=tmp_path)
    generate(other, MONTHS)
    for label in ("2024-12", "2025-12", "2026-10"):
        a, b = gl(landing, label), gl(other, label)
        assert [(t.account_code, t.entry_date, t.reference, t.debit, t.credit) for t in a.transactions] == \
               [(t.account_code, t.entry_date, t.reference, t.debit, t.credit) for t in b.transactions]
        for name in ("platform_bills.csv", "ap_bill_lines.csv"):
            assert (landing.landing_dir / label / name).read_bytes() == (other.landing_dir / label / name).read_bytes()
    assert landing.budget_path.read_bytes() == other.budget_path.read_bytes()


def test_a_month_generated_alone_matches_the_same_month_in_a_longer_run(landing, tmp_path):
    other = Config(root=tmp_path)
    generate(other, [date(2025, 11, 1), date(2025, 12, 1)])
    a, b = gl(landing, "2025-12"), gl(other, "2025-12")
    assert [(t.account_code, t.reference, t.debit, t.credit) for t in a.transactions] == \
           [(t.account_code, t.reference, t.debit, t.credit) for t in b.transactions]
    for name in ("platform_bills.csv", "ap_bill_lines.csv"):
        assert (landing.landing_dir / "2025-12" / name).read_bytes() == (other.landing_dir / "2025-12" / name).read_bytes()


def test_year_end_count_adjustment_is_one_journal_and_larger_in_fy2025(landing):
    def adjustment(label, ref):
        entries = [t for t in gl(landing, label).transactions if t.reference == ref and t.account_code == "5305"]
        assert {t.entry_date for t in entries} == {date(int(label[:4]), 12, 31)}
        return sum(t.debit - t.credit for t in entries)

    small, large = adjustment("2024-12", "AJE-2024-12-01"), adjustment("2025-12", "AJE-2025-12-01")
    assert 0 < small < large
    assert large > 2 * small


def test_partial_month_stops_at_the_cutoff(landing):
    dates = [t.entry_date for t in gl(landing, "2026-10").transactions]
    assert max(dates) == date(2026, 10, 4)
    assert min(dates) >= date(2026, 10, 1)
    full = [t.entry_date for t in gl(landing, "2025-12").transactions]
    assert max(full) == date(2025, 12, 31)


def test_every_entry_is_dated_inside_its_own_month(landing):
    for label in ("2024-12", "2025-12", "2026-10"):
        assert {t.entry_date.strftime("%Y-%m") for t in gl(landing, label).transactions} == {label}


def test_codes_and_cost_centres_are_in_the_closed_sets(landing):
    for label in ("2024-12", "2026-10"):
        for t in gl(landing, label).transactions:
            assert len(t.account_code) == 4 and t.account_code.isdigit()
            assert t.cost_center in {"ST01", "ST02", "ST03", "ST04", "ST05", "HQ01"}
    for r in rows(landing.landing_dir / "2025-12" / "platform_bills.csv"):
        assert r["location"] in {"ST01", "ST02", "ST03", "ST04", "ST05", "HQ01", "Split"}


def test_every_entry_balances_by_reference(landing):
    by_ref = defaultdict(float)
    for t in gl(landing, "2025-12").transactions:
        by_ref[t.reference] += t.debit - t.credit
    assert max(abs(v) for v in by_ref.values()) < 0.01


def test_budget_covers_fy2025_and_fy2026_profit_and_loss_only(landing):
    b = rows(landing.budget_path)
    months = {r["month"][:7] for r in b}
    assert min(months) == "2025-01" and max(months) == "2026-12" and len(months) == 24
    assert all(r["account_code"][0] in "456" for r in b)
    assert {r["cost_center"] for r in b} == {"ST01", "ST02", "ST03", "ST04", "ST05", "HQ01"}


def test_no_currency_marks_in_any_generated_file(landing):
    for path in landing.landing_dir.rglob("*.csv"):
        text = path.read_text()
        assert not any(sym in text for sym in "$£€¥"), path
    for t in gl(landing, "2025-12").transactions:
        assert not any(sym in t.description for sym in "$£€¥")


def test_platform_bills_carry_payment_dates_and_open_bills_are_blank(landing):
    r = rows(landing.landing_dir / "2026-10" / "platform_bills.csv")
    assert r and all(x["due_date"] for x in r)
    assert any(x["paid_date"] == "" for x in r)
    for x in rows(landing.landing_dir / "2025-12" / "platform_bills.csv"):
        if x["paid_date"]:
            assert date.fromisoformat(x["paid_date"]) <= landing.data_cutoff


def test_payments_slow_down_over_time(landing):
    def mean_days(label):
        done = [x for x in rows(landing.landing_dir / label / "platform_bills.csv") if x["paid_date"]]
        return sum((date.fromisoformat(x["paid_date"]) - date.fromisoformat(x["bill_date"])).days for x in done) / len(done)

    assert mean_days("2025-12") > mean_days("2024-12") + 3


def test_platform_and_accounting_overlap_exists(landing):
    pb = rows(landing.landing_dir / "2025-12" / "platform_bills.csv")
    docs = rows(landing.landing_dir / "2025-12" / "ap_bill_lines.csv")
    assert len(pb) > 20
    assert len({d["doc_id"] for d in docs}) > 20
    assert len({d["doc_id"] for d in docs}) <= len(pb) + 10


def test_returns_and_discounts_reduce_revenue(landing):
    returns = [t for t in gl(landing, "2025-12").transactions if t.account_code == "4905"]
    assert returns and all(t.debit > 0 and t.credit == 0 for t in returns)


def test_budget_holds_returns_as_negative_revenue(landing):
    returns = [r for r in rows(landing.budget_path) if r["account_code"] == "4905"]
    assert returns and all(float(r["amount"]) < 0 for r in returns)
