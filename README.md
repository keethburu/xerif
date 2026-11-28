# xerif

**xerif** is an open-source automated typesetting system. It is based on XML
and TeX and is designed for the production of high-quality print and digital
publications.

xerif converts structured manuscripts into professionally typeset publications,
combining the flexibility of XML workflows with the typographic quality of TeX.
It is particularly suited for complex publications containing extensive
footnotes, mathematical formulas, tables, indexes, multilingual content, and
sophisticated layouts.

## Overview

A typical transpect pipeline including xerif would look like this:

```
Manuscript
   |
   | Word / XML / TeX / Markdown
   v
transpect conversion
   |
   v
   +--> Hub XML
   +--> HTML
   +--> XML (client-specific)
   |
   v
transpect conversion (xml2tex)
   |
   v
   +--> TeX (CoCoTeX)
   |
   v
typesetting (LuaTeX)
   |
   +--> PDF/X/UA
   |
   v
Validation (XML with Schematron/RelaxNG, PDF/UA with VeraPDF)
   |
   +--> HTML report
```

xerif uses the transpect framework for XML processing and workflow
orchestration. XProc pipelines coordinate the processing steps, XSLT performs
the transformations, and Schematron/Relax NG are used for validation.

## Features

### Professional typesetting

xerif handles complex publishing requirements out of the box:

- Long footnotes and endnotes
- Multi-page tables
- Complex figure layouts
- Mathematical formulas
- Indexes and registers
- Bibliographies
- Cross references and hyperlinks
- Automatic tables of contents and lists
- Professional page breaking and pagination

For automatic note references and diagnostics requiring publication review, see
the [supported reference semantics](tests/README.md#supported-reference-semantics).

### Accessibility

xerif can create standards-compliant accessible PDFs:

- PDF/UA output
- PDF tagging
- Alternative texts
- Metadata for assistive technologies

### Multilingual publishing

Thanks to Unicode, OpenType fonts, and advanced hyphenation support,
xerif supports many writing systems, including Latin-based languages,
Arabic, Hebrew, Chinese, Japanese, and Korean.

In Hub XML, use `xml:lang` on a heading's `title` or `subtitle` to select its
language in the TeX output. xerif uses the converter's Babel mapping for the
body heading and for running heads and table-of-contents entries generated from
that title or subtitle. If the converter has no mapping for the language code,
the heading uses the surrounding language.

At top-level chapter boundaries, a chapter with an unmapped language code does
not inherit the previous foreign chapter's Babel selection. The previous mapped
chapter restores the book's root language, just as it does before an untagged
chapter or a chapter explicitly using the root language. This also prevents the
selection from leaking into later untagged content. An unmapped code does not
become a supported Babel language through this fallback.

These language selections govern TeX typesetting. They do not establish PDF
language tagging, PDF/UA conformance, or accessibility acceptance.

In both standard and customer table-of-contents entries, a nonblank inline
`phrase` with its own mapped `xml:lang` retains that language when it differs
from the mapped language of the enclosing `title` or `subtitle`. This also
applies inside styled superscripts, subscripts, and distinct link labels.
Literal URL labels keep their existing URL rendering and language handling.

### Multiple input and output formats

Supported input formats include:

- Microsoft Word
- XML (DocBook, JATS/BITS, TEI, customer-specific XML)
- TeX
- Markdown

Output formats include:

- PDF
- XML
- EPUB
- HTML

## Technology

xerif is built around several open-source technologies:

- **transpect** – XML publishing framework and pipeline engine
- **XProc** – workflow orchestration
- **XSLT** – XML transformation
- **Schematron / Relax NG** – validation
- **xml2tex** – XML to TeX conversion
- **CocoTeX** – LuaTeX framework for professional books and journals
- **LuaTeX** – typesetting engine

The XML content is transformed into Hub XML and then converted into CocoTeX
syntax. Formatting is controlled through TeX style files rather than being
embedded directly into the generated TeX code, allowing reusable layouts for
publishers, imprints, series, and individual publications.

## Configuration

xerif uses the [transpect configuration cascade](https://transpect.github.io/tutorial.html#cascade) mechanism. This allows
publishers to define:

- Custom document templates
- Individual layouts
- Series-specific styles
- Publisher-specific rules
- Output configurations

without modifying the core processing pipelines. Usually you would want to store a client-specific configuration here:

```
a9s/common/ (this xerif repository)
  ├── (...)
a9s/my-client/
  ├── evolve-hub/ configuration for Hub preprocessing
  ├── xml2tex/ xml2tex configuration file
  ├── latex-oops CoCoTeX framework, typically included as submodule
```

Please see the [xml2tex README](https://github.com/transpect/xml2tex#configuration) on how to configure the xml2tex configuration.

