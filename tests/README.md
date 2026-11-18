# Heading mapping regressions

`heading-style-context.xml` is original synthetic CC0-1.0 input. Run the focused
XSLT regression with Python, `lxml==5.2.1`, and `saxonche==12.9.0`:

```sh
python3 -B tests/heading-style-context.py --docx2tex-conf /absolute/path/to/docx2tex/conf/conf.xml
```

Use the plain XML [inherited mapping at docx2tex commit
6e1ffe7d259888f47ab3f311edc24b2e4c69147b](https://github.com/transpect/docx2tex/blob/6e1ffe7d259888f47ab3f311edc24b2e4c69147b/conf/conf.xml).
The runner verifies its SHA-256
`dee9e30f77fd71e473494cf3958b14f2e2d6f652bbc76e3384e7d74738f7c1e9`.
It makes no network requests. The optional `--config /absolute/path/to/latex.conf.xml`
supports a before-fix negative control.

Pushes to `scripello/heading-context` and pull requests targeting it run these
cases in the five-minute **Heading context regression** CI job. It pins Python,
the two Python wheels, action revisions, and both downloaded mapping inputs;
wheel and mapping SHA-256 checks reject changed dependencies. The installed
baseline is also required to fail the independent heading output assertions,
so an import or download error cannot satisfy the negative control.

The same job runs `heading-config-schema.py` through lxml's real Relax NG
validator against the complete mapping. The workflow pins the installed XML2TeX
grammar revision; the checker owns the required checksums for `xml2tex.rng`,
its adjacent include `xslt2.rng`, and the landed mapping. The landed heading backport
at `3c2e95780c046105ed5c7aac4737e8c110c379d0` must be rejected specifically
at its unsupported explicit document constructor, while the current mapping
must validate. See the `xml2tex:headings-without-color` declaration in
`xml2tex/latex.conf.xml` for the compatibility constraint on the shared copy.

```sh
python3 -B tests/heading-config-schema.py --schema /absolute/path/to/schema/xml2tex.rng --landed-config /absolute/path/to/landed-latex.conf.xml
```

The runner executes the checkout's actual colored-phrase handler and shared document-copy
helpers, the pinned inherited style key and seven style wrappers, and xerif's
heading footnote/index/break filters. It takes destination selectors and tunnel
parameters from the actual TOC and running-title configuration. Only the small
command/parameter subset needed by these filters is lowered to XSLT in the
harness; this does not execute the complete xml2tex generator. Color-name
helpers are fixed to the fixture's red input. An instrumented link checks
ancestor language, chapter/title IDs, and a current-tree ID lookup outside the
heading.

The running-head language cases stub the pinned converter's lookup with its
results for a mapped English title and an unmapped Latvian subtitle. See
[Multilingual publishing](../README.md#multilingual-publishing) for the heading
language behavior.

Hand-written expected fragments cover body output with color retained or
removed, TOC, running heads with color retained or removed, bookmark filtering,
subtitles, explicit title abbreviations, nested colored phrases, combined role
styles, direct normal-weight/upright overrides, and footnote-only phrases.
Nested colored footnote-only phrases in titles and subtitles must dissolve their
role wrapper in body output and leave no empty style wrapper in filtered destinations.
The nested case's independent expected body output is `Outer\protect\footnote{OnlyNote}`.
They require
role-derived bold, italic, underline style and strike-through to survive color
removal, while role-derived color stays suppressed, including on descendants
without an inline color attribute. The break assertions expect a line break in
the TOC entry derived from the full title and a space in the corresponding
running head and bookmark.
A copy-mode execution probe also requires at most one document copy per
transformation, rejecting repeated full-book copies for sibling or nested phrases.
The pre-fix configuration fails these output assertions.

This is a mapping-level check. It does not certify generated TeX in the complete
pipeline or PDF output. Full rendering additionally requires the complete
transpect/CoCoTeX/LuaLaTeX pipeline; XML/XSLT-only results do not establish PDF
correctness.

## TOC inline language

`toc-inline-language.py` renders the synthetic `toc-inline-language.xml` in
the pinned Scripello worker. It checks the emitted TeX for literal and distinct
link labels, styled script runs, and note references. Run it with the current
mapping mounted read-only. Set `SCRIPPELLO_HEAVY_LOCK` to the shared Scripello
rendering lock before running the commands.

```sh
image=sha256:d19587429905c905c0fd8aa5b53d2a542a005ead00b30c14ee406e9de3514bc0
output=$(mktemp -d "$PWD/.toc-language.XXXXXX")
chmod a+rx "$output"
for route in standard customer; do
  flock -w 60 "$SCRIPPELLO_HEAVY_LOCK" timeout 100 docker run --rm --pull never \
    --network none --cpus 3 --memory 4g \
    -v "$PWD/tests:/tests:ro" -v "$output:/output" \
    -v "$PWD/xml2tex/latex.conf.xml:/opt/transpect/a9s/common/xml2tex/latex.conf.xml:ro" \
    --entrypoint /opt/venv/bin/python "$image" -B /tests/toc-inline-language.py "/output/$route" "$route"
done
```
