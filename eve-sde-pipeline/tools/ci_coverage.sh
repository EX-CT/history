#!/usr/bin/env bash
# usage: ci_coverage.sh DATASET OUTDIR
# Fetches Pyfa master eos/effects.py and the public EX-CT/eve-dogma-rs engine source, then classifies Pyfa effects.
# The engine effect names are the union of the live engine source and the committed snapshot
# tools/engine-effect-names.json, which is the fallback if the clone fails. The refreshed list goes to OUTDIR.
set -euo pipefail
DS=$1; OUT=$2; HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT" /tmp/cov/pyfa/eos
curl -sfL https://raw.githubusercontent.com/pyfa-org/Pyfa/master/eos/effects.py -o /tmp/cov/pyfa/eos/effects.py
SRC=()
rm -rf /tmp/cov/eve-dogma-rs
if git clone -q --depth 1 https://github.com/EX-CT/eve-dogma-rs /tmp/cov/eve-dogma-rs 2>/dev/null; then
  SRC=(--engine-src /tmp/cov/eve-dogma-rs/src)
  echo "engine source: EX-CT/eve-dogma-rs@$(git -C /tmp/cov/eve-dogma-rs rev-parse --short HEAD)"
else
  echo "WARN: could not clone EX-CT/eve-dogma-rs, using committed snapshot only" >&2
fi
python3 "$HERE/pyfa_effects.py" --pyfa /tmp/cov/pyfa --dataset "$DS" "${SRC[@]}" \
  --engine-names "$HERE/engine-effect-names.json" --dump-engine-names "$OUT/engine-effect-names.json" --out "$OUT"
if ! diff -q "$HERE/engine-effect-names.json" "$OUT/engine-effect-names.json" >/dev/null; then
  echo "NOTE: engine effect-name list changed vs committed snapshot (commit $OUT/engine-effect-names.json to update)"
fi
