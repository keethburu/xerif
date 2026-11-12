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
styles, direct normal-weight/upright overrides, and footnote-only phrases. They require
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
