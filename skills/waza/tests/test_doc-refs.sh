#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

CHECKER="$ROOT/skills/health/scripts/check-doc-refs.sh"

tmpdir=$(make_tmpdir)
project="$tmpdir/project"
home_dir="$tmpdir/home"
mkdir -p "$project/docs" "$project/.claude/rules" "$project/.claude/skills/demo/references" "$home_dir/.claude/rules"
touch "$project/AGENTS.md" "$project/docs/existing.md" "$project/.claude/skills/demo/references/info.md" "$home_dir/.claude/rules/global.md"
printf '%s\n' 'See docs/existing.md, @AGENTS.md, and ~/.claude/rules/global.md.' > "$project/CLAUDE.md"
printf '%s\n' 'Use docs/existing.md from a nested rule file.' > "$project/.claude/rules/sample.md"
printf '%s\n' 'Use references/info.md from the skill directory.' > "$project/.claude/skills/demo/SKILL.md"

HOME="$home_dir" bash "$CHECKER" "$project" >"$tmpdir/ok.out"
grep -q 'doc references: ok' "$tmpdir/ok.out"

# Broken references: checker exits non-zero and names every missing target.
printf '%s\n' 'See docs/existing.md, docs/missing.md, and @MISSING.md.' > "$project/CLAUDE.md"
if HOME="$home_dir" bash "$CHECKER" "$project" >"$tmpdir/bad.out"; then
  echo "doc-ref check should reject missing references"; exit 1
fi
grep -q 'MISSING: CLAUDE.md:1 -> docs/missing.md' "$tmpdir/bad.out"
grep -q 'MISSING: CLAUDE.md:1 -> @MISSING.md' "$tmpdir/bad.out"

echo "doc references smoke: ok"
