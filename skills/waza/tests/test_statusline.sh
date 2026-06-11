#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

tmpdir=$(make_tmpdir)
json1='{"context_window":{"current_usage":{"input_tokens":10},"context_window_size":100},"rate_limits":{"five_hour":{"used_percentage":12,"resets_at":2000000000},"seven_day":{"used_percentage":34,"resets_at":2000003600}}}'
json2='{"context_window":{"current_usage":{"input_tokens":20},"context_window_size":100}}'
json_high='{"context_window":{"current_usage":{"input_tokens":30},"context_window_size":100},"rate_limits":{"five_hour":{"used_percentage":61,"resets_at":2000000000},"seven_day":{"used_percentage":63,"resets_at":2000003600}}}'
json_low='{"context_window":{"current_usage":{"input_tokens":40},"context_window_size":100},"rate_limits":{"five_hour":{"used_percentage":1,"resets_at":2000000000},"seven_day":{"used_percentage":61,"resets_at":2000003600}}}'

printf '%s' "$json1" | HOME="$tmpdir" bash "$ROOT/scripts/statusline.sh" >/dev/null
printf '%s' "$json2" | HOME="$tmpdir" bash "$ROOT/scripts/statusline.sh" >"$tmpdir/out2"
printf '%s' "$json2" | HOME="$tmpdir" bash "$ROOT/scripts/statusline.sh" >"$tmpdir/out3"
grep -q '"used_percentage": 12' "$tmpdir/.cache/waza-statusline/last.json"
printf '%s' "$json_high" | HOME="$tmpdir" bash "$ROOT/scripts/statusline.sh" >/dev/null
printf '%s' "$json_low" | HOME="$tmpdir" bash "$ROOT/scripts/statusline.sh" >"$tmpdir/out4"
grep -q '5h:' "$tmpdir/out2"
grep -q '7d:' "$tmpdir/out2"
grep -q '12%' "$tmpdir/out2"
grep -q '34%' "$tmpdir/out3"
grep -q '1%' "$tmpdir/out4"
grep -q '61%' "$tmpdir/out4"

# Live values override existing high-water mark.
tmpdir2=$(make_tmpdir)
mkdir -p "$tmpdir2/.cache/waza-statusline"
printf '%s\n' '{"seven_day":{"used_percentage":63,"resets_at":2000003600}}' > "$tmpdir2/.cache/waza-statusline/highwater.json"
printf '%s' "$json1" | HOME="$tmpdir2" bash "$ROOT/scripts/statusline.sh" >"$tmpdir2/out"
grep -q '12%' "$tmpdir2/out"
grep -q '34%' "$tmpdir2/out"

# Empty input must not crash; both rate-limit slots fall back to "--".
tmpdir3=$(make_tmpdir)
printf '' | HOME="$tmpdir3" bash "$ROOT/scripts/statusline.sh" >"$tmpdir3/out"
grep -q '5h: --' "$tmpdir3/out"
grep -q '7d: --' "$tmpdir3/out"

# Context >= 85% must render with red ANSI (\033[31m); usage >= 90% likewise red.
tmpdir4=$(make_tmpdir)
json_hot='{"context_window":{"current_usage":{"input_tokens":90},"context_window_size":100},"rate_limits":{"five_hour":{"used_percentage":95,"resets_at":2000000000},"seven_day":{"used_percentage":10,"resets_at":2000003600}}}'
printf '%s' "$json_hot" | HOME="$tmpdir4" bash "$ROOT/scripts/statusline.sh" >"$tmpdir4/out"
grep -q $'\033\[31m90%' "$tmpdir4/out"
grep -q $'\033\[31m95%' "$tmpdir4/out"

# resets_at in the past must clear the rate-limit slot, no stale "(0m)" output.
tmpdir5=$(make_tmpdir)
json_expired='{"context_window":{"current_usage":{"input_tokens":5},"context_window_size":100},"rate_limits":{"five_hour":{"used_percentage":42,"resets_at":1000000000},"seven_day":{"used_percentage":50,"resets_at":1000003600}}}'
printf '%s' "$json_expired" | HOME="$tmpdir5" bash "$ROOT/scripts/statusline.sh" >"$tmpdir5/out"
grep -q '5h: --' "$tmpdir5/out"
grep -q '7d: --' "$tmpdir5/out"

# Stale cache (older than CACHE_MAX_AGE = 6h) must not surface as live values
# when the current input lacks rate_limits.
tmpdir6=$(make_tmpdir)
mkdir -p "$tmpdir6/.cache/waza-statusline"
printf '%s\n' '{"rate_limits":{"five_hour":{"used_percentage":77,"resets_at":2000000000},"seven_day":{"used_percentage":88,"resets_at":2000003600}}}' \
  > "$tmpdir6/.cache/waza-statusline/last.json"
touch -t 200001010000 "$tmpdir6/.cache/waza-statusline/last.json"
printf '%s' "$json2" | HOME="$tmpdir6" bash "$ROOT/scripts/statusline.sh" >"$tmpdir6/out"
grep -q '5h: --' "$tmpdir6/out"
grep -q '7d: --' "$tmpdir6/out"

echo "statusline smoke: ok"
