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
role on the link or its sole textual marker. An empty link to a note anchor also
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
