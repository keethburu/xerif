# Note reference regression

`note-reference-hub.xml` is original synthetic text dedicated to the public domain
under CC0-1.0. It contains mixed footnote/endnote input, repeated references,
paragraph and blockquote notes in body, title and table paths, three chapters,
ordinary hyperlinks, Greek and Cyrillic text, a float, and a 120-row table.

Run `note-reference-render.sh` with Docker and `XERIF_TEST_IMAGE` set to an
immutable Scripello check image digest containing the real transpect/CoCoTeX/
LuaLaTeX pipeline and Python `pypdf`. The script mounts the checkout containing
it read-only and overlays that checkout's `xml2tex/latex.conf.xml` on the image's
renderer. It records the checkout HEAD, status, image ID and source hashes.
Use the task's shared heavy-work lock and an external timeout when required.
`XERIF_TEST_OUTPUT` optionally retains the output in an absolute host directory;
otherwise output is temporary. `XERIF_TEST_CONFIG` is only for a before-fix
negative control; leave it unset when validating the current checkout.

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

## Colored heading style context regression

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

The runner executes the checkout's actual colored-phrase handler and shared document-copy
helpers, the pinned inherited style key and seven style wrappers, and xerif's
heading footnote/index/break filters. It takes destination selectors and tunnel
parameters from the actual TOC and running-title configuration. Only the small
command/parameter subset needed by these filters is lowered to XSLT in the
harness; this does not execute the complete xml2tex generator. Color-name
helpers are fixed to the fixture's red input. An instrumented link checks
ancestor language, chapter/title IDs, and a current-tree ID lookup outside the
heading.

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
without an inline color attribute. Break expectations preserve
the existing distinction between TOC fallback and running/bookmark output.
A copy-mode execution probe also requires at most one document copy per
transformation, rejecting repeated full-book copies for sibling or nested phrases.
The pre-fix configuration fails these output assertions.

This is a mapping-level check, separate from the standard-library XML syntax
CI. It does not certify generated TeX in the complete pipeline or PDF output.
Full rendering additionally requires Docker and the immutable Scripello check
image described above; XML/XSLT-only results do not establish PDF correctness.

## Heading configuration schema regression

The shared heading-copy variable uses an implicit document node because the
installed XML2TeX configuration grammar rejects an explicit `xsl:document`.
Run the complete mapping through the actual Relax NG validator:

```sh
python3 -B tests/heading-config-schema.py --schema /absolute/path/to/schema/xml2tex.rng
```

Use `schema/xml2tex.rng` and its sibling `schema/xslt2.rng` from
[XML2TeX commit 9d50c5185ed811cd3e9f2b946a5b720fd750b46a](https://github.com/transpect/xml2tex/tree/9d50c5185ed811cd3e9f2b946a5b720fd750b46a/schema).
The checker pins both installed schema checksums in its `SCHEMA_SHA256` and
`XSLT_SCHEMA_SHA256` constants. Optional `--baseline-config` accepts only the
original main mapping at `d001ddcbef646f419ae978c50de4741af90052fa` and requires
its rejection specifically at the unsupported document constructor.

The five-minute heading CI job runs this schema check, all 22 heading cases
and the shared-copy probe, and the installed-baseline output negative control.
It uses pinned actions, Python and wheel hashes with read-only permissions.
These checks complement the existing XML syntax CI; they do not run the full
XML2TeX generator or establish a whole-corpus or PDF pass.

## Styled link context regression

`styled-link-context.xml` is public synthetic CC0-1.0 input. The full regression
runs the image's actual Calabash generator and Java Saxon HE 10.5, with this
checkout's mapping overlaid read-only. It uses no PDF renderer, private fonts,
network or extracted/stubbed mapping. The known local evidence image is
`ghcr.io/keethburu/scripello-worker-check@sha256:ded69ce10466b9d20d6a14520c57de161897d35ab63a2035f13451e974c2185a`;
this historical image is a test input, not a current runtime release.

```sh
XERIF_TEST_IMAGE=sha256:ded69ce10466b9d20d6a14520c57de161897d35ab63a2035f13451e974c2185a \
XERIF_TEST_OUTPUT=/absolute/scratch/candidate \
XERIF_TEST_LOCK=/absolute/shared-renderer.lock \
bash tests/styled-link-context.sh --measure
```

Docker must already have the immutable image. The runner never pulls/builds an
image. It waits at most 120 seconds for the supplied shared lock, then runs one
serial container with a 180-second timeout, three CPUs, 4 GiB RAM, no additional
swap and a 3072 MiB Java heap. Output, generated stylesheets, runtime
checksums and logs stay in the caller's scratch directory; checkout HEAD, image
ID and source checksums are printed to stdout. The selected Saxon
jar's checksum and actual version are verified.

Hand-written TeX assertions cover nested index range ends, parent-sensitive
underline/color suppression, inherited and explicit language, role styles and
direct overrides, sibling/deep inline content, one-pass URL escaping and breaks,
notes with/without IDs, links inside notes, internal/plain/URL-equals-text links,
and non-link controls. A heading link checks body color/notes, filtered TOC style,
and plain bookmark text. A separate executable probe inspects returned nodes'
ancestors, language and real current-tree style/ID keys.

Diagnostic instrumentation observes actual replacement-function entries, shared
context construction and additive style-key visits on generated XSLT. Seven and
fourteen links, with two depth-three children each and thirteen/twenty-six CSS
rules, must each build one shared link context and one style index on each of the
source and shared trees. Plain-text-only links must avoid a link-context copy.
The existing color-filtered heading tree is derived from that shared tree when
needed for heading links, so their text is never replaced twice. Notes in copied
link content return to their original nodes for identity-based numbering.

For an independent before-fix control, set `XERIF_TEST_CONFIG` to the original
mapping from xerif `0d7ca05322a15d1c5ad15ed0a4665b6293f80d7a`, use a separate
output directory and add `--baseline`. This requires the same common output
controls while explicitly reproducing missing nested range terms, changed
parent/language selections and repeated CSS-bearing copies/key construction.
It does not accept those defects as candidate behavior.

`--measure` reports first-transform time, the median of three later transforms
and transform-thread allocation for synthetic 400-link inputs with 1,000 retained
rules or zero rules/direct styles. The zero-rule control has a materialized shape;
it does not execute Scripello assembly. Compilation, parsing, escape preprocessing
and serialization are outside the transform timer. Allocation is cumulative
churn, not live heap; process high-water RSS includes compilation and prior runs.
These limited local measurements do not establish normal Scripello latency or
PDF correctness. A styled-link transformation keeps one additional full source
context tree; its cost also depends on the rest of the document.

## Standalone XHTML export regression

Run with the transpect Calabash launcher and a dedicated scratch directory:

```sh
CATALOGS="$PWD/tests/xhtml-export-catalog.xml" \
  /path/to/transpect/calabash/calabash.sh tests/xhtml-export.xpl \
  scratch-dir-uri=file:///absolute/path/to/scratch
```

The catalog supplies stand-ins for external conversion and EPUB packaging. The
fixture runs Xerif's HTML and TEI pipelines, serializes their public `html`
outputs, and follows chapter and cover references from the publication directory.

Run the report fixture with the same launcher and its default runtime catalogs:

```sh
/path/to/transpect/calabash/calabash.sh tests/xhtml-report.xpl \
  scratch-dir-uri=file:///absolute/path/to/scratch
```

The fixture checks that the renderer locates the diagnostic and that the
serialized report keeps diagnostic text and usable locators without exposing the
source directory. Run it again with a separate scratch directory and
`source-dir-uri=https://editorial.example/private/book/` to exercise remote storage.
