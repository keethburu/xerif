# Colored heading style context regression

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

The dedicated `scripello/heading-context` branch and its pull requests run these
22 cases in the five-minute **Heading context regression** CI job. It pins Python,
the two Python wheels, action revisions, and both downloaded mapping inputs;
wheel and mapping SHA-256 checks reject changed dependencies. The installed
baseline is also required to fail the independent heading output assertions,
so an import or download error cannot satisfy the negative control. This job is
limited to the heading backport and does not render PDFs.

The same job runs `heading-config-schema.py` through lxml's real Relax NG
validator against the complete mapping. It uses the installed XML2TeX grammar
from commit `9d50c5185ed811cd3e9f2b946a5b720fd750b46a`, with SHA-256
`7c0832c800373fcdaac8df87b41ce2adbe4b5156c5d57500a8a1d5e1064a5181`.
The included `xslt2.rng` is checksum-verified too. The landed heading backport
at `3c2e95780c046105ed5c7aac4737e8c110c379d0` must be rejected specifically
at its unsupported explicit document constructor, while the current mapping
must validate. An untyped variable with sequence-constructor content creates
an implicit document node in XSLT 2.0, preserving the shared copy while using
instructions supported by this configuration grammar.

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

This is a mapping-level check. It does not certify generated TeX in the complete
pipeline or PDF output. Full rendering additionally requires the complete
transpect/CoCoTeX/LuaLaTeX pipeline; XML/XSLT-only results do not establish PDF
correctness.
