"""Unit tests for skill_frontmatter.parse_frontmatter.

Exercises happy path + every failure mode. Failures raise SystemExit (via the
`fail()` helper), so pytest matches against that.
"""

from pathlib import Path

import pytest

from skill_frontmatter import parse_frontmatter, parse_when_to_use_keywords


GOOD = """---
name: example
description: "Does the thing. Not for the other thing."
when_to_use: "trigger1, trigger2, 中文触发"
dispatch_intent: "Example dispatch intent"
---

# Example

body
"""


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(text)
    return p


def test_happy_path(tmp_path):
    fields = parse_frontmatter(write(tmp_path, GOOD))
    assert fields == {
        "name": "example",
        "description": "Does the thing. Not for the other thing.",
        "when_to_use": "trigger1, trigger2, 中文触发",
        "dispatch_intent": "Example dispatch intent",
    }


def test_dispatch_intent_optional_returns_empty(tmp_path):
    text = GOOD.replace('dispatch_intent: "Example dispatch intent"\n', "")
    fields = parse_frontmatter(write(tmp_path, text))
    assert fields["dispatch_intent"] == ""


def test_missing_opening_delimiter(tmp_path):
    with pytest.raises(SystemExit):
        parse_frontmatter(write(tmp_path, "name: example\n"))


def test_missing_closing_delimiter(tmp_path):
    with pytest.raises(SystemExit):
        parse_frontmatter(write(tmp_path, "---\nname: example\n"))


def test_missing_name(tmp_path):
    text = GOOD.replace("name: example\n", "")
    with pytest.raises(SystemExit):
        parse_frontmatter(write(tmp_path, text))


def test_missing_description(tmp_path):
    text = GOOD.replace(
        'description: "Does the thing. Not for the other thing."\n', ""
    )
    with pytest.raises(SystemExit):
        parse_frontmatter(write(tmp_path, text))


def test_legacy_metadata_version_rejected(tmp_path, capsys):
    text = GOOD.replace("---\n\n# Example", 'metadata:\n  version: "1.0.0"\n---\n\n# Example')
    with pytest.raises(SystemExit):
        parse_frontmatter(write(tmp_path, text))
    assert "STALE metadata.version" in capsys.readouterr().err


def test_unquoted_colon_in_value(tmp_path, capsys):
    # `description: foo: bar` is ambiguous (no quotes around the value).
    text = GOOD.replace(
        'description: "Does the thing. Not for the other thing."',
        "description: foo: bar",
    )
    with pytest.raises(SystemExit):
        parse_frontmatter(write(tmp_path, text))
    assert "UNQUOTED FRONTMATTER COLON" in capsys.readouterr().err


def test_invalid_quote_in_value(tmp_path, capsys):
    # Unterminated quoted string.
    text = GOOD.replace(
        'description: "Does the thing. Not for the other thing."',
        'description: "unterminated',
    )
    with pytest.raises(SystemExit):
        parse_frontmatter(write(tmp_path, text))
    assert "INVALID FRONTMATTER QUOTE" in capsys.readouterr().err


def test_keywords_lowercase_and_dedupe():
    kws = parse_when_to_use_keywords("Foo, FOO, bar, , 中文")
    assert kws == {"foo", "bar", "中文"}


def test_keywords_empty():
    assert parse_when_to_use_keywords("") == set()
