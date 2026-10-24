import openpyxl
import pytest

from src.audit import FormulaError, audit_workbook, evaluate_formula

CELLS = {"A1": 10.0, "A2": 5.0, "A3": 2.5, "B1": 1.0}


def ev(formula):
    return evaluate_formula(formula, lambda ref: CELLS.get(ref, 0.0), lambda a, b: _rng(a, b))


def _rng(a, b):
    col = a[0]
    first, last = int(a[1:]), int(b[1:])
    return [CELLS.get(f"{col}{i}", 0.0) for i in range(first, last + 1)]


@pytest.mark.parametrize(
    "formula, expected",
    [
        ("=SUM(A1:A3)", 17.5),
        ("=SUM(A1,A3,B1)", 13.5),
        ("=SUM(A1:A2,B1)", 16.0),
        ("=A1-A2+A3", 7.5),
        ("=A1 - A2 - A3", 2.5),
        ("=SUM(A1:A2)-SUM(A3)", 12.5),
        ("=-A1+A2", -5.0),
        ("=A1+100", 110.0),
    ],
)
def test_supported_syntax(formula, expected):
    assert ev(formula) == pytest.approx(expected)


@pytest.mark.parametrize(
    "formula",
    ["=AVERAGE(A1:A3)", "=A1*A2", "=A1/A2", "=IF(A1>1,1,0)", "=Sheet2!A1", "=SUM(A1:A3", "=SUM(A1:A3)+", "=A1^2", "=ROUND(A1,0)", "=A1+B1:B2", "=$A$1"],
)
def test_unsupported_syntax_is_an_error(formula):
    with pytest.raises(FormulaError):
        ev(formula)


def make_book(tmp_path, cells):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "S"
    for ref, v in cells.items():
        ws[ref] = v
    path = tmp_path / "b.xlsx"
    wb.save(path)
    return path


def test_audit_passes_when_formulas_match_expected_values(tmp_path):
    path = make_book(tmp_path, {"A1": 10, "A2": 5, "A3": "=SUM(A1:A2)", "A4": "=A3-A2"})
    result = audit_workbook(path, {("S", "A3"): 15.0, ("S", "A4"): 10.0})
    assert result.ok and result.checked == 2


def test_audit_reports_mismatch(tmp_path):
    path = make_book(tmp_path, {"A1": 10, "A2": "=SUM(A1:A1)"})
    result = audit_workbook(path, {("S", "A2"): 11.0})
    assert not result.ok and "A2" in result.errors[0]


def test_audit_treats_unsupported_formula_as_error_not_skip(tmp_path):
    path = make_book(tmp_path, {"A1": 10, "A2": "=A1*2"})
    result = audit_workbook(path, {("S", "A2"): 20.0})
    assert not result.ok and any("unsupported" in e.lower() for e in result.errors)


def test_audit_requires_an_expectation_for_every_formula(tmp_path):
    path = make_book(tmp_path, {"A1": 10, "A2": "=A1+1", "A3": "=A1+2"})
    result = audit_workbook(path, {("S", "A2"): 11.0})
    assert not result.ok and any("A3" in e and "expect" in e.lower() for e in result.errors)


def test_audit_flags_expectation_without_a_formula_cell(tmp_path):
    path = make_book(tmp_path, {"A1": 10})
    result = audit_workbook(path, {("S", "A1"): 10.0})
    assert not result.ok
