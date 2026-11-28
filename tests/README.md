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
the two Python wheels, action revisions, and the downloaded mapping inputs;
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

## Chapter language transitions

`chapter-language-transition.xml` contains original CC0-1.0 synthetic fixtures.
`chapter-language-transition.py` executes the actual chapter selection/restoration
handler, title/subtitle handlers, running-head handlers, both TOC branches, and
mapped inline phrase wrappers. Like the heading runner above, it lowers only the
required mapping command/parameter subset; the root preamble and ordinary body
traversal are bounded stand-ins. It uses the real converter language function
from XML2TeX commit `9d50c5185ed811cd3e9f2b946a5b720fd750b46a`, file
`xsl/functions.xsl`, with SHA-256
`cc0e04208ac5c06618019df055375e7052b608db07ffc3274d0001dd6cc13745`.
It uses the same checksum-pinned inherited Docx2TeX mapping as the heading suite.

For native HE proof use Java 17, lxml 5.2.1, and the normally source-built
Cartavelio Saxon HE 12.10 JAR from commit
`95d1c544b435ab49cbc2ab4e175a8af22551e2d3`, SHA-256
`242956b0d00bcb5c083f463a07f400c76c47b58814118118566edb65069f1764`,
plus its XML Resolver dependency. The runner rejects a different engine JAR.
Point the arguments at verified local tooling; it downloads and installs nothing.

```sh
python3 -B tests/chapter-language-transition.py \
  --docx2tex-conf "$DOCX2TEX_CONF" --xml2tex-functions "$XML2TEX_FUNCTIONS" \
  --saxon-jar "$SAXON_JAR" --resolver-jar "$RESOLVER_JAR" --output "$OUTPUT"
```

The output directory retains the exact fixtures, lowered stylesheets and emitted
TeX. `--config` selects an earlier mapping for the negative control. The CI job
also runs the suite with its existing pinned SaxonC 12.9.0 dependency via
`--existing-ci-saxonche`, and requires the maintained pre-fix mapping at
`5a73cda7ec734fd08c91cd604e8ff72953ce6d60` to fail the English-to-Latvian
body assertion while the disconfirming mapped/untagged/root/last controls pass.
This CI cross-check is separate from the native HE proof.

Hand-authored expected languages check every emitted title/subtitle occurrence
and adjacent body marker, plus restoration after the final chapter. The 15 cases
cover English-to-Latvian-to-untagged, mapped French switches, explicit root and
absent chapter languages, a blank language, consecutive unmapped chapters,
reordered controls, an English-root mask, a French root, repeated mapped
chapters, and mapped heading/inline overrides after an unmapped chapter. Both
TOC routes run; the standard route uses its existing body-subtitle fallback.
The language-scope interpreter checks the generated TeX interface only. It
cannot establish actual shipped glyph language IDs, delayed running-head/TOC
execution, PDF language tags, PDF/UA, or installed-consumer acceptance. Those
require coordinated full-generator and native rendering tests with the exact
installed mapping and immutable consumer image, without source overlays.

## TOC inline language

`toc-inline-language.py` renders the synthetic `toc-inline-language.xml` in
the pinned Scripello worker. It compares literal labels and their break markers
with the compatibility mapping installed in that image, and checks the emitted
TeX for distinct link labels, styled script runs, and note references. Set
`SCRIPPELLO_HEAVY_LOCK` to the shared Scripello rendering lock before running the
commands.

```sh
(
  set -eu
  image=sha256:d19587429905c905c0fd8aa5b53d2a542a005ead00b30c14ee406e9de3514bc0
  output=$(mktemp -d "$PWD/.toc-language.XXXXXX")
  chmod a+rx "$output"
  run() {
    flock -w 60 "$SCRIPPELLO_HEAVY_LOCK" timeout 100 docker run --rm --pull never \
      --network none --cpus 3 --memory 4g \
      -v "$PWD/tests:/tests:ro" -v "$output:/output" \
      --entrypoint /opt/venv/bin/python "$@"
  }
  for route in standard customer; do
    run "$image" -B /tests/toc-inline-language.py "/output/base-$route" "$route" --compatibility-base
    run -v "$PWD/xml2tex/latex.conf.xml:/opt/transpect/a9s/common/xml2tex/latex.conf.xml:ro" \
      "$image" -B /tests/toc-inline-language.py "/output/$route" "$route" \
      --compatibility-tex "/output/base-$route/render/xml2tex.tex"
  done
)
```

## Note reference regression

`note-reference-hub.xml` is original synthetic text dedicated to the public domain
under CC0-1.0. It contains mixed footnote/endnote input, repeated references,
paragraph and blockquote notes in body, title and table paths, three chapters,
ordinary hyperlinks, Greek and Cyrillic text, a float, and a 120-row table.

Run the mapping-level regression with the same pinned Python dependencies and
inherited configuration used by the heading suite:

```sh
python3 -B tests/note-reference-mapping.py --docx2tex-conf /absolute/path/to/docx2tex/conf/conf.xml
```

It executes the actual note label, anchor, link and heading filter handlers
against the CC0 fixture, using the inherited superscript formatter and a bounded
note-macro stand-in. Hand-written fixture expectations require labels inside
paragraph and blockquote note bodies, semantic and empty references, literal
numeric/Roman/superscript/mixed-prose links, and ambiguity diagnostics. Both
`notes-per-chapter` settings must pass; filtered heading destinations omit the
note and its label. `--config` accepts an earlier mapping for a negative control.
The existing Heading context CI job runs this regression and requires the pinned
pre-port mapping to fail its rendered-body label assertion. This regression does
not test the complete XML2TeX generator, TeX counters, chapter resets, or PDF output.

Run `note-reference-render.sh` with Docker and `XERIF_TEST_IMAGE` set to an
immutable Scripello check image digest containing the real transpect/CoCoTeX/
LuaLaTeX pipeline and Python `pypdf`. The image must already contain the exact
checkout mapping: the checker verifies byte equality before rendering. The
script mounts the checkout read-only, records its HEAD, status, image ID and
source hashes, and does not overlay renderer files.
Use the task's shared heavy-work lock and an external timeout when required.
`XERIF_TEST_OUTPUT` optionally retains the output in an absolute host directory;
otherwise output is temporary. Run the negative control with an image and
checkout containing the earlier mapping.

The regression extracts actual PDF text for default footnotes, default endnotes,
and endnotes with chapter resets. A fourth render uses the bundled compiled
De Gruyter Brill small proof variant to check alternating chapter running heads;
the default proof package deliberately uses plain pages. Each repeated call must match its original
rendered mark. Separate assertions preserve the existing original-note sequence,
chapter policy, note bodies and explicit hyperlink text. The test also rejects
unresolved references and missing-glyph diagnostics, checks every numbered
continuation row across at least three pages and its chapter running head,
preserves the float and non-Latin text, and requires the ambiguity diagnostic in the conversion
log. This exercises output behavior rather than inspecting implementation text.
The checker retains the worker API used by the original merged notes suite;
consumer integration must verify it against the supported worker entrypoint and
record immutable source/image provenance. A mapping-level pass is not consumer
acceptance or proof of PDF/reset behavior.

## Supported reference semantics

Automatic references to note anchors use the label assigned inside the actual
rendered note. They do not derive numbers from saved display text or anchor
order. The supported anchor layouts are inside the note, immediately before the
note, or immediately before a phrase containing the note. A nonempty automatic
reference must retain the existing `FootnoteReference` or `EndnoteReference`
role on the link or its sole textual marker, and its entire text must be an
integer or Roman numeral. An empty link to a note anchor also
requests the automatic label. Page references keep their existing behavior.

An arbitrary hyperlink's text is explicit content, including numbers, Roman
numerals and superscripts. It is preserved. For note-like literal links or
mixed prose with a reference role, `XERIF_NOTE_REFERENCE_AMBIGUOUS` reports that
automatic numbering cannot be established. The renderer still produces a proof
with the explicit text; this diagnostic is an unresolved publication-review
condition, not a claim that the saved text matches the note. Do not grant
automatic publication readiness to such content without resolving its meaning.
The existing DOCX importer maps NOTEREF to a Hub link and can lose the field
identity when no reference role survives; this renderer does not guess it back.

These focused checks do not establish general house-style suitability or full
publication approval. Both remain content-dependent. No numbering policy,
page-wide note layout, or publication-ready setting is introduced here.
