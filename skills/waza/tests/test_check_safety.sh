#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

tmpdir=$(make_tmpdir)
repo="$tmpdir/repo"
mkdir -p "$repo"
(cd "$repo" && git init -q)
printf 'tracked\n' > "$repo/tracked.txt"
(cd "$repo" && git add tracked.txt)
printf 'draft\n' > "$repo/draft.txt"

status="$(cd "$repo" && git status --short --branch -uall)"
[[ "$status" == *"?? draft.txt"* ]] || {
  echo "fixture did not expose untracked file through status preflight"
  exit 1
}

skill="$ROOT/skills/check/SKILL.md"
rules="$ROOT/rules/anti-patterns.md"

grep -q '## Worktree Safety Preflight' "$skill"
grep -q 'git status --short --branch -uall' "$skill"
grep -q 'Treat modified, staged, and untracked files as user work' "$skill"

for forbidden in \
  'git switch' \
  'git checkout' \
  'git reset --hard' \
  'git clean' \
  'git stash -u' \
  'git stash --include-untracked' \
  'git stash -a' \
  'git stash --all' \
  'gh pr checkout'; do
  grep -q "$forbidden" "$skill" || {
    echo "missing forbidden worktree command in /check safety docs: $forbidden"
    exit 1
  }
done

for safe_pr_command in \
  'gh pr view' \
  'gh pr diff' \
  'git fetch origin pull/<n>/head:refs/tmp/pr-<n>' \
  'git merge-tree'; do
  grep -q "$safe_pr_command" "$skill" || {
    echo "missing read-only PR inspection command: $safe_pr_command"
    exit 1
  }
done

grep -q 'Review request as worktree authorization' "$rules"
grep -q 'git status --short --branch -uall' "$rules"

echo "check safety smoke: ok"
