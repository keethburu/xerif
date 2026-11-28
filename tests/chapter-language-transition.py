"""Execute chapter and heading mappings with checksum-pinned Saxon HE.

The observable contract is generated TeX language selection, not a PDF render.
Expected languages come from the documented root fallback and mapped overrides.
"""

import argparse
import copy
import hashlib
import os
from pathlib import Path
import re
import subprocess

from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
XSL = "http://www.w3.org/1999/XSL/Transform"
CONF = "http://transpect.io/xml2tex"
DBK = "http://docbook.org/ns/docbook"
NS = {"xsl": XSL, "c": CONF}
FUNCTIONS_SHA256 = "cc0e04208ac5c06618019df055375e7052b608db07ffc3274d0001dd6cc13745"
INHERITED_SHA256 = "dee9e30f77fd71e473494cf3958b14f2e2d6f652bbc76e3384e7d74738f7c1e9"
SAXON_SHA256 = "242956b0d00bcb5c083f463a07f400c76c47b58814118118566edb65069f1764"


def xsl(tag, **attrs):
    return E.Element(f"{{{XSL}}}{tag}", **attrs)


def lower(node):
    """Only the mapping cmd/param/template subset exercised by this fixture."""
    if node.tag == f"{{{CONF}}}template":
        attrs = ({"name": node.get("name")} if node.get("name") else
                 {"match": node.get("context"), "mode": "xml2tex",
                  "priority": node.get("priority", "100")})
        result = xsl("template", **attrs)
    elif node.tag == f"{{{CONF}}}rule":
        assert node.get("type") == "cmd", E.tostring(node)
        result = xsl("if", test="true()")
        E.SubElement(result, f"{{{XSL}}}text").text = "\\" + node.get("name")
    elif node.tag == f"{{{CONF}}}param":
        result = xsl("if", test="true()")
        E.SubElement(result, f"{{{XSL}}}text").text = "{"
        apply = E.SubElement(result, f"{{{XSL}}}apply-templates",
                             select=node.get("select", "node()"), mode="#current")
        for child in node:
            if isinstance(child.tag, str):
                apply.append(lower(child))
        E.SubElement(result, f"{{{XSL}}}text").text = "}"
        return result
    elif node.tag == f"{{{CONF}}}with-param":
        result = xsl("with-param", **dict(node.attrib))
    else:
        assert not node.tag.startswith(f"{{{CONF}}}"), E.tostring(node)
        result = E.Element(node.tag, **dict(node.attrib))
        result.text = node.text
    for child in node:
        if isinstance(child.tag, str):
            result.append(lower(child))
    return result


def stylesheet(config, inherited, functions, route):
    sheet = E.fromstring(rb'''<xsl:stylesheet version="2.0"
      xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
      xmlns:dbk="http://docbook.org/ns/docbook" xmlns:css="http://www.w3.org/1996/css"
      xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xml2tex="http://transpect.io/xml2tex">
      <xsl:output method="text"/>
      <xsl:variable name="verse-style" select="'verse'"/>
      <xsl:variable name="toc-header-regex" select="'^toc-title$'"/>
      <xsl:variable name="col-head-short-style" select="'^short$'"/>
      <xsl:variable name="col-head-left-style" select="'^left$'"/>
      <xsl:variable name="col-head-right-style" select="'^right$'"/>
      <xsl:variable name="remove-textcolor-for-runningtitles" select="false()"/>
      <xsl:variable name="create-TocAuthorNames-by-style" select="false()"/>
      <xsl:template match="*" mode="xml2tex" priority="-100"><xsl:apply-templates mode="#current"/></xsl:template>
      <xsl:template name="create-bookmark-content"/>
      <xsl:template match="/">
        <xsl:for-each select="suite/input">
          <xsl:text>CASE:</xsl:text><xsl:value-of select="@name"/><xsl:text>&#10;</xsl:text>
          <xsl:apply-templates select="document(@href)" mode="xml2tex"/>
          <xsl:text>AfterCase&#10;ENDCASE&#10;</xsl:text>
        </xsl:for-each>
      </xsl:template>
      <xsl:template match="/" mode="xml2tex">
        <xsl:value-of select="concat('\selectlanguage{', xml2tex:lang-to-babel-lang(/*/@xml:lang), '}')"/>
        <xsl:apply-templates select="/*/dbk:chapter" mode="#current"/>
      </xsl:template>
      <xsl:template match="dbk:info" mode="xml2tex" priority="-10">
        <xsl:apply-templates mode="#current"/>
        <xsl:call-template name="col-titles"/>
        <xsl:call-template name="toc-titles"/>
      </xsl:template>
      <xsl:template match="dbk:para" mode="xml2tex" priority="-10">
        <xsl:text>\Body{</xsl:text><xsl:apply-templates mode="#current"/><xsl:text>}</xsl:text>
      </xsl:template>
    </xsl:stylesheet>''')
    sheet.append(xsl("variable", name="create-customer-toctitles", select=str(route == "customer").lower() + "()"))
    sheet.append(copy.deepcopy(functions.xpath('xsl:function[@name="xml2tex:lang-to-babel-lang"]', namespaces=NS)[0]))
    sheet.append(copy.deepcopy(config.xpath('xsl:function[@name="xml2tex:heading-language-start"]', namespaces=NS)[0]))
    # Real mapped inline wrappers, including the TOC override from the maintained mapping.
    for node in inherited.xpath('xsl:variable[@name="text-style-elements"]', namespaces=NS):
        sheet.append(copy.deepcopy(node))
    for node in inherited.findall(f"{{{CONF}}}template"):
        if "suppress-foreign-lang" in E.tostring(node).decode() and "@xml:lang" in node.get("context", ""):
            sheet.append(lower(node))
    for node in config.xpath('xsl:template[@name="toc-language-start" or @match="dbk:phrase[@xml:lang][normalize-space()]"]', namespaces=NS):
        sheet.append(copy.deepcopy(node))
    for node in config.findall(f"{{{CONF}}}template"):
        context = node.get("context", "")
        if (node.get("priority") == "800" or node.get("name") in ("col-titles", "toc-titles", "customer-toctitles")
                or context == "dbk:info/dbk:subtitle" or context.endswith("/dbk:info/dbk:title")
                or context == "dbk:br"):
            sheet.append(lower(node))
    return sheet


def languages(tex):
    """Interpret only language scopes in the generated TeX fixture interface.

    This is deliberately not a TeX renderer. Every occurrence of each text marker
    is checked, including body, running, and TOC macro arguments.
    """
    state, stack, found = "unset", [], {}
    token = re.compile(r"\\selectlanguage\{([^{}]*)\}|\\(?:protect\\)?foreignlanguage\{([^{}]*)\}\{|[{}]|[A-Z][A-Za-z0-9]*")
    for match in token.finditer(tex):
        if match.group(1) is not None:
            assert match.group(1), "empty Babel selection"
            state = match.group(1)
        elif match.group(2) is not None:
            stack.append(state)
            state = match.group(2)
        elif match[0] == "{":
            stack.append(state)
        elif match[0] == "}":
            state = stack.pop()
        else:
            found.setdefault(match[0], []).append(state)
    assert not stack, "unbalanced language scopes"
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "xml2tex/latex.conf.xml")
    parser.add_argument("--docx2tex-conf", required=True, type=Path)
    parser.add_argument("--xml2tex-functions", required=True, type=Path)
    engine = parser.add_mutually_exclusive_group(required=True)
    engine.add_argument("--saxon-jar", type=Path)
    engine.add_argument("--existing-ci-saxonche", action="store_true",
                        help="Reuse the existing CI job's pinned saxonche==12.9.0")
    parser.add_argument("--resolver-jar", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    pinned_inputs = [(args.docx2tex_conf, INHERITED_SHA256), (args.xml2tex_functions, FUNCTIONS_SHA256)]
    if args.saxon_jar:
        if not args.resolver_jar:
            parser.error("--resolver-jar is required with --saxon-jar")
        pinned_inputs.append((args.saxon_jar, SAXON_SHA256))
    for path, expected in pinned_inputs:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"Unpinned input: {path}"
    args.output.mkdir(parents=True, exist_ok=True)
    suite = E.parse(str(ROOT / "tests/chapter-language-transition.xml")).getroot()
    manifest = E.Element("suite")
    expected_cases = {}
    for case in suite.findall("case"):
        hub = case.find(f"{{{DBK}}}hub")
        source = args.output / (case.get("name") + ".xml")
        source.write_bytes(E.tostring(hub))
        E.SubElement(manifest, "input", name=case.get("name"), href=source.resolve().as_uri())
        expected_cases[case.get("name")] = case
    assert expected_cases, "No fixture cases"
    manifest_path = args.output / "suite.xml"
    manifest_path.write_bytes(E.tostring(manifest))
    failures = []
    for route in ("standard", "customer"):
        sheet = stylesheet(E.parse(str(args.config)).getroot(), E.parse(str(args.docx2tex_conf)).getroot(),
                           E.parse(str(args.xml2tex_functions)).getroot(), route)
        sheet_path = args.output / (route + ".xsl")
        sheet_path.write_bytes(E.tostring(sheet))
        tex_path = args.output / (route + ".tex")
        if args.saxon_jar:
            subprocess.run(["java", "-Xmx256m", "-cp", os.pathsep.join(map(str, (args.saxon_jar, args.resolver_jar))),
                            "net.sf.saxon.Transform", "-t", "-s:" + str(manifest_path),
                            "-xsl:" + str(sheet_path), "-o:" + str(tex_path)], check=True, timeout=60)
        else:
            import saxonche
            assert saxonche.__version__ == "12.9.0", "Use the existing CI job's pinned engine"
            with saxonche.PySaxonProcessor(license=False) as processor:
                processor.new_xslt30_processor().transform_to_file(
                    source_file=str(manifest_path), stylesheet_file=str(sheet_path), output_file=str(tex_path))
        results = re.findall(r"CASE:([^\n]+)\n(.*?)ENDCASE", tex_path.read_text(), re.S)
        assert [name for name, _ in results] == list(expected_cases), "Missing, reordered or duplicate cases"
        for name, tex in results:
            case = expected_cases[name]
            selected = languages(tex)
            previous_failures = len(failures)
            for check in case.findall("expect"):
                marker, language = check.get("marker"), check.get("language")
                count = int(check.get("standard" if route == "standard" else "customer", "1"))
                actual = selected.get(marker, [])
                if actual != [language] * count:
                    failures.append(f"{route}/{name}/{marker}: expected {[language] * count}, actual {actual}")
            if len(failures) == previous_failures:
                print(f"PASS {route}/{name}")
    assert not failures, "chapter language selection\n" + "\n".join(failures)


if __name__ == "__main__":
    main()
