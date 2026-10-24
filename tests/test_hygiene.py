"""Repo-wide rules: no currency marks or words, only the six cost centres, 4-digit account codes."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCANNED = [p for pattern in ("src/*.py", "dbt/models/**/*.sql", "dbt/models/**/*.yml", "dbt/seeds/*.csv", "dbt/tests/*.sql",
                              "dbt/macros/*.sql", "docs/*.md", "README.md", "dashboard/pages/**/*.md", "dashboard/sources/**/*.*",
                              "dashboard/*.json", "dashboard/*.yaml", ".github/workflows/*.yml")
           for p in ROOT.glob(pattern)]
CURRENCY_WORDS = re.compile(r"\b(dollars?|usd|euros?|eur|gbp|sterling|yen|cents)\b", re.IGNORECASE)


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_currency_symbols_or_words(path):
    text = path.read_text()
    assert not re.search(r"[£€¥]", text)
    assert not CURRENCY_WORDS.search(text)
    # a dollar sign is fine in GitHub Actions expressions and regex anchors, never in front of a number or letter run
    assert not re.search(r"\$\s?\d", text)


def test_the_only_segments_are_store_and_head_office_cost_centres():
    codes = {line.split(",")[0] for line in (ROOT / "dbt/seeds/cost_centers.csv").read_text().splitlines()[1:]}
    assert codes == {"ST01", "ST02", "ST03", "ST04", "ST05", "HQ01"}


def test_account_codes_are_four_digits():
    for line in (ROOT / "dbt/seeds/accounts.csv").read_text().splitlines()[1:]:
        assert re.fullmatch(r"\d{4}", line.split(",")[0])


def test_the_readme_does_not_mention_reviews_or_confidentiality():
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text().lower()
        assert "confidential" not in text and "audit" not in text
