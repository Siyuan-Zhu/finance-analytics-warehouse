"""Deterministic generator for the fictional company's monthly exports. Every value here is invented.

Larkspur Outfitters is a five-store outdoor-gear retailer with a head office. Amounts are NIU (normalized index units).
For each month the generator writes a folder under data/landing/ with the report-style ledger export (gl.xlsx), the
bill-pay platform's bills (platform_bills.csv) and the accounting system's bill lines (ap_bill_lines.csv). It also writes
one budget file. Each month is drawn from its own seeded random streams, so a month generated alone is identical to the
same month inside a longer run.

Run: python -m src.generate_data
"""
from __future__ import annotations

import calendar
import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import openpyxl

from src.config import REPO_ROOT, Config, month_label

STORES = ("ST01", "ST02", "ST03", "ST04", "ST05")
SEASON = [0.82, 0.80, 0.90, 0.95, 1.02, 1.08, 1.10, 1.05, 0.96, 1.00, 1.35, 1.65]
INCOME_ACCOUNTS = {"4045", "4025", "4035", "4210", "4805", "4905"}

SALES_BASE = {
    "4045": {"ST01": 54000, "ST02": 47000, "ST03": 41000, "ST04": 36000, "ST05": 44000},
    "4025": {"ST01": 38000, "ST02": 33000, "ST03": 29000, "ST04": 25000, "ST05": 30000},
    "4035": {"ST01": 26000, "ST02": 22000, "ST03": 20000, "ST04": 17000, "ST05": 21000},
}
COGS_RATIO = {"4045": 0.36, "4025": 0.42, "4035": 0.41}
WAGE_BASE = {"ST01": 18000, "ST02": 16000, "ST03": 14000, "ST04": 12500, "ST05": 15000}
RENT_BASE = {"ST01": 11500, "ST02": 10200, "ST03": 9400, "ST04": 8300, "ST05": 9800}
UTIL_BASE = {"ST01": 2400, "ST02": 2050, "ST03": 1900, "ST04": 1750, "ST05": 1950}
# Yearly growth, applied cumulatively from FY2024. The budget assumes the same growth, so it is a fair plan.
GROWTH = {
    2025: {"sales": 1.05, "online": 1.15, "wages": 1.04, "rent": 1.03, "utilities": 1.05, "software": 1.15,
           "ho_salary": 1.04, "insurance": 1.05, "depreciation": 1.07, "marketing": 1.05},
    2026: {"sales": 1.04, "online": 1.12, "wages": 1.04, "rent": 1.03, "utilities": 1.06, "software": 1.18,
           "ho_salary": 1.05, "insurance": 1.06, "depreciation": 1.09, "marketing": 1.05},
}
UNCODED = [
    ("Inbound freight - pallet delivery", "HQ01"), ("Courier freight to online customers", "HQ01"),
    ("Software licence renewal - extra seats", "HQ01"), ("Cleaning contractor visit", "ST02"),
    ("Signage touch-up", "ST03"), ("Legal review of supplier terms", "HQ01"),
    ("Insurance premium adjustment", "HQ01"), ("Equipment repair call-out", "ST04"),
]
# Year-end physical count true-up, booked on 31 December across the five stores. Larger in FY2025 than FY2024.
COUNT_ADJUSTMENT = {2024: 64300.00, 2025: 171800.00}
COUNT_SHARE = {"ST01": 0.30, "ST02": 0.24, "ST03": 0.17, "ST04": 0.13, "ST05": 0.16}
BUDGET_COUNT_ADJUSTMENT = 64300.00  # the budget assumes a repeat of last year's true-up
MISPOSTINGS = {  # reference -> (date, posted account, description, cost centre, amount)
    "MP-2025-0231": (date(2025, 6, 18), "6650", "Legal fees - lease review", "HQ01", 3850.00),
    "MP-2026-0118": (date(2026, 4, 9), "6265", "Roof leak repair - ST02", "ST02", 2940.00),
}


def _growth(year: int, key: str) -> float:
    out = 1.0
    for y in range(2025, year + 1):
        out *= GROWTH[y][key]
    return out


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _account_names() -> dict[str, str]:
    with open(REPO_ROOT / "dbt" / "seeds" / "accounts.csv", newline="") as f:
        return {r["account_code"]: r["account_name"] for r in csv.DictReader(f)}


# ------------------------------------------------------------------ monthly amounts (plan and actual)

def _planted_effect(account: str, cc: str, year: int, month: int) -> float:
    """Things that go wrong in the actuals and are not in the budget."""
    if account == "6105" and cc == "ST03" and (year, month) >= (2025, 7):
        return 1.13  # one store's wages run over budget from July 2025
    if account == "6240" and cc == "HQ01" and year == 2025 and month >= 10:
        return 1.40  # outbound delivery freight over budget for the fourth quarter of FY2025
    if account in ("4045", "4025", "4035") and cc == "ST04" and year == 2026:
        return 0.85  # one store's sales under budget through FY2026
    return 1.0


def monthly_amounts(year: int, month: int, seed: int, actual: bool) -> dict[tuple[str, str], float]:
    """Amount per (account, cost centre) in the account's natural direction. actual=False is the plan (the budget basis)."""
    s = SEASON[month - 1]

    def rng(account, cc):
        return random.Random(f"{seed}|{year}|{month}|{account}|{cc}")

    def noise(account, cc, spread=0.05):
        return 1 + rng(account, cc).uniform(-spread, spread) if actual else 1.0

    def eff(account, cc):
        return _planted_effect(account, cc, year, month) if actual else 1.0

    out: dict[tuple[str, str], float] = {}
    store_sales: dict[str, float] = defaultdict(float)
    store_cogs: dict[str, float] = defaultdict(float)
    for acct, bases in SALES_BASE.items():
        for st, base in bases.items():
            amt = base * s * _growth(year, "sales") * noise(acct, st) * eff(acct, st)
            out[(acct, st)] = amt
            store_sales[st] += amt
            store_cogs[st] += amt * COGS_RATIO[acct]
    online = 70000 * s * _growth(year, "online") * noise("4210", "HQ01")
    out[("4210", "HQ01")] = online
    out[("5040", "HQ01")] = online * 0.46 * noise("5040", "HQ01", 0.02)
    out[("4805", "HQ01")] = 8000 * noise("4805", "HQ01", 0.1)
    wage_f = (1 + 0.3 * (s - 1)) * _growth(year, "wages")
    winter = 1.3 if month in (12, 1, 2) else 1.15 if month in (7, 8) else 1.0
    for st in STORES:
        out[("4905", st)] = -store_sales[st] * 0.045 * noise("4905", st, 0.1)  # contra revenue: negative
        out[("5040", st)] = store_cogs[st] * noise("5040", st, 0.02)
        out[("5205", st)] = store_cogs[st] * 0.045 * noise("5205", st)
        out[("5305", st)] = store_sales[st] * 0.012 * noise("5305", st, 0.2)
        wages = WAGE_BASE[st] * wage_f * noise("6105", st, 0.03) * eff("6105", st)
        out[("6105", st)] = wages
        out[("6115", st)] = wages * 0.18
        out[("6145", st)] = RENT_BASE[st] * _growth(year, "rent")
        out[("6155", st)] = UTIL_BASE[st] * winter * _growth(year, "utilities") * noise("6155", st)
        out[("6165", st)] = 500 * noise("6165", st, 0.5)
        out[("6250", st)] = store_sales[st] * 0.0185 * noise("6250", st, 0.02)
        out[("6265", st)] = 1300 * noise("6265", st, 0.25)
        out[("6185", st)] = 1550 * noise("6185", st, 0.2)
    out[("6250", "HQ01")] = online * 0.019
    out[("6240", "HQ01")] = online * 0.055 * noise("6240", "HQ01") * eff("6240", "HQ01")
    mk = 11000 * _growth(year, "marketing") + (18000 if month == 11 else 4000 if month == 10 else 0)
    out[("6185", "HQ01")] = mk * noise("6185", "HQ01", 0.03)
    sal = 29000 * _growth(year, "ho_salary") * noise("6600", "HQ01", 0.01)
    out[("6600", "HQ01")] = sal
    out[("6610", "HQ01")] = sal * 0.17
    soft = 9400 * _growth(year, "software") * noise("6620", "HQ01", 0.02)
    out[("6620", "HQ01")] = soft + (8200 * _growth(year, "software") if month == 3 else 0)
    legal = rng("6630", "HQ01").uniform(1800, 2600) if actual else 2200
    out[("6630", "HQ01")] = legal + ((14000 if year < 2026 else 15500) if month == 2 else 0)
    out[("6640", "HQ01")] = 4100 * _growth(year, "insurance")
    out[("6650", "HQ01")] = 2300 * noise("6650", "HQ01", 0.2)
    out[("6475", "HQ01")] = 1500 * (rng("6475", "HQ01").uniform(0.4, 1.8) if actual else 1.0)
    out[("6905", "HQ01")] = 11800 * _growth(year, "depreciation")
    return {k: v for k, v in out.items() if abs(v) > 0.004}


# ------------------------------------------------------------------ the ledger for one month

class Month:
    def __init__(self, year: int, month: int, cutoff: date, seed: int):
        self.year, self.month, self.cutoff, self.seed = year, month, cutoff, seed
        self.rng = random.Random(f"{seed}|{year}|{month}|postings")
        self.entries: list[tuple[str, date, str, str, str, float, float]] = []
        self.counters: defaultdict[str, int] = defaultdict(int)

    def ref(self, prefix: str) -> str:
        self.counters[prefix] += 1
        return f"{prefix}-{str(self.year)[2:]}{self.month:02d}-{self.counters[prefix]:05d}"

    def day(self, d: int) -> date:
        return date(self.year, self.month, min(d, _last_day(self.year, self.month)))

    def post(self, account, d: date, desc, cc, amount, counter, ref=None, prefix="JE"):
        """Post amount in the account's natural direction to account and the other side to counter."""
        if d > self.cutoff or abs(amount) < 0.005:
            return
        ref = ref or self.ref(prefix)
        amount = round(amount, 2)
        debit, credit = (0.0, amount) if account in INCOME_ACCOUNTS else (amount, 0.0)
        if amount < 0:  # a reversal: swap the sides
            debit, credit = abs(credit), abs(debit)
        self.entries.append((account, d, ref, desc, cc, debit, credit))
        self.entries.append((counter, d, ref, desc, cc, credit, debit))

    def spread(self, account, days, desc, cc, total, counter, prefix, weights=None):
        """Split a monthly total over posting days; days after the cutoff are simply not posted."""
        w = weights or [self.rng.uniform(0.8, 1.2) for _ in days]
        norm = sum(w)
        for d, x in zip(days, w, strict=True):
            self.post(account, self.day(d), desc, cc, total * x / norm, counter, prefix=prefix)


def _build_month(year: int, month: int, cfg: Config) -> Month:
    m = Month(year, month, cfg.data_cutoff, cfg.seed)
    eom = _last_day(year, month)
    amounts = monthly_amounts(year, month, cfg.seed, actual=True)
    sale_days = [4, 11, 18, 25, eom]
    for (acct, cc), amt in sorted(amounts.items()):
        if acct in ("4045", "4025", "4035", "4210"):
            for d, part in zip(sale_days, _chunks(m, amt, 5), strict=True):
                m.post(acct, m.day(d), "Online orders" if acct == "4210" else "Sales takings", cc, part,
                       "1055" if m.rng.random() < 0.6 else "1010", prefix="SL")
        elif acct == "5040":
            for d, part in zip(sale_days, _chunks(m, amt, 5), strict=True):
                m.post(acct, m.day(d), "Cost of goods sold", cc, part, "2100", prefix="CG")
        elif acct == "4905":
            m.post(acct, m.day(eom), "Returns and discounts", cc, amt, "1055", prefix="RT")  # amt is negative
        elif acct == "5205":
            m.post(acct, m.day(25), "Inbound freight", cc, amt, "1010", prefix="FR")
        elif acct == "5305":
            m.post(acct, m.day(eom), "Inventory shrinkage accrual", cc, amt, "2100", prefix="SH")
        elif acct in ("6105", "6600"):
            m.spread(acct, [15, eom], "Store payroll" if acct == "6105" else "Head office payroll", cc, amt,
                     "1010", "PY", weights=[1, 1])
        elif acct in ("6115", "6610"):
            m.spread(acct, [15, eom], "Payroll taxes and benefits", cc, amt,
                     "2100" if m.rng.random() < 0.7 else "1010", "PY", weights=[1, 1])
        elif acct == "6145":
            m.post(acct, m.day(1), "Monthly rent", cc, amt, "1010", prefix="RN")
        elif acct == "6155":
            m.post(acct, m.day(12), "Utilities", cc, amt, "2100", prefix="UT")
        elif acct == "6165":
            m.post(acct, m.day(m.rng.randint(2, 27)), "Store repair", cc, amt, "1010", prefix="RP")
        elif acct == "6250":
            m.post(acct, m.day(eom), "Card processing fees", cc, amt, "1010", prefix="CF")
        elif acct == "6265":
            m.post(acct, m.day(18), "Store supplies", cc, amt, "1010", prefix="SP")
        elif acct == "6185":
            m.post(acct, m.day(9 if cc != "HQ01" else 5), "Local marketing" if cc != "HQ01" else "Campaign marketing",
                   cc, amt, "1010", prefix="MK")
        elif acct == "6240":
            m.post(acct, m.day(28), "Outbound delivery", cc, amt, "1010", prefix="DL")
        elif acct == "4805":
            m.post(acct, m.day(20), "Supplier rebates", cc, amt, "1010", prefix="RB")
        elif acct == "6620":
            m.post(acct, m.day(3), "Software subscriptions", cc, amt, "1010", prefix="SW")
        elif acct == "6630":
            m.post(acct, m.day(22), "Legal retainer and audit fee" if month == 2 else "Legal retainer", cc, amt,
                   "2100", prefix="PF")
        elif acct == "6640":
            m.post(acct, m.day(1), "Insurance premium", cc, amt, "1010", prefix="IN")
        elif acct == "6650":
            n = m.rng.randint(2, 4)
            for part in _chunks(m, amt, n):
                m.post(acct, m.day(m.rng.randint(1, 28)), "Office and travel", cc, part, "1010", prefix="OT")
        elif acct == "6475":
            m.post(acct, m.day(10), "Training and recruitment", cc, amt, "1010", prefix="TR")
        elif acct == "6905":
            m.post(acct, m.day(eom), "Monthly depreciation", cc, amt, "1655", prefix="DP")
    m.post("1900", m.day(28), "Transfer to savings account", "HQ01", m.rng.uniform(40000, 60000), "1010", prefix="TF")
    if m.rng.random() < 0.8:  # a posting with no usable account code; only its description places it
        desc, cc = m.rng.choice(UNCODED)
        m.post("6990", m.day(m.rng.randint(2, 27)), desc, cc, m.rng.uniform(150, 2400), "1010", prefix="UN")
    for ref, (d, acct, desc, cc, amt) in MISPOSTINGS.items():
        if (d.year, d.month) == (year, month):
            m.post(acct, d, desc, cc, amt, "1010", ref=ref)
    if month == 12 and year in COUNT_ADJUSTMENT:
        ref = f"AJE-{year}-12-01"
        for st, share in COUNT_SHARE.items():
            m.post("5305", date(year, 12, 31), "Year-end physical count true-up", st,
                   COUNT_ADJUSTMENT[year] * share, "2100", ref=ref)
    # card settlement: clear whatever card sales were taken this month into the bank
    net = sum(e[5] - e[6] for e in m.entries if e[0] == "1055")
    last = m.day(eom)
    if net > 0 and last <= m.cutoff:
        ref = m.ref("CS")
        m.entries.append(("1055", last, ref, "Card settlement to bank", "HQ01", 0.0, round(net, 2)))
        m.entries.append(("1010", last, ref, "Card settlement to bank", "HQ01", round(net, 2), 0.0))
    return m


def _chunks(m: Month, total: float, n: int) -> list[float]:
    w = [m.rng.uniform(0.8, 1.2) for _ in range(n)]
    return [total * x / sum(w) for x in w]


def _write_gl(m: Month, path: Path, names: dict[str, str]) -> None:
    by_account = defaultdict(list)
    for i, e in enumerate(m.entries):
        by_account[e[0]].append((e[1], i, e))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Account Transactions"
    end = min(m.cutoff, date(m.year, m.month, _last_day(m.year, m.month)))
    ws.append(["Larkspur Outfitters (fictional)"])
    ws.append(["Account Transactions"])
    ws.append([f"For the period 1 {date(m.year, m.month, 1):%B %Y} to {end.day} {end:%B %Y}"])
    ws.append(["Synthetic data generated by src/generate_data.py. Amounts are NIU (normalized index units)."])
    ws.append([])
    for code in sorted(by_account):
        name = names[code]
        ws.append([f"{code} {name}"])
        ws.append(["Date", "Reference", "Description", "Cost Center", "Debit", "Credit"])
        debit = credit = 0.0
        for d, _i, e in sorted(by_account[code], key=lambda x: (x[0], x[1])):
            _acct, _d, ref, desc, cc, dr, cr = e
            ws.append([d, ref, desc, cc, dr or None, cr or None])
            ws.cell(row=ws.max_row, column=1).number_format = "yyyy-mm-dd"
            debit += dr
            credit += cr
        ws.append([f"Total {code} {name}", None, None, None, round(debit, 2), round(credit, 2)])
        ws.append([])
    wb.save(path)


# ------------------------------------------------------------------ accounts payable

VENDORS = [
    # name, bills per month, low, high, GL codes, locations, share entered directly in the accounting system, net terms
    ("Ridgeline Apparel Supply Inc", 2, 18000, 70000, ["5040"], ["HQ01"], 0.0, 45),
    ("Basecamp Footwear Wholesale LLC", 2, 12000, 48000, ["5040"], ["HQ01"], 0.0, 45),
    ("Cedar Ridge Freight Inc", 5, 420, 1300, ["5205"], list(STORES), 0.05, 30),
    ("Bluefin Signage LLC", 2, 380, 2900, ["6265", "6185"], list(STORES), 0.0, 30),
    ("Northfield Packaging Co", 2, 600, 2100, ["6265", "5205"], ["ST01", "ST03", "HQ01"], 0.05, 30),
    ("Summit Ridge Software Ltd", 1, 1800, 3200, ["6620"], ["HQ01"], 0.0, 30),
    ("Harbor Light Utilities Inc", 4, 1500, 2600, ["6155"], list(STORES), 0.92, 20),
    ("Oakline Cleaning Services LLC", 4, 380, 720, ["6265"], list(STORES), 0.1, 30),
    ("Tallgrass Fixtures LLC", 2, 900, 4200, ["6265"], list(STORES), 0.0, 30),
    ("Ironwood Contractors Inc", 1, 1500, 9000, ["6165"], list(STORES), 0.1, 30),
    ("Willow & Finch Design", 1, 1200, 4800, ["6185"], ["HQ01"], 0.0, 30),
    ("Copperleaf Legal LLP", 1, 1800, 3900, ["6630"], ["HQ01"], 0.1, 30),
    ("Stonebridge Insurance Brokers Inc", 1, 4100, 4400, ["6640"], ["HQ01"], 0.9, 30),
    ("Alder Creek Courier Co", 4, 160, 780, ["6240"], ["HQ01"], 0.0, 30),
    ("Pinegate Office Supply Inc", 2, 90, 640, ["6650", "6265"], ["HQ01", "ST02"], 0.15, 30),
    ("Meridian Print & Display Ltd", 1, 700, 3800, ["6185"], list(STORES), 0.0, 30),
    ("Quillfeather Staffing Inc", 2, 1800, 6100, ["6105"], list(STORES), 0.0, 30),
    ("Redwood Pallet Works LLC", 3, 300, 1100, ["5205"], ["ST02", "ST04"], 0.0, 30),
]
TERMS = {v[0]: v[7] for v in VENDORS}
PAYMENT_METHODS = ["ach", "ach", "ach", "card", "check", "virtual card"]
SPLIT_RATE, BLANK_GL_RATE, SYNC_RATE = 0.14, 0.55, 0.93
SLOWDOWN_START = date(2025, 7, 1)  # payments start to slip


def _vendor_variant(rng, name: str) -> str:
    style = rng.randint(0, 3)
    if style == 0:
        return name
    if style == 1:
        return name.upper()
    if style == 2:
        head, _, tail = name.rpartition(" ")
        return head if tail in ("Inc", "LLC", "Ltd", "Co") else name
    parts = name.rsplit(" ", 1)
    return f"{parts[0]}, {parts[1]}." if parts[1] in ("Inc", "LLC", "Ltd", "Co") else name


def _split_amount(rng, total: float, n: int) -> list[float]:
    cuts = sorted(rng.uniform(0.15, 0.85) for _ in range(n - 1))
    shares = [b - a for a, b in zip([0.0] + cuts, cuts + [1.0], strict=True)]
    parts = [round(total * s, 2) for s in shares[:-1]]
    return parts + [round(total - sum(parts), 2)]


def _pay_dates(rng, vendor: str, bill_date: date, cutoff: date) -> tuple[date, date | None]:
    """Due date and payment date. Before July 2025 bills are paid a little early; after, progressively late."""
    terms = TERMS[vendor]
    if bill_date < SLOWDOWN_START:
        days = terms - rng.randint(0, 6) + (rng.randint(1, 5) if rng.random() < 0.08 else 0)
    elif bill_date < date(2026, 1, 1):
        days = terms + rng.randint(-4, 12)
    else:
        days = terms + rng.randint(-2, 18)
    paid = bill_date + timedelta(days=days)
    return bill_date + timedelta(days=terms), (paid if paid <= cutoff else None)


def _ap_for_month(year: int, month: int, cfg: Config):
    """Platform bills dated in this month, and every accounting document those bills (and direct entries) create."""
    rng = random.Random(f"{cfg.seed}|ap|{year}-{month:02d}")
    tag = f"{str(year)[2:]}{month:02d}"
    platform: list[list] = []
    accounting: list[list] = []
    counts = {"pb": 0, "doc": 0}
    cutoff = cfg.data_cutoff
    growth = 1.0 + 0.02 * ((year - 2024) * 12 + month) / 12  # purchase volumes drift up slowly

    def add_doc(vendor, d, lines, due, paid):
        if d > cutoff:
            return None
        counts["doc"] += 1
        doc = f"BILL-{tag}-{counts['doc']:04d}"
        for i, (code, loc, amt) in enumerate(lines, start=1):
            accounting.append([doc, i, vendor, d.isoformat(), due.isoformat(), paid.isoformat() if paid else "",
                               code, loc, f"{amt:.2f}"])
        return doc

    def add_pb(name, d, amount, method, gl, location, due, paid):
        counts["pb"] += 1
        platform.append([f"PB-{tag}-{counts['pb']:04d}", name, d.isoformat(), due.isoformat(),
                         paid.isoformat() if paid else "", f"{amount:.2f}", method, gl, location])

    def make_lines(amount, codes, locs, split):
        n = rng.randint(2, 4) if split or rng.random() < 0.45 else 1
        amounts = _split_amount(rng, amount, n)
        if split:
            line_locs = rng.sample(locs, min(len(locs), n)) if len(locs) >= 2 else locs * n
            line_locs = (line_locs * n)[:n]
        else:
            line_locs = [rng.choice(locs)] * n
        return [(rng.choice(codes), line_locs[i], amounts[i]) for i in range(n)]

    last = _last_day(year, month)
    for name, per_month, lo, hi, codes, locs, direct, _terms in VENDORS:
        for _ in range(per_month):
            d = date(year, month, rng.randint(1, max(1, last - 3)))
            if d > cutoff:
                continue
            amount = round(rng.uniform(lo, hi) * growth, 2)
            split = len(locs) > 1 and rng.random() < SPLIT_RATE
            lines = make_lines(amount, codes, locs, split)
            due, paid = _pay_dates(rng, name, d, cutoff)
            if rng.random() < direct:
                add_doc(_vendor_variant(rng, name), d, lines, due, paid)
                continue
            gl = "" if rng.random() < BLANK_GL_RATE else lines[0][0]
            add_pb(name, d, amount, rng.choice(PAYMENT_METHODS), gl, "Split" if split else lines[0][1], due, paid)
            if rng.random() < SYNC_RATE:
                drift = rng.choice([0, 0, 0, 1, 2])
                if rng.random() < 0.12:  # rounding differences between the two systems
                    diff = round(rng.uniform(-0.3, 0.3), 2)
                    lines[0] = (lines[0][0], lines[0][1], round(lines[0][2] + diff, 2))
                add_doc(_vendor_variant(rng, name), d + timedelta(days=drift), lines, due, paid)

    # planted: a platform bill with two same-looking accounting documents (ambiguous)
    if rng.random() < 0.45:
        name = rng.choice(["Alder Creek Courier Co", "Cedar Ridge Freight Inc", "Redwood Pallet Works LLC"])
        d = date(year, month, 10)
        amount = round(rng.uniform(200, 900), 2)
        due, paid = _pay_dates(rng, name, d, cutoff)
        if d <= cutoff:
            add_pb(name, d, amount, "ach", "", "ST01", due, paid)
            add_doc(name.upper(), d, [("5205", "ST01", amount)], due, paid)
            add_doc(name, d + timedelta(days=2), [("5205", "ST01", amount)], due, paid)
    # planted: the same bill entered twice in the platform, synced once
    if rng.random() < 0.2:
        name = rng.choice(["Bluefin Signage LLC", "Oakline Cleaning Services LLC"])
        d = date(year, month, 16)
        amount = round(rng.uniform(300, 700), 2)
        due, paid = _pay_dates(rng, name, d, cutoff)
        if d <= cutoff:
            for _ in range(2):
                add_pb(name, d, amount, "card", "", "ST03", due, paid)
            add_doc(name, d, [("6265", "ST03", amount)], due, paid)
    # planted: a synced bill whose accounting date drifted beyond the matching window
    if rng.random() < 0.3:
        name = rng.choice(["Ironwood Contractors Inc", "Willow & Finch Design", "Copperleaf Legal LLP"])
        d = date(year, month, 8)
        amount = round(rng.uniform(2000, 9000), 2)
        due, paid = _pay_dates(rng, name, d, cutoff)
        if d <= cutoff:
            add_pb(name, d, amount, "ach", "", "HQ01", due, paid)
            add_doc(name, d + timedelta(days=9), [("6630", "HQ01", amount)], due, paid)
    return platform, accounting


PLATFORM_COLS = ["bill_id", "vendor", "bill_date", "due_date", "paid_date", "amount", "payment_method", "gl_code",
                 "location"]
LINE_COLS = ["doc_id", "line_no", "vendor", "bill_date", "due_date", "paid_date", "gl_code", "location", "amount"]


def _write_csv(path: Path, cols, rows) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)


def _write_ap(month: date, cfg: Config, folder: Path) -> None:
    previous = date(month.year - (month.month == 1), (month.month - 2) % 12 + 1, 1)
    platform, accounting = _ap_for_month(month.year, month.month, cfg)
    _prev_platform, prev_accounting = _ap_for_month(previous.year, previous.month, cfg)
    label = month_label(month)
    docs = [r for r in prev_accounting + accounting if r[3].startswith(label)]  # a document lands in its own month
    docs.sort(key=lambda r: (r[3], r[0], r[1]))
    platform.sort(key=lambda r: (r[2], r[0]))
    _write_csv(folder / "platform_bills.csv", PLATFORM_COLS, platform)
    _write_csv(folder / "ap_bill_lines.csv", LINE_COLS, docs)


# ------------------------------------------------------------------ budget

def _write_budget(cfg: Config) -> None:
    rows = []
    for year in (2025, 2026):
        for month in range(1, 13):
            plan = monthly_amounts(year, month, cfg.seed, actual=False)
            for (acct, cc), amt in sorted(plan.items()):
                if acct[0] in "456":
                    rows.append([date(year, month, 1).isoformat(), acct, cc, f"{round(amt):.2f}"])
            if month == 12:
                for st, share in COUNT_SHARE.items():
                    rows.append([date(year, 12, 1).isoformat(), "5305", st, f"{round(BUDGET_COUNT_ADJUSTMENT * share):.2f}"])
    merged: dict[tuple, float] = defaultdict(float)
    for month, acct, cc, amt in rows:
        merged[(month, acct, cc)] += float(amt)
    cfg.landing_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(cfg.budget_path, ["month", "account_code", "cost_center", "amount"],
               [[m, a, c, f"{v:.2f}"] for (m, a, c), v in sorted(merged.items())])


def generate(cfg: Config, months: list[date] | None = None) -> list[Path]:
    """Write one landing folder per month, plus the budget. Same seed, same files."""
    names = _account_names()
    folders = []
    for month in months or cfg.months:
        folder = cfg.landing_dir / month_label(month)
        folder.mkdir(parents=True, exist_ok=True)
        _write_gl(_build_month(month.year, month.month, cfg), folder / "gl.xlsx", names)
        _write_ap(month, cfg, folder)
        folders.append(folder)
    _write_budget(cfg)
    return folders


if __name__ == "__main__":
    print(f"wrote {len(generate(Config()))} monthly folders")
