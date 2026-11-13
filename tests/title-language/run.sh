#!/usr/bin/env bash
# Run from any checkout. Sources are bound from THIS checkout, never a worker path.
set -euo pipefail
repo=$(git -C "$(dirname -- "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
proof=${1:?usage: run.sh ABSOLUTE_FRESH_PROOF_DIRECTORY [BASE_REVISION]}
base_revision=${2:-e893853}
case "$proof" in /*) ;; *) echo 'Proof directory must be absolute' >&2; exit 2;; esac
if [ -e "$proof" ]; then echo 'Proof directory must be fresh' >&2; exit 2; fi
mkdir -p "$proof/reference"
image=ghcr.io/keethburu/scripello-worker-check@sha256:992eb9bf11f0fed0834a9a14227bc06f3d7dd65ff3274a87ef16ee7258390b14
git -C "$repo" rev-parse HEAD > "$proof/head.txt"
git -C "$repo" diff --binary HEAD > "$proof/uncommitted.diff"
git -C "$repo" show "$base_revision:xml2tex/latex.conf.xml" > "$proof/reference/latex.conf.xml"
sha256sum "$repo/xml2tex/latex.conf.xml" "$repo"/tests/title-language/* > "$proof/input-sha256.txt"
printf '%s\n' "$image" > "$proof/toolchain-image.txt"
run_case() {
  local name=$1
  local configuration=$2
  shift 2
  timeout --kill-after=15s 600s docker run --rm --network none --cpus 3 --memory 4g \
    --mount "type=bind,src=$repo/tests/title-language,dst=/tests,readonly" \
    --mount "type=bind,src=$configuration,dst=/opt/transpect/a9s/common/xml2tex/latex.conf.xml,readonly" \
    --mount "type=bind,src=$proof,dst=/proof" \
    --entrypoint python "$image" /tests/check.py "/proof/$name" "$@" \
    > "$proof/$name.log" 2>&1
}
# Shared heavy lock covers every real render/validator; each case has a finite bound.
exec 9>/home/fm/fm-home/state/scripello-heavy.lock
flock 9
run_case fixed "$repo/xml2tex/latex.conf.xml"
run_case fixed-standard-toc "$repo/xml2tex/latex.conf.xml" --standard-toc
# Original must really render, then fail our independent shipped-language assertions.
if run_case original "$proof/reference/latex.conf.xml"; then
  echo 'Regression unexpectedly passed on original' >&2; exit 1
fi
if [ ! -f "$proof/original/output.pdf" ] || ! grep -q 'AssertionError:.*Internationalization' "$proof/original.log"; then
  echo 'Original failed for a reason other than the reproduced language defect' >&2; exit 1
fi
# Byte comparison is on generated public TeX, including inherited-language scopes.
run_case untagged-fixed "$repo/xml2tex/latex.conf.xml" --untagged --emit-only
run_case untagged-original "$proof/reference/latex.conf.xml" --untagged --emit-only
cmp "$proof/untagged-fixed/xml2tex.tex" "$proof/untagged-original/xml2tex.tex"
# Check the configuration actually read inside each proof container against this checkout.
python3 - "$repo" "$proof" <<'PYTHON'
import hashlib
import json
from pathlib import Path
import sys
repo, proof = map(Path, sys.argv[1:])
expected = hashlib.sha256((repo / 'xml2tex/latex.conf.xml').read_bytes()).hexdigest()
fixtures = set()
for case in ('fixed', 'fixed-standard-toc'):
    result = json.loads((proof / case / 'result.json').read_text())
    assert result['configuration_sha256'] == expected, (case, result, expected)
    fixtures.add(result['fixture_sha256'])
assert len(fixtures) == 1, 'TOC cases did not use identical Hub input'
(proof / 'overlay-verified.json').write_text(json.dumps({
    'head': (proof / 'head.txt').read_text().strip(),
    'configuration_sha256': expected, 'fixture_sha256': next(iter(fixtures)),
}, indent=2) + '\n')
PYTHON
# Ensure the current checkout did not change underneath the proof.
sha256sum --check "$proof/input-sha256.txt" > "$proof/input-sha256-verified.txt"
printf '%s\n' 'PASS: body, subtitle, TOC, ordinary/filtered heads, language scope, original failure, untagged compatibility' > "$proof/PASS.txt"
cat "$proof/PASS.txt"
