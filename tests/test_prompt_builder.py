"""Tests for repair prompt builder (QALLM-12)."""

from app.domain.models import Finding
from app.repair.prompt_builder import SYSTEM_PROMPT, build_repair_prompt


def _make_finding(**kwargs) -> Finding:
    defaults = dict(
        tool="bandit",
        type="SECURITY",
        severity="HIGH",
        file="app/main.py",
        line=10,
        message="Use of eval() detected",
        rule_id="B307",
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def test_prompt_includes_finding_details():
    f = _make_finding()
    prompt = build_repair_prompt(f, "x = eval(input())", context_start_line=10)
    assert "bandit" in prompt
    assert "SECURITY" in prompt
    assert "HIGH" in prompt
    assert "B307" in prompt
    assert "eval()" in prompt
    assert "app/main.py" in prompt


def test_prompt_includes_code_context():
    ctx = "def foo():\n    eval('1+1')"
    prompt = build_repair_prompt(_make_finding(), ctx, context_start_line=5)
    assert "def foo():" in prompt
    assert "eval('1+1')" in prompt
    assert "line 5" in prompt


def test_prompt_includes_task_instruction():
    prompt = build_repair_prompt(_make_finding(), "x = 1", context_start_line=1)
    assert "Fix ONLY" in prompt
    assert "raw Python code" in prompt


def test_system_prompt_has_rules():
    assert "expert Python" in SYSTEM_PROMPT
    assert "no markdown" in SYSTEM_PROMPT.lower() or "no explanations" in SYSTEM_PROMPT.lower()
