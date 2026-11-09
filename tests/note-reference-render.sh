#!/usr/bin/env bash
# Run on a host with the pinned Scripello check image and Docker available.
set -euo pipefail
subject=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
image=${XERIF_TEST_IMAGE:?Set XERIF_TEST_IMAGE to the pinned check image digest}
config=${XERIF_TEST_CONFIG:-$subject/xml2tex/latex.conf.xml}
case "$image" in sha256:*|*@sha256:*) ;; *) echo "Use an immutable image digest" >&2; exit 2;; esac
output=(--mount type=volume,dst=/work)
if [[ -n "${XERIF_TEST_OUTPUT:-}" ]]; then
  mkdir -p "$XERIF_TEST_OUTPUT"
  output=(--mount "type=bind,src=$XERIF_TEST_OUTPUT,dst=/work")
fi
git -C "$subject" rev-parse HEAD
git -C "$subject" status --short
docker image inspect "$image" --format '{{.Id}}'
sha256sum "$config" "$subject"/tests/note-reference-{hub.xml,render.py,render.sh}
docker run --rm --network none --read-only --memory 4g --cpus 3 \
  --mount "type=bind,src=$subject,dst=/subject,readonly" \
  --mount "type=bind,src=$config,dst=/opt/transpect/a9s/common/xml2tex/latex.conf.xml,readonly" \
  "${output[@]}" --entrypoint python "$image" /subject/tests/note-reference-render.py
