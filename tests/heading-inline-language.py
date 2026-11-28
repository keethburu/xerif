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
    E.SubElement(sheet, f"{{{XSL}}}variable", name="langs", select="/dbk:hub/@xml:lang")
    for node in inherited.xpath('xsl:variable[@name="footnotes" or @name="footnote-ids"]', namespaces=NS):
        sheet.append(copy.deepcopy(node))
    for node in inherited.xpath(
        'c:template[starts-with(@context,"dbk:phrase[@xml:lang]") or starts-with(@context,"dbk:para[xml2tex:lang-to-babel-lang")]',
        namespaces=NS,
    ):
        template = heading.compile_fragment(node)
        template.set("priority", "100")
        sheet.append(template)
    for node in inherited.xpath('c:template[@context="dbk:footnote"]', namespaces=NS):
        template = heading.compile_fragment(node)
        template.set("priority", "-80")
        sheet.append(template)
    for node in config.xpath(
        'xsl:template[@mode="copy"]'
        ' | xsl:template[@name="toc-language-start"]'
        ' | xsl:template[starts-with(@match,"dbk:phrase[@xml:lang]")]'
        ' | xsl:function[@name="xml2tex:replace-recursive-linktext" or @name="xml2tex:optionally-encode-uri"]',
        namespaces=NS,
    ):
        sheet.append(copy.deepcopy(node))
    for node in config.xpath(
        'c:template[contains(@context,"dbk:link[@xlink:href != .]") or @context="dbk:ulink" or @context="dbk:footnote" or @context="dbk:footnote/dbk:para"]',
        namespaces=NS,
    ):
        template = heading.compile_fragment(node)
        if node.get("context") == "dbk:footnote":
            template.set("priority", "0")
        sheet.append(template)
    return sheet


def render(processor, sheet, config, destination, source):
    name, query, subtitle = destination
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
    return executable.transform_to_string(source_file=str(source))


def boundary_cases():
    restoration = (r'\foreignlanguage{english}{AfterEnglish}Nach}'
                   r'\foreignlanguage{ngerman}{Sibling}End')
    tail = ('<phrase xml:lang="en">AfterEnglish</phrase>Nach</phrase>'
            '<phrase xml:lang="de">Sibling</phrase>End')
    note = '<footnote><para xml:lang="de">Deutsch <phrase xml:lang="en">English</phrase></para></footnote>'
    yield ('footnote', 'T' + note + '<phrase xml:lang="de">Sibling</phrase>End',
           r'T\protect\footnote{%s\selectlanguage{ngerman}%%' + '\n'
           + r'Deutsch \foreignlanguage{english}{English}}\foreignlanguage{ngerman}{Sibling}End',
           r'T\foreignlanguage{ngerman}{Sibling}End')
    yield ('nested-footnote', '<phrase xml:lang="de">Vor' + note + tail,
           r'\foreignlanguage{ngerman}{Vor\protect\footnote{%s\selectlanguage{ngerman}%%' + '\n'
           + r'Deutsch \foreignlanguage{english}{English}}' + restoration,
           r'\foreignlanguage{ngerman}{Vor' + restoration)
    for element, target in (('ulink', 'https://example.org/profile'),
                            ('ulink', 'mailto:info@example.org'),
                            ('link', 'mailto:info@example.org')):
        label = target.removeprefix('mailto:')
        attribute = 'url' if element == 'ulink' else 'xlink:href'
        if element == 'ulink':
            content = f'<phrase xml:lang="en" css:font-style="italic">{label}</phrase>'
            formatted = r'\foreignlanguage{english}{\textit{' + label + '}}'
        else:
            content = f'<phrase css:font-style="italic"><phrase xml:lang="en">{label}</phrase></phrase>'
            formatted = r'\textit{\foreignlanguage{english}{' + label + '}}'
        expected = (r'\foreignlanguage{ngerman}{Vor\href{' + target + '}{' + formatted + '}' + restoration)
        yield (f'literal-{element}/{target.split(":")[0]}',
               f'<phrase xml:lang="de">Vor<{element} {attribute}="{target}">{content}</{element}>' + tail,
               expected, expected)
    expected = (r'\foreignlanguage{ngerman}{Vor\href{https://example.org/profile}'
                r'{\foreignlanguage{english}{\textit{Label}}}' + restoration)
    yield ('nonliteral-ulink',
           '<phrase xml:lang="de">Vor<ulink url="https://example.org/profile">'
           '<phrase xml:lang="en" css:font-style="italic">Label</phrase></ulink>' + tail,
           expected, expected)
    # Even a phrase matching the heading introduces suppression; a literal
    # label must release that scope before applying its nested override.
    expected = (r'Vor\href{https://example.org/@team/profile}'
                r'{\textit{\foreignlanguage{ngerman}{https://example.org/@team/profile}}}End')
    yield ('same-language-literal',
           '<phrase xml:lang="en">Vor<link xlink:href="https://example.org/@team/profile">'
           '<phrase css:font-style="italic"><phrase xml:lang="de">https://example.org/@team/profile'
           '</phrase></phrase></link>End</phrase>', expected, expected)
    yield from copied_note_cases()


def copied_note_cases():
    note = ('<footnote xml:id="n"><para xml:lang="de">Deutsch '
            '<phrase xml:lang="en">English</phrase></para>%s</footnote>')
    rendered_note = ('{\\footnote{\\selectlanguage{ngerman}%\n'
                     'Deutsch \\foreignlanguage{english}{English}%s}}')
    after = '<phrase xml:lang="de">Nach</phrase>'
    rendered_after = r'\foreignlanguage{ngerman}{Nach}'
    for target in ('http://example.org', 'https://example.org', 'ftp://example.org', 'mailto:info@example.org'):
        for multiple in (False, True):
            extra = '<para xml:lang="de">Zweit <phrase xml:lang="en">Second</phrase></para>' if multiple else ''
            rendered_extra = '\nZweit \\foreignlanguage{english}{Second}' if multiple else ''
            italic = r'{\itshape ' if multiple else r'\textit{'
            content = (f'<link xlink:href="{target}"><phrase css:font-style="italic">Label'
                       + note % extra + after + '</phrase></link>' + after)
            body = (r'\href{' + target + '}{' + italic + 'Label'
                    + rendered_note.replace('%s', rendered_extra) + rendered_after + '}}' + rendered_after)
            filtered = r'\href{' + target + '}{' + italic + 'Label' + rendered_after + '}}' + rendered_after
            yield (f'copied-note/{target.split(":")[0]}/{"multiple" if multiple else "single"}',
                   content, body, filtered)
            if not multiple:
                content = ('<phrase xml:lang="de">Vor' + content + '</phrase>' + after)
                body = (r'\foreignlanguage{ngerman}{Vor' + body.replace(rendered_after, 'Nach') + '}' + rendered_after)
                filtered = (r'\foreignlanguage{ngerman}{Vor' + filtered.replace(rendered_after, 'Nach') + '}' + rendered_after)
                yield (f'nested-copied-note/{target.split(":")[0]}', content, body, filtered)


def escape_stylesheet(config):
    sheet = E.fromstring(b'''<xsl:stylesheet version="2.0"
      xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
      xmlns:dbk="http://docbook.org/ns/docbook"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      xmlns:xml2tex="http://transpect.io/xml2tex">
      <xsl:output method="xml"/>
      <xsl:template match="/"><xsl:apply-templates select="." mode="escape-bad-chars"/></xsl:template>
      <xsl:template match="@* | node()" mode="escape-bad-chars" priority="-100">
        <xsl:copy><xsl:apply-templates select="@* | node()" mode="#current"/></xsl:copy>
      </xsl:template>
    </xsl:stylesheet>''')
    for node in config.xpath('xsl:template[@mode="escape-bad-chars"][contains(@match,"dbk:ulink")]', namespaces=NS):
        sheet.append(copy.deepcopy(node))
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
                actual = render(processor, sheet, config, (name, query, subtitle), source)
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
        escape = processor.new_xslt30_processor().compile_stylesheet(stylesheet_text=E.tostring(escape_stylesheet(config)).decode())
        for case, content, body, filtered in boundary_cases():
            subtitle_content = content.replace('xml:id="n"', 'xml:id="subtitle-n"')
            xml = ('<hub xmlns="http://docbook.org/ns/docbook" xmlns:css="http://www.w3.org/1996/css" '
                   'xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="en"><chapter><info>'
                   f'<title xml:lang="en">{content}</title><subtitle xml:lang="en">{subtitle_content}</subtitle>'
                   '</info></chapter></hub>')
            source.write_text(escape.transform_to_string(xdm_node=processor.parse_xml(xml_text=xml)))
            for destination in destinations:
                name, _, subtitle = destination
                actual = render(processor, sheet, config, destination, source)
                expected = body if name.startswith('body-') else filtered
                if 'footnote' in case and name.startswith('body-'):
                    expected = expected % ('' if subtitle else r'\protect')
                expected = r'{\protect\foreignlanguage{english}{' + expected + '}}'
                if actual != expected:
                    failures.append(f'{name}/{case}\nexpected: {expected!r}\nactual: {actual!r}')
                else:
                    print(f'PASS {name}/{case}')
        # Compatibility oracle: the native TOC contract (also checked by the
        # real renderer) leaves literal labels unchanged. An enclosing phrase
        # scope is tested separately above; it must still release suppression.
        for element, target in (('link', 'https://example.org/@team/profil'),
                                ('link', 'ftp://example.org/@team/profil'),
                                ('link', 'mailto:team@example.org'),
                                ('ulink', 'https://example.org/@team/profil')):
            label = target.removeprefix('mailto:')
            prefix, suffix = label.rsplit('/' if '/' in label else '@', 1)
            separator = '/' if '/' in label else '@'
            attribute = 'xlink:href' if element == 'link' else 'url'
            content = (f'<{element} {attribute}="{target}">{prefix}{separator}'
                       f'<phrase><phrase xml:lang="de">{suffix}</phrase></phrase></{element}>')
            xml = ('<hub xmlns="http://docbook.org/ns/docbook" xmlns:xlink="http://www.w3.org/1999/xlink" '
                   'xml:lang="de"><chapter><info>'
                   f'<title xml:lang="en">{content}</title><subtitle xml:lang="en">{content}</subtitle>'
                   '</info></chapter></hub>')
            source.write_text(escape.transform_to_string(xdm_node=processor.parse_xml(xml_text=xml)))
            for destination in destinations:
                name, _, _ = destination
                if 'toc' not in name:
                    continue
                actual = render(processor, sheet, config, destination, source)
                expected = (r'{\protect\foreignlanguage{english}{\href{'
                            + target + '}{' + label + '}}}')
                assert actual == expected, f'{name}/native-literal/{element}/{target}\nexpected: {expected!r}\nactual: {actual!r}'
                print(f'PASS {name}/native-literal/{element}/{target}')
    assert not failures, '\n\n'.join(failures)


if __name__ == '__main__':
    main()
