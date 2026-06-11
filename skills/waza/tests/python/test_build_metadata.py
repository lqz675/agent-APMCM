"""Unit tests for build_metadata codegen helpers.

These are the pure functions inside the codegen pipeline. Full drift detection
is covered by the shell smoke (tests/test_codegen.sh); here we test the small
transforms.
"""

import build_metadata as bm


def test_render_readme_rewrites_main_to_latest_asset():
    body = "curl https://raw.githubusercontent.com/tw93/Waza/main/scripts/setup-rule.sh"
    out = bm.render_readme(body, "9.9.9")
    assert "https://github.com/tw93/Waza/releases/latest/download/setup-rule.sh" in out
    assert "raw.githubusercontent.com" not in out


def test_render_readme_rewrites_pinned_version_to_latest_asset():
    body = "curl https://raw.githubusercontent.com/tw93/Waza/v1.2.3/scripts/setup-rule.sh"
    out = bm.render_readme(body, "9.9.9")
    assert "https://github.com/tw93/Waza/releases/latest/download/setup-rule.sh" in out
    assert "v1.2.3" not in out


def test_render_readme_no_change_when_already_latest_asset():
    body = "curl https://github.com/tw93/Waza/releases/latest/download/setup-rule.sh"
    assert bm.render_readme(body, "9.9.9") == body


def test_render_script_ref_pins_main():
    body = 'WAZA_REF="${WAZA_REF:-main}"'
    out = bm.render_script_ref(body, "9.9.9")
    assert out == 'WAZA_REF="${WAZA_REF:-v9.9.9}"'


def test_render_script_ref_repins_old_version():
    body = 'WAZA_REF="${WAZA_REF:-v1.2.3}"'
    out = bm.render_script_ref(body, "9.9.9")
    assert out == 'WAZA_REF="${WAZA_REF:-v9.9.9}"'


def test_render_dispatcher_injects_table():
    template = """# Header

## Routing

<!-- routing-table:start -->
<!-- routing-table:end -->

## Footer
"""
    skills = [
        {"name": "alpha", "dispatch_intent": "first thing"},
        {"name": "beta", "dispatch_intent": "second thing"},
    ]
    out = bm.render_dispatcher(template, skills)
    assert "| first thing | alpha | `skills/alpha/SKILL.md` |" in out
    assert "| second thing | beta | `skills/beta/SKILL.md` |" in out
    assert "<!-- routing-table:start -->" in out
    assert "<!-- routing-table:end -->" in out
    # Original Header and Footer preserved.
    assert "# Header" in out
    assert "## Footer" in out


def test_render_dispatcher_alphabetical():
    template = "<!-- routing-table:start -->\n<!-- routing-table:end -->"
    skills = [
        {"name": "zebra", "dispatch_intent": "z"},
        {"name": "apple", "dispatch_intent": "a"},
    ]
    out = bm.render_dispatcher(template, skills)
    apple_idx = out.index("apple")
    zebra_idx = out.index("zebra")
    assert apple_idx < zebra_idx
