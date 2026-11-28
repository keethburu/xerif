"""Execute styled heading language handlers (not the full generator or PDF).

Uses the existing bounded mapping harness and checksum-pinned inherited mapping.
Short ASCII link labels make tactical URL breaking and character conversion
irrelevant here; the native render regression covers those separately.
"""

import argparse
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile

from lxml import etree as E
from saxonche import PySaxonProcessor


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("heading_context", ROOT / "tests/heading-style-context.py")
heading = importlib.util.module_from_spec(spec)
spec.loader.exec_module(heading)
NS = heading.NS
XSL = heading.XSL


def stylesheet(config, inherited):
    base = heading.stylesheet(config, inherited)
    sheet = E.Element(base.tag, attrib=dict(base.attrib),
                      nsmap={**base.nsmap, "xlink": "http://www.w3.org/1999/xlink"})
    sheet.extend(base)
    lookup = sheet.xpath('xsl:function[@name="xml2tex:lang-to-babel-lang"]/xsl:sequence', namespaces=NS)[0]
    lookup.set("select", "if ($lang = ('en', 'en-US')) then 'english' else if ($lang = 'de') then 'ngerman' else ''")
    for name in ("xml2tex:add-tactical-breaks-by-string-length", "xml2tex:add-tactical-break-chars-in-linktext"):
        function = E.SubElement(sheet, f"{{{XSL}}}function", name=name)
        E.SubElement(function, f"{{{XSL}}}param", name="value")
        E.SubElement(function, f"{{{XSL}}}sequence", select="$value")
    # Execute inherited phrase-language behavior as well as the style wrappers.
    for node in inherited.xpath('c:template[starts-with(@context,"dbk:phrase[@xml:lang]")]', namespaces=NS):
        template = heading.compile_fragment(node)
        template.set("priority", "100")
        sheet.append(template)
    for node in config.xpath(
        'xsl:template[@mode="copy"]'
        ' | xsl:template[@name="toc-language-start"]'
        ' | xsl:template[starts-with(@match,"dbk:phrase[@xml:lang]")]'
        ' | xsl:function[@name="xml2tex:replace-recursive-linktext" or @name="xml2tex:optionally-encode-uri"]',
        namespaces=NS,
    ):
        sheet.append(copy.deepcopy(node))
    link = config.xpath('c:template[contains(@context,"dbk:link[@xlink:href != .]")]', namespaces=NS)
    assert len(link) == 1
    sheet.append(heading.compile_fragment(link[0]))
    return sheet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx2tex-conf", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "xml2tex/latex.conf.xml")
    args = parser.parse_args()
    assert hashlib.sha256(args.docx2tex_conf.read_bytes()).hexdigest() == heading.INHERITED_SHA256
    config = E.parse(str(args.config)).getroot()
    sheet = stylesheet(config, E.parse(str(args.docx2tex_conf)).getroot())
    # Each destination takes its selector, variables and tunnels from source.
    destinations = (
        ("body-title", 'c:template[contains(@context,"/dbk:info/dbk:title")]/c:rule[@name="tpTitle"]/c:param', False),
        ("body-subtitle", 'c:template[@context="dbk:info/dbk:subtitle"]/c:rule/c:param', True),
        ("running-title", 'c:template[@name="col-titles"]/xsl:choose/xsl:when[2]/c:rule/c:param', False),
        ("running-subtitle", 'c:template[@name="col-titles"]/xsl:if/xsl:if/c:rule[@name="tpRunSubtitle"]/c:param', True),
        ("standard-toc", 'c:template[@name="toc-titles"]/xsl:choose/xsl:when[2]/c:rule/c:param', False),
        ("customer-toc-title", 'c:template[@name="customer-toctitles"]/xsl:choose/xsl:otherwise/c:rule[@name="tpTocTitle"]/c:param', False),
        ("customer-toc-subtitle", 'c:template[@name="customer-toctitles"]//c:rule[@name="tpTocSubtitle"]/c:param', True),
    )
    failures = []
    with PySaxonProcessor(license=False) as processor, tempfile.TemporaryDirectory() as tmp:
        for language in ('en', 'en-US', 'lv', ''):
            attribute = f' xml:lang="{language}"' if language else ''
            source = Path(tmp) / "book.xml"
            content = ('Start<phrase xml:lang="de" css:font-weight="bold">Wort</phrase>|'
                       '<link xlink:href="https://example.org/contact"><phrase xml:lang="de" css:font-style="italic">Kontakt</phrase></link>|'
                       '<link xlink:href="mailto:info@example.org"><phrase xml:lang="de" css:font-weight="bold">Anfrage</phrase></link>|'
                       '<phrase xml:lang="lv" css:font-style="italic">Unknown</phrase>End')
            source.write_text('<hub xmlns="http://docbook.org/ns/docbook" xmlns:css="http://www.w3.org/1996/css" '
                              'xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="de"><chapter><info>'
                              f'<title{attribute}>{content}</title><subtitle{attribute}>{content}</subtitle>'
                              '</info></chapter></hub>')
            for name, query, subtitle in destinations:
                params = config.xpath(query, namespaces=NS)
                assert len(params) == 1, (name, len(params))
                param = params[0]
                probe = copy.deepcopy(sheet)
                driver = E.SubElement(probe, f"{{{XSL}}}template", match="/")
                context = '/dbk:hub/dbk:chapter/dbk:info'
                if name.startswith('body-'):
                    context += '/dbk:subtitle' if subtitle else '/dbk:title'
                loop = E.SubElement(driver, f"{{{XSL}}}for-each", select=context)
                for variable in param.xpath('ancestor::c:template/xsl:variable | preceding-sibling::xsl:variable', namespaces=NS):
                    loop.append(copy.deepcopy(variable))
                rendered_param = heading.compile_fragment(param)
                rendered_param.find(f"{{{XSL}}}apply-templates").set("mode", "xml2tex")
                loop.append(rendered_param)
                executable = processor.new_xslt30_processor().compile_stylesheet(stylesheet_text=E.tostring(probe).decode())
                actual = executable.transform_to_string(source_file=str(source))
                # Native unwrapped labels have no language wrapper. A mapped
                # heading must preserve the explicit overrides inside its scope.
                inline = language in ('en', 'en-US')
                german = lambda text: rf'\foreignlanguage{{ngerman}}{{{text}}}' if inline else text
                word = r'\textbf{Wort}'
                if language == 'lv' and 'toc' not in name:
                    word = rf'\foreignlanguage{{ngerman}}{{{word}}}'
                expected = ('Start' + german(word) + '|'
                            + r'\href{https://example.org/contact}{' + german(r'\textit{Kontakt}') + '}|'
                            + r'\href{mailto:info@example.org}{' + german(r'\textbf{Anfrage}') + '}|'
                            + r'\textit{Unknown}End')
                if inline:
                    expected = r'\protect\foreignlanguage{english}{' + expected + '}'
                expected = '{' + expected + '}'
                if actual != expected:
                    failures.append(f'{name}/{language or "untagged"}\nexpected: {expected!r}\nactual: {actual!r}')
                else:
                    print(f'PASS {name}/{language or "untagged"}')
    assert not failures, '\n\n'.join(failures)


if __name__ == '__main__':
    main()
