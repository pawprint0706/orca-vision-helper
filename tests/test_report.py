"""Vision report parsing with staged fallback (ported from VGMCP, plan §7.7)."""

from __future__ import annotations

from orca_vision_helper import report as report_mod


def test_parse_direct_json():
    r = report_mod.try_parse('{"summary": "ok", "issues": []}')
    assert r is not None and r.summary == "ok" and not r.parse_degraded


def test_parse_fenced_json():
    raw = (
        "분석 결과입니다:\n```json\n{\"summary\": \"s\", \"issues\": "
        "[{\"severity\": \"high\", \"description\": \"d\"}]}\n```\n끝."
    )
    r = report_mod.try_parse(raw)
    assert r is not None
    assert r.issues[0].severity == "high"
    assert r.raw_text == raw


def test_parse_plain_brace_block():
    raw = '여기 결과:\n{"summary": "s", "issues": [{"element": "button"}]}'
    r = report_mod.try_parse(raw)
    assert r is not None
    assert r.summary == "s"
    assert r.issues[0].element == "button"


def test_parse_invalid_returns_none():
    assert report_mod.try_parse("그냥 평범한 설명, JSON 아님") is None


def test_degraded_preserves_raw():
    r = report_mod.degraded("첫 줄 요약\n둘째 줄")
    assert r.parse_degraded is True
    assert r.summary == "첫 줄 요약"
    assert r.raw_text == "첫 줄 요약\n둘째 줄"


def test_bad_severity_coerced():
    r = report_mod.try_parse(
        '{"summary":"s","issues":[{"severity":"critical","description":"d"}]}'
    )
    assert r.issues[0].severity == "medium"


def test_schema_instruction_present():
    assert '"summary"' in report_mod.SCHEMA_INSTRUCTION
    assert '"issues"' in report_mod.SCHEMA_INSTRUCTION
