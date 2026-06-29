"""Unit tests for the eval harness pure pieces (no network)."""

from app.ai.evals.cases import CASES, EvalCase, load_cases
from app.ai.evals.judge import Judgment, build_judge_messages, parse_judgment
from app.ai.evals.report import CaseResult, format_report, report_to_dict, summarize


def test_load_cases_filters_by_tag():
    safety = load_cases(("safety",))
    assert safety
    assert all("safety" in c.tags for c in safety)
    assert len(load_cases()) >= len(safety)


def test_parse_judgment_valid_json():
    j = parse_judgment('{"passed": true, "score": 0.8, "reason": "ok"}')
    assert j.passed is True
    assert j.score == 0.8
    assert j.reason == "ok"


def test_parse_judgment_strips_code_fence():
    raw = '```json\n{"passed": false, "score": 0.2, "reason": "missing VND"}\n```'
    j = parse_judgment(raw)
    assert j.passed is False
    assert j.score == 0.2
    assert j.reason == "missing VND"


def test_parse_judgment_clamps_score():
    assert parse_judgment('{"score": 5}').score == 1.0
    assert parse_judgment('{"score": -3}').score == 0.0


def test_parse_judgment_malformed_is_fail_not_crash():
    j = parse_judgment("not json at all")
    assert j.passed is False
    assert j.score == 0.0
    assert "Unparseable" in j.reason


def test_build_judge_messages_includes_prompt_rubric_answer():
    case = EvalCase(id="x", prompt="P", rubric="R", tags=())
    [msg] = build_judge_messages(case, "ANSWER")
    assert msg["role"] == "user"
    assert "P" in msg["content"]
    assert "R" in msg["content"]
    assert "ANSWER" in msg["content"]


def _result(cid: str, tags, passed: bool, score: float) -> CaseResult:
    return CaseResult(
        case=EvalCase(id=cid, prompt="", rubric="", tags=tags),
        answer="",
        judgment=Judgment(passed=passed, score=score, reason="r"),
    )


def test_summarize_overall_and_by_tag():
    results = [
        _result("a", ("safety",), True, 1.0),
        _result("b", ("safety", "write"), False, 0.0),
        _result("c", ("reporting",), True, 0.5),
    ]
    report = summarize(results)
    assert report.total == 3
    assert report.passed == 2
    assert abs(report.pass_rate - 2 / 3) < 1e-9
    assert abs(report.mean_score - 0.5) < 1e-9
    assert report.by_tag["safety"] == (1, 2)
    assert report.by_tag["write"] == (0, 1)
    assert report.by_tag["reporting"] == (1, 1)


def test_summarize_empty_is_safe():
    report = summarize([])
    assert report.total == 0
    assert report.pass_rate == 0.0
    assert report.mean_score == 0.0


def test_format_report_marks_pass_and_fail():
    results = [
        _result("ok-case", ("t",), True, 1.0),
        _result("bad-case", ("t",), False, 0.0),
    ]
    text = format_report(summarize(results), results)
    assert "PASS ok-case" in text
    assert "FAIL bad-case" in text


def test_report_to_dict_is_json_serializable_and_complete():
    import json

    results = [
        _result("a", ("safety",), True, 1.0),
        _result("b", ("ux",), False, 0.25),
    ]
    payload = report_to_dict(summarize(results), results)
    # round-trips through JSON (CI artifact / history file)
    assert json.loads(json.dumps(payload))["total"] == 2
    assert payload["passed"] == 1
    assert payload["by_tag"]["safety"] == {"passed": 1, "total": 1}
    ids = {c["id"] for c in payload["cases"]}
    assert ids == {"a", "b"}


def test_case_ids_are_unique():
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids))


def test_regression_cases_present():
    # The bugs we fixed must each keep a permanent guard case.
    ids = {c.id for c in CASES}
    assert "regression-no-fake-success" in ids
    assert "regression-no-detail-duplication" in ids
