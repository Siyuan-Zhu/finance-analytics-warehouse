import duckdb

from src.config import Config
from src.run_all import main


def test_run_all_generates_and_closes_months_in_order(tmp_path):
    cfg = Config(root=tmp_path)
    assert main(["--from", "2024-01", "--to", "2024-03"], config=cfg) == 0
    con = duckdb.connect(str(cfg.warehouse_path), read_only=True)
    rows = con.execute("select strftime(month, '%Y-%m'), status from raw.close_log order by run_at").fetchall()
    assert rows == [("2024-01", "closed"), ("2024-02", "closed"), ("2024-03", "closed")]
    assert con.execute("select count(*) from raw.gl_entries").fetchone()[0] == con.execute(
        "select count(*) from marts.fct_gl_entries").fetchone()[0]
    con.close()
    assert (cfg.landing_dir / "2024-02" / "gl.xlsx").exists()


def test_a_second_run_starts_from_a_clean_warehouse(tmp_path):
    cfg = Config(root=tmp_path)
    main(["--from", "2024-01", "--to", "2024-01"], config=cfg)
    main(["--from", "2024-01", "--to", "2024-01"], config=cfg)
    con = duckdb.connect(str(cfg.warehouse_path), read_only=True)
    assert con.execute("select count(*) from raw.close_log").fetchone()[0] == 1
    con.close()
