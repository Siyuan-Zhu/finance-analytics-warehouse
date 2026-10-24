"""Generate the synthetic data, then close every month in order from the first month.

    python -m src.run_all                      # all 34 months, January 2024 to the first days of October 2026
    python -m src.run_all --from 2024-01 --to 2024-03

The warehouse is rebuilt from scratch each time, so the close log has exactly one row per month. Stops at the first
failed close and exits non-zero.
"""
from __future__ import annotations

import argparse
import shutil
import sys

from src.close import close_month
from src.config import Config, month_label, months_between, parse_month
from src.dbt_runner import run_dbt
from src.generate_data import generate


def main(argv=None, config: Config | None = None, runner=run_dbt) -> int:
    config = config or Config()
    parser = argparse.ArgumentParser(description="Generate data and close every month in order.")
    parser.add_argument("--from", dest="first", default=month_label(config.first_month))
    parser.add_argument("--to", dest="last", default=month_label(config.last_month))
    args = parser.parse_args(argv)
    months = months_between(parse_month(args.first), parse_month(args.last))

    shutil.rmtree(config.landing_dir, ignore_errors=True)
    shutil.rmtree(config.output_dir, ignore_errors=True)
    config.warehouse_path.unlink(missing_ok=True)
    generate(config, months)
    print(f"generated {len(months)} monthly exports under {config.landing_dir}")
    for month in months:
        result = close_month(config, month, runner=runner)
        print(f"{month_label(month)} {result.status}: gl {result.gl_rows}, platform bills {result.platform_rows}, "
              f"bill lines {result.ap_line_rows}, checks {result.checks_passed}/{result.checks_total}")
        if not result.ok:
            for failure in result.failures:
                print(f"  {failure}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
