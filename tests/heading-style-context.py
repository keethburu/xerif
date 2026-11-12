"""Execute the actual heading handler and selected inherited XSLT templates.

This is a bounded XSLT regression, not the xml2tex generator or a PDF render.
Expected TeX fragments are hand-written below, independently of the handler.
"""

import argparse
import copy
import hashlib
from pathlib import Path
import tempfile

from lxml import etree as E
from saxonche import PySaxonProcessor


ROOT = Path(__file__).resolve().parents[1]
XSL = "http://www.w3.org/1999/XSL/Transform"
CONF = "http://transpect.io/xml2tex"
NS = {"xsl": XSL, "c": CONF}
INHERITED_SHA256 = "dee9e30f77fd71e473494cf3958b14f2e2d6f652bbc76e3384e7d74738f7c1e9"


def xsl(name, **attributes):
    return E.Element(f"{{{XSL}}}{name}", **attributes)


def compile_fragment(node):
    """Lower only the cmd/param subset used by the selected filter templates."""
    if node.tag == f"{{{CONF}}}template":
        result = xsl("template", mode="xml2tex", match=node.get("context"), priority="1000")
    elif node.tag == f"{{{CONF}}}rule":
        assert node.get("type") == "cmd", E.tostring(node)
        result = xsl("if", test="true()")
        result.append(xsl("text"))
        result[-1].text = "\\" + node.get("name")
    elif node.tag in (f"{{{CONF}}}param", f"{{{CONF}}}option"):
        result = xsl("if", test="true()")
        result.append(xsl("text"))
        result[-1].text = "{" if node.tag.endswith("param") else "["
        apply = E.SubElement(result, f"{{{XSL}}}apply-templates", select=node.get("select", "node()"), mode="#current")
        for child in node:
            apply.append(compile_fragment(child))
        result.append(xsl("text"))
        result[-1].text = "}" if node.tag.endswith("param") else "]"
        return result
    elif node.tag == f"{{{CONF}}}with-param":
        result = xsl("with-param", **dict(node.attrib))
    else:
        assert not node.tag.startswith(f"{{{CONF}}}"), E.tostring(node)
        result = E.Element(node.tag, **dict(node.attrib))
        result.text = node.text
    for child in node:
        if isinstance(child.tag, str):
            result.append(compile_fragment(child))
    return result


def stylesheet(config, inherited):
    # Include the real current-tree key and the pure-XSLT style wrappers in
    # source order. No style predicate is reimplemented by this harness.
    result = E.fromstring(b'''<xsl:stylesheet version="2.0"
      xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
      xmlns:dbk="http://docbook.org/ns/docbook" xmlns:css="http://www.w3.org/1996/css"
      xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:tr="http://transpect.io"
      xmlns:xml2tex="http://transpect.io/xml2tex">
      <xsl:output method="text"/>
      <xsl:variable name="root" select="/"/>
      <xsl:variable name="verse-style" select="'verse'"/>
      <xsl:variable name="remove-textcolor-for-runningtitles" select="true()"/>
      <xsl:variable name="toc-header-regex" select="'^toc-title$'"/>
      <xsl:variable name="col-head-short-style" select="'^short$'"/>
      <xsl:variable name="col-head-left-style" select="'^left$'"/>
      <xsl:variable name="col-head-right-style" select="'^right$'"/>
      <xsl:key name="item-by-id" match="*[@xml:id]" use="@xml:id"/>
      <xsl:template match="*" mode="xml2tex" priority="-100"><xsl:apply-templates mode="#current"/></xsl:template>
      <xsl:template match="dbk:footnote" mode="xml2tex" priority="-90"><xsl:text>UNFILTERED-NOTE</xsl:text></xsl:template>
      <xsl:template match="dbk:indexterm" mode="xml2tex" priority="-90"><xsl:text>INDEX</xsl:text></xsl:template>
      <xsl:template match="dbk:link" mode="xml2tex" priority="-90">
        <xsl:value-of select="concat(ancestor::*[@xml:lang][1]/@xml:lang, '/', ancestor::dbk:chapter/@xml:id, '/', ancestor::dbk:title/@xml:id, '/', key('item-by-id', @linkend)/@xreflabel)"/>
      </xsl:template>
      <xsl:function name="tr:hex-rgb-color-to-ints"><xsl:param name="color"/><xsl:sequence select="255, 0, 0"/></xsl:function>
      <xsl:function name="tr:color-hex-rgb-to-keyword"><xsl:param name="color"/><xsl:sequence select="'red'"/></xsl:function>
    </xsl:stylesheet>''')
    for node in inherited.xpath('xsl:key[@name="style"] | xsl:variable[@name="text-style-elements"]', namespaces=NS):
        result.append(copy.deepcopy(node))
    wrappers = []
    for node in inherited.findall(f"{{{CONF}}}template"):
        context = node.get("context", "")
        if context.startswith("*[local-name() = $text-style-elements]") and any(
            name in context for name in ("@css:color", "@css:font-weight", "@css:font-style", "@css:text-decoration-line")
        ):
            if "matches(.," not in context:  # unrelated single-Greek-letter special case
                wrappers.append(node)
    assert len(wrappers) == 7, len(wrappers)
    for priority, node in enumerate(wrappers, 10):
        template = xsl("template", match=node.get("context"), mode="xml2tex", priority=str(priority))
        for child in node:
            template.append(copy.deepcopy(child))
        result.append(template)
    # Raw high-priority handlers and their copy helpers are used unchanged.
    for node in config.xpath('xsl:template[contains(@match,"@css:color")] | xsl:template[@mode="xml2tex:heading-without-color"] | xsl:function[@name="xml2tex:heading-node-in-copy"] | xsl:variable[@name="xml2tex:headings-without-color"]', namespaces=NS):
        result.append(copy.deepcopy(node))
    for context in ("dbk:br", "dbk:indexterm", "dbk:title//dbk:footnote\n                    |dbk:subtitle//dbk:footnote\n                    |dbk:author//dbk:footnote"):
        node = config.xpath('c:template[normalize-space(@context)=$context]', namespaces=NS, context=" ".join(context.split()))
        assert len(node) == 1, context
        result.append(compile_fragment(node[0]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx2tex-conf", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "xml2tex/latex.conf.xml")
    args = parser.parse_args()
    assert hashlib.sha256(args.docx2tex_conf.read_bytes()).hexdigest() == INHERITED_SHA256, "Use the documented pinned inherited mapping"
    config = E.parse(str(args.config)).getroot()
    style = stylesheet(config, E.parse(str(args.docx2tex_conf)).getroot())
    source = ROOT / "tests/heading-style-context.xml"
    base = (r"\textbf{Bold}|\textit{Italic}|\uuline{\sout{Decorated}}|"
            r"\textnormal{Normal}|\textup{Upright}|\textbf{RoleColor}|")
    context = "|de/chapter-1/title-1/Target"
    # TOC's fallback deliberately keeps heading breaks; running heads and
    # bookmarks replace them with spaces. Footnotes/index terms are filtered.
    expected = {
        "body-stripped": base + "\\textbf{Before\\tpBreak\nAfter\\protect\\footnote{Note}INDEX\\textit{Nested}}|\\protect\\footnote{OnlyNote}" + context,
        "toc": base + "\\textbf{Before\\tpBreak\nAfter\\textit{Nested}}|" + context,
        "running": base + r"\textbf{Before After\textit{Nested}}|" + context,
        "bookmark": base + r"\textbf{Before After\textit{Nested}}|" + context,
        "subtitle": "\\textit{Subtitle\\tpBreak\nNext\\protect\\footnote{SubNote}}|"
                    + r"\textbf{\textit{\uuline{\sout{Combined}}}}",
        "subtitle-bookmark": r"\textit{Subtitle Next}|\textbf{\textit{\uuline{\sout{Combined}}}}",
        "explicit-toc": r"\textit{\textcolor{red}{ExplicitTOC}}",
        "explicit-running": r"\textbf{\textcolor{red}{ExplicitRun}}",
        "nested-role-color": r"\textbf{Outer\textit{RoleOnly}}",
    }
    colored = (r"\textbf{\textcolor{red}{Bold}}|\textit{\textcolor{red}{Italic}}|"
               r"\textcolor{red}{\uuline{\sout{Decorated}}}|\textnormal{\textcolor{red}{Normal}}|"
               r"\textup{\textcolor{red}{Upright}}|"
               r"\textbf{\textcolor{red}{RoleColor}}|")
    expected["body"] = (colored + "\\textbf{\\textcolor{red}{Before\\tpBreak\nAfter"
                        + "\\protect\\footnote{Note}INDEX\\textit{\\textcolor{red}{Nested}}}}|"
                        + r"\protect\footnote{OnlyNote}|\textcolor{red}{de/chapter-1/title-1/Target}")
    expected["running-colored"] = (colored + r"\textbf{\textcolor{red}{Before After\textit{\textcolor{red}{Nested}}}}|"
                                   + r"|\textcolor{red}{de/chapter-1/title-1/Target}")
    expected["run-override"] = expected["running-colored"]
    title = "/dbk:hub/dbk:chapter[1]/dbk:info/dbk:title/node()"
    cases = [("body", title, {}),
             ("body-stripped", title, {"remove-textcolor": "true()"}),
             ("nested-role-color", "/dbk:hub/dbk:chapter[3]/dbk:info/dbk:title/node()", {"remove-textcolor": "true()"}),
             ("run-override", title, {"run-override": "true()"}),
             ("bookmark", title, {"bm-override": "true()"}),
             ("subtitle", "/dbk:hub/dbk:chapter[1]/dbk:info/dbk:subtitle/node()", {"remove-textcolor": "true()"}),
             ("subtitle-bookmark", "/dbk:hub/dbk:chapter[1]/dbk:info/dbk:subtitle/node()", {"bm-override": "true()"})]
    # Exercise actual destination selectors and tunnel settings from xerif.
    for name, template, branch in (("toc", "customer-toctitles", "otherwise"), ("running", "col-titles", "when[2]"), ("explicit-toc", "customer-toctitles", "when[1]"), ("explicit-running", "col-titles", "when[1]")):
        param = config.xpath(f'c:template[@name="{template}"]/xsl:choose/xsl:{branch}/c:rule[@name="' + ("tpTocTitle" if "toc" in name else "tpRunTitle") + '"]/c:param', namespaces=NS)[0]
        cases.append((name, param.get("select"), {p.get("name"): p.get("select") for p in param}))
        if name == "running":
            parameters = dict(cases[-1][2], **{"remove-textcolor": "false()"})
            cases.append(("running-colored", param.get("select"), parameters))
    failures = []
    with PySaxonProcessor(license=False) as processor, tempfile.TemporaryDirectory() as tmp:
        for name, select, parameters in cases:
            sheet = copy.deepcopy(style)
            copy_probe = E.SubElement(sheet, f"{{{XSL}}}template", match="/*",
                                      mode="xml2tex:heading-without-color", priority="100")
            E.SubElement(copy_probe, f"{{{XSL}}}message").text = "document-copy"
            E.SubElement(copy_probe, f"{{{XSL}}}next-match")
            driver = E.SubElement(sheet, f"{{{XSL}}}template", match="/")
            context_node = "/dbk:hub/dbk:chapter[2]/dbk:info" if name.startswith("explicit-") else "/dbk:hub/dbk:chapter[1]/dbk:info"
            context_loop = E.SubElement(driver, f"{{{XSL}}}for-each", select=context_node)
            if name.startswith("explicit-"):
                template_name = "customer-toctitles" if name == "explicit-toc" else "col-titles"
                variable_name = "toctitle-para" if name == "explicit-toc" else "runtitle-para"
                variable = config.xpath('c:template[@name=$template]/xsl:variable[@name=$variable]', namespaces=NS, template=template_name, variable=variable_name)[0]
                context_loop.append(copy.deepcopy(variable))
            apply = E.SubElement(context_loop, f"{{{XSL}}}apply-templates", select=select, mode="xml2tex")
            for key, value in parameters.items():
                E.SubElement(apply, f"{{{XSL}}}with-param", name=key, select=value, tunnel="yes")
            path = Path(tmp) / "probe.xsl"
            path.write_bytes(E.tostring(sheet))
            executable = processor.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(path))
            executable.set_save_xsl_message(True)
            actual = executable.transform_to_string(source_file=str(source))
            messages = executable.get_xsl_messages()
            copy_count = messages.size if messages is not None else 0
            if copy_count > 1:
                failures.append(f"{name}: copied the document {copy_count} times; at most one is allowed")
            if actual == expected[name]:
                print(f"PASS {name}")
            else:
                failures.append(f"{name}\nexpected: {expected[name]!r}\nactual:   {actual!r}")
    assert not failures, "\n\n".join(failures)


if __name__ == "__main__":
    main()
