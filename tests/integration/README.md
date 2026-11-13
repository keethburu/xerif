# Block-boundary line breaks (local integration test)

`block_linebreak.py` executes the real xml2tex configuration compiler, Hub-to-TeX
transform, and LuaLaTeX through the Scripello check toolchain's `xerif.render`
wrapper. It requires that toolchain (including PyMuPDF), not just Python. These
are local rendering tests; do not run the image or TeX jobs on hosted CI.

Mount the **current checkout** over `/opt/transpect/a9s/common` in an existing
check image. An image's ID identifies the toolchain, not the overlaid source.
Use a new empty output directory for each run. For example, with absolute paths
in `source_root`, `evidence`, and `heavy_lock`, and a local image ID in `image`:

```sh
mkdir -p "$evidence"
(
  exec 9>"$heavy_lock"
  flock -w 120 9 || exit 1
  container="xerif-break-$$"
  trap 'docker stop -t 5 "$container" >/dev/null 2>&1 || true' EXIT
  timeout --signal=TERM --kill-after=20s 240s \
  docker run --rm --name "$container" --network none --read-only --memory 4g --cpus 3 \
  --mount "type=bind,src=$source_root,dst=/opt/transpect/a9s/common,readonly" \
  --mount "type=bind,src=$evidence,dst=/work" \
  --entrypoint python "$image" \
  /opt/transpect/a9s/common/tests/integration/block_linebreak.py /work/proof
)
```

Record the toolchain image ID, current Git head and diff, source-file hashes,
and fixture hashes (`proof/results.json`) with each run. A timeout is a failed
run; the exit trap stops that invocation's container while still holding the
shared heavy-work lock. Preserve logs, generated TeX, and PDFs in the evidence
directory outside the source checkout.

The independent behavioral oracles are:

- Inline `br`: both words survive exactly once on distinct PDF baselines.
- Block image followed by `br`: LuaLaTeX succeeds and the PDF contains a visible
  image and both surrounding body markers exactly once.
- Block image, then text, then `br`: the text resumes horizontal mode, so its
  explicit break must still separate the two words. This counterfactual passes
  even before the correction; merely detecting a preceding image is insufficient.
- Plain body: all fixture text survives exactly once. Comparing its word boxes
  and emitted TeX with an original-source run checks unchanged body output.

The script fails on the original source's figure case with `There's no line
here to end` immediately after `end{tpFigure}`. It has no expected-failure mode.
The generated colored square and short manuscript are synthetic. No licensed
fonts or manuscript assets are included. The full consuming application's
assembly fixture remains a separate acceptance test; these small regressions
do not replace it or claim complete book-layout qualification.
