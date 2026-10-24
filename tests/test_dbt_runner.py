from src.dbt_runner import DbtResult, summarise_run_results


def result(unique_id, status, message=None):
    return {"unique_id": unique_id, "status": status, "message": message}


def test_counts_tests_by_outcome_and_lists_failures():
    run_results = {"results": [
        result("model.larkspur.stg_gl_entries", "success"),
        result("test.larkspur.unique_x", "pass"),
        result("test.larkspur.not_null_x", "pass"),
        result("test.larkspur.assert_totals", "fail", "Got 2 results, configured to fail if != 0"),
        result("unit_test.larkspur.int_gl_mapped.first_rule_wins", "pass"),
        result("test.larkspur.skipped_one", "skipped"),
    ]}
    r = summarise_run_results(run_results, returncode=1)
    assert (r.tests_total, r.tests_passed, r.tests_failed) == (5, 3, 2)  # a skipped test counts as not passed
    assert not r.ok
    assert any("assert_totals" in f for f in r.failures)


def test_a_model_error_fails_the_run_even_if_every_test_passed():
    run_results = {"results": [result("model.larkspur.rpt_x", "error", "Binder Error: no such column"),
                               result("test.larkspur.unique_x", "pass")]}
    r = summarise_run_results(run_results, returncode=1)
    assert not r.ok and any("rpt_x" in f for f in r.failures)


def test_clean_run_is_ok():
    r = summarise_run_results({"results": [result("test.larkspur.a", "pass"), result("model.larkspur.b", "success")]}, 0)
    assert r == DbtResult(ok=True, tests_total=1, tests_passed=1, tests_failed=0, failures=())


def test_nonzero_exit_with_no_results_file_is_a_failure():
    r = summarise_run_results(None, returncode=2, output="Runtime Error: could not open database")
    assert not r.ok and "could not open database" in r.failures[0]
