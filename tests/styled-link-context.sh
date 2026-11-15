#!/usr/bin/env bash
# Full generator/Java acceptance; all output stays in the caller's scratch directory.
set -euo pipefail
subject=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
image=${XERIF_TEST_IMAGE:?Set an immutable local Scripello check image digest}
output=${XERIF_TEST_OUTPUT:?Set an absolute scratch output directory}
lock=${XERIF_TEST_LOCK:?Set the shared renderer lock path}
config=${XERIF_TEST_CONFIG:-$subject/xml2tex/latex.conf.xml}
case "$image" in sha256:*|*@sha256:*) ;; *) echo 'Use an immutable image digest' >&2; exit 2;; esac
case "$output" in /*) ;; *) echo 'Output must be absolute' >&2; exit 2;; esac
mkdir -p "$output"
git -C "$subject" rev-parse HEAD
docker image inspect "$image" --format '{{.Id}}'
sha256sum "$config" "$subject"/tests/styled-link-context.{xml,py,sh} "$subject/tests/StyledLinkBench.java"
flock -E 75 -w 120 "$lock" timeout 180s docker run --rm --network none --read-only \
  --memory 4g --memory-swap 4g --cpus 3 --pids-limit 256 \
  --mount "type=bind,src=$subject,dst=/subject,readonly" \
  --mount "type=bind,src=$config,dst=/opt/transpect/a9s/common/xml2tex/latex.conf.xml,readonly" \
  --mount "type=bind,src=$output,dst=/scout" \
  --entrypoint python "$image" /subject/tests/styled-link-context.py "$@"
