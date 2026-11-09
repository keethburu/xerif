#!/usr/bin/env bash
# Run on a host with the pinned Scripello check image and Docker available.
set -euo pipefail
subject=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
image=${XERIF_TEST_IMAGE:?Set XERIF_TEST_IMAGE to the pinned check image digest}
docker run --rm --network none --read-only --memory 4g --cpus 3 \
  --mount "type=bind,src=$subject,dst=/subject,readonly" \
  --mount "type=bind,src=$subject/xml2tex/latex.conf.xml,dst=/opt/transpect/a9s/common/xml2tex/latex.conf.xml,readonly" \
  --mount type=volume,dst=/work --entrypoint python "$image" /subject/tests/note-reference-render.py
