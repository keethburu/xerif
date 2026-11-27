"""Execute note handlers against the original CC0 manuscript.

The maintained reference contract is the oracle: semantic/empty repeats read a
label inside the rendered note; literal text survives. This bounded XSLT check
does not run the XML2TeX generator, TeX counters, or PDF engine.
"""

import argparse
import copy
import hashlib
import runpy
import tempfile
from pathlib import Path

from lxml import etree as E
from saxonche import PySaxonProcessor


ROOT = Path(__file__).resolve().parents[1]
HELPERS = runpy.run_path(str(ROOT / "tests/heading-style-context.py"))
XSL = HELPERS["XSL"]
CONF = HELPERS["CONF"]
NS = HELPERS["NS"]


def stylesheet(config, inherited, policy):
    sheet = E.fromstring(b'''<xsl:stylesheet version="2.0"
      xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
      xmlns:dbk="http://docbook.org/ns/docbook"
      xmlns:css="http://www.w3.org/1996/css"
      xmlns:xs="http://www.w3.org/2001/XMLSchema"
      xmlns:xml2tex="http://transpect.io/xml2tex">
      <xsl:output method="xml" omit-xml-declaration="yes"/>
      <xsl:key name="item-by-linkend" match="dbk:link" use="@linkend"/>
      <xsl:template match="*" mode="xml2tex" priority="-100">
        <xsl:apply-templates mode="#current"/>
      </xsl:template>
      <!-- Boundary stand-in for the engine-owned note macro, not its counters. -->
      <xsl:template match="dbk:footnote" mode="xml2tex" priority="-90">
        <xsl:text>\\footnote{</xsl:text>
        <xsl:apply-templates mode="#current"/>
        <xsl:text>}</xsl:text>
      </xsl:template>
      <xsl:template match="/">
        <results>
          <notes><xsl:for-each select="//dbk:footnote">
            <note><xsl:apply-templates select="." mode="xml2tex"/></note>
          </xsl:for-each></notes>
          <links><xsl:for-each select="//dbk:link">
            <link><xsl:apply-templates select="." mode="xml2tex"/></link>
          </xsl:for-each></links>
          <headings><xsl:for-each select="//dbk:title[.//dbk:footnote]">
            <body><xsl:apply-templates select="node()" mode="xml2tex"/></body>
            <toc><xsl:apply-templates select="node()" mode="xml2tex">
              <xsl:with-param name="toc-override" select="true()" tunnel="yes"/>
            </xsl:apply-templates></toc>
            <running><xsl:apply-templates select="node()" mode="xml2tex">
              <xsl:with-param name="run-override" select="true()" tunnel="yes"/>
            </xsl:apply-templates></running>
            <bookmark><xsl:apply-templates select="node()" mode="xml2tex">
              <xsl:with-param name="bm-override" select="true()" tunnel="yes"/>
            </xsl:apply-templates></bookmark>
          </xsl:for-each></headings>
        </results>
      </xsl:template>
    </xsl:stylesheet>''')
    E.SubElement(sheet, f"{{{XSL}}}variable", name="notes-per-chapter", select=f"'{policy}'")
    for node in config.xpath('xsl:variable[@name="link-refs" or @name="anchor-ids" or @name="anchor-digits"]', namespaces=NS):
        sheet.append(copy.deepcopy(node))
    for node in inherited.xpath('xsl:key[@name="style"]', namespaces=NS):
        sheet.append(copy.deepcopy(node))
    for node in inherited.findall(f"{{{CONF}}}template"):
        if node.get("context", "").startswith("dbk:superscript[not(dbk:footnote)]"):
            lowered = HELPERS["compile_fragment"](node)
            lowered.set("priority", "0")
            sheet.append(lowered)
    for node in config.findall(f"{{{CONF}}}template"):
        context = node.get("context", "")
        if (context in ("dbk:footnote", "dbk:footnote/dbk:para", "dbk:link[@linkend]")
                or context.startswith("dbk:footnote/*[")
                or context.startswith("dbk:anchor[@role eq 'start'")
                or context.startswith("dbk:title//dbk:footnote")):
            lowered = HELPERS["compile_fragment"](node)
            lowered.set("priority", node.get("priority", "10" if context.startswith("dbk:title//") else "0"))
            sheet.append(lowered)
    return sheet


def check(result, messages, source, policy):
    # Independent fixture ledger: anchor indices include the ordinary anchor,
    # while Extra is an unreferenced note. Neither is a note-number oracle.
    indices = {"alpha": 1, "beta": 3, "tabnote": 4, "gamma": 5,
               "delta": 6, "title-note": 7, "quote-note": 8, "quote-table": 9}
    bodies = ("Alpha note body.", "Extra note body.", "Beta note body.",
              "Table note body.", "Gamma note body.", "Delta note body.",
              "Title quotation body.", "Quotation note body.", "Table quotation body.")
    note_indices = (1, None, 3, 4, 5, 6, 7, 8, 9)
    actual_notes = [n.text or "" for n in result.findall("notes/note")]
    assert len(actual_notes) == len(bodies), actual_notes
    for actual, body, index in zip(actual_notes, bodies, note_indices):
        label = rf"\label{{note-ref-{index}}}" if index is not None else ""
        assert label + body in actual, (policy, "rendered-body label missing", body, actual)
        assert actual.count(r"\label{") == (index is not None), actual
        prefix = r"\protect\footnote{" if index == 7 else r"{\footnote{"
        assert actual.startswith(prefix), actual
    links = source.xpath("//dbk:link", namespaces={"dbk": "http://docbook.org/ns/docbook"})
    outputs = [n.text or "" for n in result.findall("links/link")]
    assert len(outputs) == len(links)
    # The accepted fixture's semantic references, in document order, plus its
    # empty links. Saved values intentionally disagree with real note numbers.
    semantic = {0, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}
    for position, (link, output) in enumerate(zip(links, outputs)):
        target = link.get("linkend")
        if position in semantic:
            label = rf"\ref*{{note-ref-{indices[target]}}}"
            if len(link) or (link.text or ""):
                label = r"\textsuperscript{" + label + "}"
            assert output == rf"{{\hyperlink{{ref-0{indices[target]}}}{{{label}}}}}", (position, output)
        else:
            # The inherited formatter may add grouping around superscripts.
            literal = "".join(link.itertext())
            assert literal in output, (policy, "literal link changed", literal, output)
            assert r"\ref*{note-ref-" not in output, output
    diagnostic = "XERIF_NOTE_REFERENCE_AMBIGUOUS: linkend=alpha; explicit link text retained."
    # The literal word "mix" also consists entirely of Roman-numeral letters;
    # the accepted implementation warns while retaining that text.
    assert messages.count(diagnostic) == 8, messages
    headings = result.find("headings")
    assert r"\label{note-ref-7}" in headings.findtext("body"), E.tostring(headings)
    for destination in ("toc", "running", "bookmark"):
        assert headings.findtext(destination) == "Coverage chapter TitleMark", E.tostring(headings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx2tex-conf", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "xml2tex/latex.conf.xml")
    args = parser.parse_args()
    assert hashlib.sha256(args.docx2tex_conf.read_bytes()).hexdigest() == HELPERS["INHERITED_SHA256"]
    config = E.parse(str(args.config)).getroot()
    inherited = E.parse(str(args.docx2tex_conf)).getroot()
    fixture = ROOT / "tests/note-reference-hub.xml"
    source = E.parse(str(fixture))
    with PySaxonProcessor(license=False) as processor, tempfile.TemporaryDirectory() as tmp:
        for policy in ("no", "yes"):
            path = Path(tmp) / "notes.xsl"
            path.write_bytes(E.tostring(stylesheet(config, inherited, policy)))
            executable = processor.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(path))
            executable.set_save_xsl_message(True)
            output = executable.transform_to_string(source_file=str(fixture))
            messages = executable.get_xsl_messages()
            check(E.fromstring(output.encode()), str(messages), source, policy)
            print(f"PASS note labels, literal/semantic links, diagnostics and heading filters (notes-per-chapter={policy})")


if __name__ == "__main__":
    main()
