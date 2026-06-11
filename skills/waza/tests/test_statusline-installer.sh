#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

tmpdir=$(make_tmpdir)
home_dir="$tmpdir/home"
bin_dir="$tmpdir/bin"
mkdir -p "$home_dir/.claude" "$bin_dir"
ln -s "$(command -v python3)" "$bin_dir/python3"
ln -s "$(command -v jq)" "$bin_dir/jq"
ln -s /bin/chmod "$bin_dir/chmod"
ln -s /bin/mkdir "$bin_dir/mkdir"

# Stub curl: writes a tiny statusline script to the -o output path.
cat >"$bin_dir/curl" <<'CURL'
#!/bin/bash
outfile=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then outfile="$2"; shift 2; else shift; fi
done
printf "%s\n" "#!/bin/bash" "echo statusline" > "$outfile"
CURL

# Stub brew: must not be called when jq is on PATH.
cat >"$bin_dir/brew" <<'BREW'
#!/bin/bash
echo "brew should not be called" >&2
echo "$*" >>"$BREW_LOG"
exit 99
BREW
chmod +x "$bin_dir/curl" "$bin_dir/brew"

# Invalid JSON: installer must refuse and leave file untouched.
printf '%s\n' '{invalid json' > "$home_dir/.claude/settings.json"
if WAZA_REF='../../main' BREW_LOG="$tmpdir/brew.log" PATH="$bin_dir" HOME="$home_dir" /bin/bash "$ROOT/scripts/setup-statusline.sh" >"$tmpdir/bad-ref.out" 2>"$tmpdir/bad-ref.err"; then
  echo "setup-statusline should reject unsafe WAZA_REF"; exit 1
fi
grep -q 'WAZA_REF must be main or a release tag' "$tmpdir/bad-ref.err"
if BREW_LOG="$tmpdir/brew.log" PATH="$bin_dir" HOME="$home_dir" /bin/bash "$ROOT/scripts/setup-statusline.sh" >"$tmpdir/install.out" 2>"$tmpdir/install.err"; then
  echo "setup-statusline should refuse invalid JSON"; exit 1
fi
grep -q 'Refusing to modify it' "$tmpdir/install.err"
grep -q 'invalid json' "$home_dir/.claude/settings.json"
test ! -f "$tmpdir/brew.log"

# Valid JSON: installer merges statusLine, preserves other keys.
printf '%s\n' '{"theme":"dark"}' > "$home_dir/.claude/settings.json"
BREW_LOG="$tmpdir/brew.log" PATH="$bin_dir" HOME="$home_dir" /bin/bash "$ROOT/scripts/setup-statusline.sh" >"$tmpdir/install-valid.out" 2>"$tmpdir/install-valid.err"
python3 -c "import json, sys; data=json.load(open(sys.argv[1])); assert data['theme'] == 'dark'; assert data['statusLine']['command'] == 'bash ~/.claude/statusline.sh'" "$home_dir/.claude/settings.json"
test -x "$home_dir/.claude/statusline.sh"
test ! -f "$tmpdir/brew.log"

# Foreign statusLine already present: keep it intact, no overwrite.
printf '%s\n' '{"statusLine":{"type":"command","command":"bash ~/foreign.sh"}}' > "$home_dir/.claude/settings.json"
PATH="$bin_dir" HOME="$home_dir" /bin/bash "$ROOT/scripts/setup-statusline.sh" </dev/null >"$tmpdir/install-foreign.out" 2>"$tmpdir/install-foreign.err"
grep -q 'keeping existing statusline' "$tmpdir/install-foreign.out"
python3 -c "import json, sys; data=json.load(open(sys.argv[1])); assert data['statusLine']['command'] == 'bash ~/foreign.sh', data" "$home_dir/.claude/settings.json"

echo "statusline installer smoke: ok"
