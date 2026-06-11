#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

CHECKER="$ROOT/skills/health/scripts/check-maintainability.sh"

tmpdir=$(make_tmpdir)

# Project layout helper: writes the standard 3-section AGENTS.md.
write_standard_agents_md() {
  local file="$1"
  local boundary="${2:-Do not rewrite unrelated modules.}"
  printf '%s\n' \
    '## Project' \
    'Repository Map: src contains runtime code.' \
    '## Verification' \
    'Run `make test` before handoff.' \
    '## Boundaries' \
    "$boundary" \
    > "$file"
}

# Case 1: clean project -> PASS, verification PASS.
good="$tmpdir/good"
mkdir -p "$good/.github/workflows" "$good/docs" "$good/src"
write_standard_agents_md "$good/AGENTS.md"
printf 'test:\n\t@echo test\n' > "$good/Makefile"
printf '%s\n' \
  'name: ci' \
  'on: [push]' \
  'jobs:' \
  '  test:' \
  '    runs-on: ubuntu-latest' \
  '    steps:' \
  '      - run: make test' \
  > "$good/.github/workflows/test.yml"
printf '%s\n' 'export function ok() { return true }' > "$good/src/app.ts"
bash "$CHECKER" "$good" summary >"$tmpdir/good.out"
grep -q '^maintainability_status: PASS$' "$tmpdir/good.out"
grep -q '^verification_status: PASS$' "$tmpdir/good.out"

# Case 2: huge file, no AGENTS.md, no Makefile -> FAIL with named diagnostics.
bad="$tmpdir/bad"
mkdir -p "$bad/src"
ROOT_BAD="$bad" python3 -c "
import os
from pathlib import Path
p = Path(os.environ['ROOT_BAD']) / 'src/huge.ts'
p.write_text('\n'.join(f'const item{i} = {i}; // TODO fix' for i in range(1300)) + '\n')
"
bash "$CHECKER" "$bad" summary >"$tmpdir/bad.out"
grep -q '^maintainability_status: FAIL$' "$tmpdir/bad.out"
grep -q 'no agent instruction surface' "$tmpdir/bad.out"
grep -q 'no executable verification command discovered' "$tmpdir/bad.out"
grep -q 'src/huge.ts' "$tmpdir/bad.out"

# Case 3: huge files inside excluded dirs (node_modules / dist / build) must
# not surface in summary or deep output.
excluded="$tmpdir/excluded"
mkdir -p "$excluded/src" "$excluded/node_modules/pkg" "$excluded/dist" "$excluded/build"
write_standard_agents_md "$excluded/AGENTS.md" "Avoid generated directories."
printf 'test:\n\t@echo test\n' > "$excluded/Makefile"
printf '%s\n' 'export const ok = true;' > "$excluded/src/app.ts"
ROOT_EXC="$excluded" python3 -c "
import os
from pathlib import Path
root = Path(os.environ['ROOT_EXC'])
for path, n in [('node_modules/pkg/big.js', 2000), ('dist/out.js', 2000), ('build/big.py', 2000)]:
    (root / path).write_text('\n'.join('x' for _ in range(n)) + '\n')
"
bash "$CHECKER" "$excluded" summary >"$tmpdir/excluded.out"
if grep -qE 'node_modules|dist/out.js|build/big.py' "$tmpdir/excluded.out"; then
  echo "maintainability smoke should exclude generated/dependency directories"; exit 1
fi
bash "$CHECKER" "$excluded" deep >"$tmpdir/excluded-deep.out"
grep -q '^hotspot_ownership_status: PASS$' "$tmpdir/excluded-deep.out"
if grep -qE 'node_modules|dist/out.js|build/big.py' "$tmpdir/excluded-deep.out"; then
  echo "hotspot ownership smoke should exclude generated/dependency directories"; exit 1
fi

# Case 4: documented hotspot in AGENTS.md -> PASS, no warning.
hotspot_good="$tmpdir/hotspot-good"
mkdir -p "$hotspot_good/src"
printf '%s\n' \
  '## Project' \
  'Repository Map: src contains runtime code.' \
  '## Verification' \
  'Run `make test` before handoff.' \
  '## Boundaries' \
  'Do not rewrite unrelated modules.' \
  '## Hotspot Ownership' \
  '- `src/hotspot.ts`: owned runtime hotspot. Keep the module boundary stable and run `make test` after changes.' \
  > "$hotspot_good/AGENTS.md"
printf 'test:\n\t@echo test\n' > "$hotspot_good/Makefile"
ROOT_HG="$hotspot_good" python3 -c "
import os
from pathlib import Path
p = Path(os.environ['ROOT_HG']) / 'src/hotspot.ts'
p.write_text('\n'.join(f'export const item{i} = {i};' for i in range(900)) + '\n')
"
bash "$CHECKER" "$hotspot_good" deep >"$tmpdir/hotspot-good.out"
grep -q '^hotspot_ownership_status: PASS$' "$tmpdir/hotspot-good.out"
if grep -q 'large source files lack hotspot ownership or verification map' "$tmpdir/hotspot-good.out"; then
  echo "documented hotspot should not warn"; exit 1
fi

# Case 5: undocumented hotspot -> WARN with specific file named.
hotspot_bad="$tmpdir/hotspot-bad"
mkdir -p "$hotspot_bad/src"
write_standard_agents_md "$hotspot_bad/AGENTS.md"
printf 'test:\n\t@echo test\n' > "$hotspot_bad/Makefile"
ROOT_HB="$hotspot_bad" python3 -c "
import os
from pathlib import Path
p = Path(os.environ['ROOT_HB']) / 'src/huge.ts'
p.write_text('\n'.join(f'export const item{i} = {i};' for i in range(900)) + '\n')
"
bash "$CHECKER" "$hotspot_bad" deep >"$tmpdir/hotspot-bad.out"
grep -q '^maintainability_status: WARN$' "$tmpdir/hotspot-bad.out"
grep -q '^hotspot_ownership_status: WARN$' "$tmpdir/hotspot-bad.out"
grep -q 'src/huge.ts' "$tmpdir/hotspot-bad.out"

# Case 6: hotspot has ownership but no nearby verification -> WARN with reason.
hotspot_missing_test="$tmpdir/hotspot-missing-test"
mkdir -p "$hotspot_missing_test/src"
printf '%s\n' \
  '## Project' \
  'Repository Map: src contains runtime code.' \
  '## Verification' \
  'Run `make test` before handoff.' \
  '## Boundaries' \
  'Do not rewrite unrelated modules.' \
  '## Hotspot Ownership' \
  '- `src/hotspot.ts`: owned runtime hotspot. Keep the module boundary stable.' \
  > "$hotspot_missing_test/AGENTS.md"
printf 'test:\n\t@echo test\n' > "$hotspot_missing_test/Makefile"
ROOT_HM="$hotspot_missing_test" python3 -c "
import os
from pathlib import Path
p = Path(os.environ['ROOT_HM']) / 'src/hotspot.ts'
p.write_text('\n'.join(f'export const item{i} = {i};' for i in range(900)) + '\n')
"
bash "$CHECKER" "$hotspot_missing_test" deep >"$tmpdir/hotspot-missing-test.out"
grep -q '^hotspot_ownership_status: WARN$' "$tmpdir/hotspot-missing-test.out"
grep -q 'missing verification context' "$tmpdir/hotspot-missing-test.out"

# Case 7: multiple verification commands but no Makefile test/check/verify wrapper.
wrapper="$tmpdir/wrapper"
mkdir -p "$wrapper/.github/workflows" "$wrapper/scripts"
printf '%s\n' \
  '## Project' \
  'Repository Map: scripts contains verification.' \
  '## Verification' \
  'Run `./scripts/check.sh --no-format`.' \
  '## Boundaries' \
  'Keep checks non-mutating.' \
  > "$wrapper/AGENTS.md"
printf 'build:\n\t@echo build\n' > "$wrapper/Makefile"
printf '%s\n' '#!/bin/bash' 'exit 0' > "$wrapper/scripts/check.sh"
printf '%s\n' \
  'name: check' \
  'on: [push]' \
  'jobs:' \
  '  check:' \
  '    runs-on: ubuntu-latest' \
  '    steps:' \
  '      - run: ./scripts/check.sh --no-format' \
  > "$wrapper/.github/workflows/check.yml"
bash "$CHECKER" "$wrapper" summary >"$tmpdir/wrapper.out"
grep -q '^wrapper_status: WARN$' "$tmpdir/wrapper.out"
grep -q 'multiple verification commands discovered but Makefile lacks check/test/verify wrapper' "$tmpdir/wrapper.out"

# Case 8: broken markdown link in deep mode -> WARN with named source.
links="$tmpdir/links"
mkdir -p "$links"
printf '%s\n' \
  '## Project' \
  'Repository Map: root docs.' \
  '## Verification' \
  'Run `make test`.' \
  '## Boundaries' \
  'Keep docs valid.' \
  > "$links/AGENTS.md"
printf 'test:\n\t@echo test\n' > "$links/Makefile"
printf '%s\n' 'See [safe remove](journal/2026-03-11-safe-remove-design.md).' > "$links/SECURITY_AUDIT.md"
bash "$CHECKER" "$links" deep >"$tmpdir/links.out"
grep -q '^markdown_link_status: WARN$' "$tmpdir/links.out"
grep -q 'SECURITY_AUDIT.md:1 -> journal/2026-03-11-safe-remove-design.md' "$tmpdir/links.out"

# Case 9: inside a git repo, untracked source files are still part of the review
# surface. A local review must not go blind just because a new file has not been
# staged yet.
untracked="$tmpdir/untracked"
mkdir -p "$untracked/src"
write_standard_agents_md "$untracked/AGENTS.md"
printf 'test:\n\t@echo test\n' > "$untracked/Makefile"
(cd "$untracked" && git init -q && git add AGENTS.md Makefile)
ROOT_UT="$untracked" python3 -c "
import os
from pathlib import Path
p = Path(os.environ['ROOT_UT']) / 'src/new_hotspot.ts'
p.write_text('\n'.join(f'export const item{i} = {i};' for i in range(1300)) + '\n')
"
bash "$CHECKER" "$untracked" summary >"$tmpdir/untracked.out"
grep -q 'src/new_hotspot.ts' "$tmpdir/untracked.out"

echo "maintainability smoke: ok"
