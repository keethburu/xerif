# Title and subtitle language regression

Run from this repository on the local render machine:

```sh
bash tests/title-language/run.sh /absolute/fresh/proof-directory
```

The runner uses the pinned Scripello check image only as a transpect/CoCoTeX,
LuaLaTeX, approved-font and veraPDF **toolchain**. It mounts this checkout's
`xml2tex/latex.conf.xml` and test files read-only; it does not test the xerif
configuration baked into that image. HEAD, uncommitted diff, input checksums,
base image digest, expanded Hub fixtures, generated TeX/TOC, glyph observations,
PDF text, PDFs and validator reports remain in the proof directory. It runs
locally under `/home/fm/fm-home/state/scripello-heavy.lock`, with no network,
3 CPUs / 4 GiB, a 600-second case limit and 180-second tool limits. It does not
start hosted rendering jobs or require private fonts or a reference PDF.

The independent oracle is the fixture's language contract: English titles and
French subtitles, and Greek titles and Hebrew subtitles, in a German book.
A small layout using existing CoCoTeX properties exposes both title and subtitle
in the body, TOC and running heads. A Lua shipout observer records the actual
glyph language IDs after Babel and shaping; these select LuaTeX's hyphenation
language tables. Expected IDs are obtained by explicit Babel language selection,
not from the configuration being tested. Latin examples prevent script-based
fallback from masking the defect; glyph coverage is checked separately.

The regression requires:

- Correct language on shipped title/subtitle glyphs in all three locations,
  including filtered running heads from a title containing a break and footnote.
- Both the default customer TOC route and the alternate filtered TOC route.
- German surrounding paragraphs, English chapter inheritance, and restoration
  of German after the inherited chapter.
- Text in the actual PDF and persisted TOC, with footnotes excluded from running
  heads and TOC.
- A successfully rendered original PDF whose English title fails the language
  assertion, proving the regression rejects the original behavior.
- Byte-identical generated TeX against the original when heading `xml:lang`
  attributes are removed, retaining numbering, emphasis and chapter inheritance.
- Configuration validity against the pinned xml2tex Relax NG schema.

The implementation ports upstream
[aa1374823adb419333e41d72e8a833b918af4387](https://github.com/transpect/xerif/commit/aa1374823adb419333e41d72e8a833b918af4387)
(2024-11-06). The fork also constructs filtered `tpRunTitle`/`tpRunSubtitle`
separately, so they need the same wrapper. Opening/closing wrappers are empty
without an own heading language. The closing brace is held in an XSL variable:
inside XSL conditionals, the schema validates rule attributes as literal-result
attribute value templates, where a bare closing brace would be invalid.

## Measured accessibility limit

The normal regression PDFs have no document `/Lang`, marked-content flag or
structure tree. veraPDF reports PDF/UA-1 noncompliance; those reports are retained.
The existing `a11y=true` path was also tried: LuaLaTeX stopped in `htmltabs.sty`
at undefined `\ccaAddToConfig`, before producing a PDF. Tagged-PDF language
semantics are therefore **blocked** in that path, and **absent** in the default
path. This regression proves actual Babel/hyphenation language selection and
content preservation; it does not establish PDF/UA compliance or language tags
in a tagged PDF. Accessibility integration remains a separate gate.
