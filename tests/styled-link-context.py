"""Real Calabash generator and Java/Saxon regression, with independent TeX oracles.

Run through styled-link-context.sh. No PDF, fonts, network, or extracted mapping.
--baseline proves the old context defects while still requiring common controls.
--measure adds four-run transform allocation/timing samples, never a latency gate.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess

from lxml import etree as E
from scripello.styles.compiler import RENDER_PARAMETERS

R = Path('/scout')
S = Path('/subject/tests')
XSL = 'http://www.w3.org/1999/XSL/Transform'
D = 'http://docbook.org/ns/docbook'
C = 'http://www.w3.org/1996/css'
L = 'http://www.w3.org/1999/xlink'
XML = 'http://www.w3.org/XML/1998/namespace'
SAXON = '/opt/transpect/calabash/saxon/saxon10he.jar'
CP = ':'.join(['/scout', SAXON, '/opt/transpect/calabash/distro/lib/xmlresolver-5.2.2.jar', '/opt/transpect/calabash/distro/lib/xmlresolver-5.2.2-data.jar'])
checks = []


def check(ok, label):
    assert ok, label
    checks.append(label)
    print('PASS', label, flush=True)


def run(cmd, name, timeout=35, env=None, cwd=R):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    (R / (name + '.log')).write_text(p.stdout + '\n' + p.stderr)
    assert p.returncode == 0, (name, p.returncode, p.stderr[-3000:])
    return p


def bench(source, sheet, name, mode='xml2tex', repeats=1):
    p = run(['java', '-Xmx3072m', '-Xss1024k', '-cp', CP, 'StyledLinkBench', str(sheet), str(source), str(repeats), str(R / (name + '.tex')), mode], name)
    rows = [json.loads(s) for s in p.stdout.splitlines() if s.startswith('{')]
    check(len(rows) == repeats and all(s['engine'] == '10.5' for s in rows), name + ' actual Java HE 10.5 transforms')
    (R / (name + '.json')).write_text(json.dumps(rows, indent=2))
    return (R / (name + '.tex')).read_text(), rows, p.stderr


def generate(links, rules, depth=1, siblings=1):
    hub = E.Element('{' + D + '}hub', nsmap={None: D, 'css': C, 'xlink': L}, version='5.0')
    hub.set('{' + XML + '}lang', 'en')
    info = E.SubElement(hub, '{' + D + '}info')
    E.SubElement(info, '{' + D + '}title').text = 'Synthetic link context'
    css = E.SubElement(info, '{' + C + '}rules')
    for i in range(rules):
        E.SubElement(css, '{' + C + '}rule', name='r' + str(i), attrib={'{' + C + '}font-weight': 'bold'})
    chapter = E.SubElement(hub, '{' + D + '}chapter', attrib={'{' + XML + '}id': 'chapter'})
    E.SubElement(chapter, '{' + D + '}title').text = 'Chapter'
    for i in range(links):
        para = E.SubElement(chapter, '{' + D + '}para')
        link = E.SubElement(para, '{' + D + '}link', attrib={'{' + L + '}href': 'https://example.org/target'})
        for j in range(siblings):
            parent = link
            for _ in range(depth):
                attrs = {'role': 'r0'} if rules else {'{' + C + '}font-weight': 'bold'}
                parent = E.SubElement(parent, '{' + D + '}phrase', **attrs)
            parent.text = f'Link{i:04d}Child{j}'
    return hub


def common(text):
    # Literal expectations follow the public fixture and existing mapping contract.
    for token in [r'\textbf{Bold}', r'\textit{Italic}', r'\sout{Strike}',
                  r'\textbf{Before\textit{Nested}After}',
                  r'\href{https://example.org/a\_b?x=1&y=2\%20z\#dest}{',
                  r'\href{https://example.org/plain}{PlainText}',
                  'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN↩OPQRSTUVWXYZ0123456789',
                  'a\\_b\\%↩\\#↩\\&\\({\\sim}\\)\\{x\\}\\newline\nNext/↩abcdef?↩xyz=↩123',
                  r'Top\index[idx]{RangeTerm|)}',
                  r'\textbf{First/↩abc}|\textit{Second?↩xyz}\textbf{Third\textit{Deep}}',
                  r'\textit{Ordinary/abc?xyz=123}',
                  r'\footnote{Note/abc?xyz=123 \href{https://example.org/inner}{\textit{Inside/↩abc}}}',
                  r'\textcolor{red}{OutsideDirectRed}', r'\uline{OutsideUnder}',
                  'InternalText']:
        check(token in text, 'common emitted ' + token)
    check(r'\textbf{Normal}' not in text and r'\textit{Upright}' not in text, 'explicit direct style overrides')
    check(text.count(r'\footnote{NoteBody}') == 1, 'nested note emitted once')
    check('SameURL{[}\\url{https://example.org/a_b}{]}' in text, 'URL-equals-text path remains unchanged')
    check('↩↩' not in text, 'no duplicate tactical markers')


def context(text, baseline):
    if baseline:
        check(r'Inner\index[idx]{|)}' in text and r'Inner\index[idx]{RangeTerm|)}' not in text, 'baseline reproduces missing nested range term')
        check(r'\uline{Under}' in text and r'\textcolor{red}{DirectColor}' in text, 'baseline reproduces parent-style loss')
        check(r'DirectFrench|\foreignlanguage{french}{NestedFrench}' in text, 'baseline reproduces language ancestry loss')
    else:
        for token in [r'Inner\index[idx]{RangeTerm|)}',
                      r'\href{https://example.org/target}{Under}',
                      r'\href{https://example.org/target}{DirectColor}',
                      r'\textbf{DirectFrench|NestedFrench}',
                      r'\textbf{EnglishSameEnglish\foreignlanguage{french}{French}}']:
            check(token in text, 'original-context emitted ' + token)
        check(r'\index[idx]{|)}' not in text, 'all nested range ends retain their original term')
        # Body retains its outer title color; TOC strips it and both preserve the
        # link's italic text and its one-pass breaks. Title notes stay body-only.
        check(r'\tpTocTitle{\textbf{Heading \href{https://example.org/title}{\textit{Title/↩abc}}}}' in text, 'TOC link retains style and breaks with note/color filtered')
        check(text.count('TitleNote') == 1, 'title link note emitted only in body')
        check(r'\tpBMTitle{Heading Title/abc}' in text, 'bookmark keeps unbroken plain text and filters note')
        check(r'\tpTitle{\textbf{\textcolor{red}{Heading \href{https://example.org/title}{\textit{Title/↩abc\protect\footnote{TitleNote}}}}}}' in text, 'body title retains outer color, link style and note')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--measure', action='store_true')
    args = parser.parse_args()
    check(hashlib.sha256(Path(SAXON).read_bytes()).hexdigest() == '71231d4e69af2d04ef487d992e2ccfa1b2c0eaa5bcae6c867506ee0df1fa079a', 'pinned selected Saxon jar')
    receipts = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(SAXON), Path('/opt/transpect/docx2tex/conf/conf.xml'), Path('/opt/transpect/config/render.xpl'), Path('/opt/transpect/a9s/common/xml2tex/latex.conf.xml')]}
    (R / 'runtime-receipts.json').write_text(json.dumps(receipts, indent=2))
    (R / 'pipeline/debug/status').mkdir(parents=True, exist_ok=True)
    params = E.Element('{http://www.w3.org/ns/xproc-step}param-set')
    for k, v in RENDER_PARAMETERS.items():
        E.SubElement(params, '{http://www.w3.org/ns/xproc-step}param', name=k, value=v)
    (R / 'pipeline/params.xml').write_bytes(E.tostring(params))
    env = {**os.environ, 'HOME': str(R), 'TMPDIR': str(R), 'CATALOGS': '/opt/transpect/xmlcatalog/catalog.xml', 'SYSPROPS': '-Djava.io.tmpdir=/scout'}
    run(['bash', '/opt/transpect/calabash/calabash.sh', '-i', 'source=' + str(S / 'styled-link-context.xml'), '-i', 'params=/scout/pipeline/params.xml', '-o', 'result=/scout/pipeline/raw.tex', '/opt/transpect/config/render.xpl', 'debug-dir=file:///scout/pipeline/debug'], 'pipeline', timeout=55, env=env)
    sheet = R / 'pipeline/debug/xml2tex/08.config.xsl'
    text = (R / 'pipeline/raw.tex').read_text()
    common(text)
    context(text, args.baseline)
    run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-d', str(R), '-cp', CP, str(S / 'StyledLinkBench.java')], 'compile-driver')
    # Direct properties with no CSS rules are an independent materialized-shape
    # control, not a reimplementation/benchmark of Scripello assembly.
    material = E.parse(str(S / 'styled-link-context.xml'))
    ns = {'d': D, 'c': C}
    rules = {n.get('name'): dict(n.attrib) for n in material.findall('.//{' + C + '}rule')}
    for node in material.iter():
        for name, value in rules.get(node.get('role'), {}).items():
            if name != 'name' and name not in node.attrib:
                node.set(name, value)
    for node in material.findall('.//{' + C + '}rules'):
        node.getparent().remove(node)
    source = R / 'materialized.xml'
    material.write(str(source))
    text, _, _ = bench(source, sheet, 'materialized')
    common(text)
    context(text, args.baseline)
    if not args.baseline:
        for note in material.findall('.//{' + D + '}footnote'):
            note.attrib.pop('{' + XML + '}id', None)
        material.write(str(R / 'anonymous-notes.xml'))
        text, _, _ = bench(R / 'anonymous-notes.xml', sheet, 'anonymous-notes')
        check(text.count('NoteBody') == 1 and text.count('TitleNote') == 1, 'source identity preserves anonymous nested note numbering')
    # Instrument executable generated mapping, rather than counting source
    # occurrences: observe actual helper entries and context construction.
    generated = E.parse(str(sheet))
    function = generated.find(f'{{{XSL}}}function[@name="xml2tex:replace-recursive-linktext"]')
    message = E.Element('{' + XSL + '}message')
    message.text = 'LINK_HELPER_ENTRY'
    function.insert(1, message)
    traced = R / 'traced-generated.xsl'
    generated.write(str(traced))
    trace = E.fromstring(f'''<xsl:stylesheet version="2.0" xmlns:xsl="{XSL}" xmlns:css="{C}" xmlns:dbk="{D}" xmlns:xml2tex="http://transpect.io/xml2tex">
      <xsl:import href="{traced.as_uri()}"/>
      <xsl:key name="style" match="css:rule" use="trace(@name, concat('STYLE_ROOT ',generate-id(root(.))))"/>
      <xsl:template match="/*" mode="xml2tex:link-context" priority="1000000"><xsl:message>LINK_CONTEXT_BUILD</xsl:message><xsl:next-match/></xsl:template>
      <xsl:template match="*[parent::dbk:link]" mode="copy" priority="1000000"><xsl:message>OLD_CHILD_COPY</xsl:message><xsl:next-match/></xsl:template>
    </xsl:stylesheet>''')
    trace_path = R / 'trace.xsl'
    trace_path.write_bytes(E.tostring(trace))
    input_path = R / 'multiple-children.xml'
    input_path.write_bytes(E.tostring(generate(7, 13, depth=3, siblings=2)))
    text, _, messages = bench(input_path, trace_path, 'trace')
    roots = Counter(re.findall(r'STYLE_ROOT (\S+)', messages))
    evidence = {'helper_entries': messages.count('LINK_HELPER_ENTRY'), 'shared_context_builds': messages.count('LINK_CONTEXT_BUILD'), 'old_child_copies': messages.count('OLD_CHILD_COPY'), 'style_rules_per_root': dict(roots)}
    (R / 'construction-counts.json').write_text(json.dumps(evidence, indent=2))
    check(text.count(r'\href{') == 7 and all(text.count(f'Link{i:04d}Child{j}') == 1 for i in range(7) for j in range(2)), 'all sibling/deep sentinels emitted once')
    if not args.baseline:
        check(evidence['helper_entries'] == 7, 'one replacement evaluation per link')
        check(evidence['shared_context_builds'] == 1 and evidence['old_child_copies'] == 0, 'one shared context for siblings and descendants')
        check(len(roots) == 2 and set(roots.values()) == {13}, 'style key built once on source and once on shared context')
    else:
        check(len(roots) > 2 and evidence['old_child_copies'] >= 14, 'baseline repeats CSS-bearing copies and key construction')
    # Double links and CSS together: construction remains per source context,
    # while each key necessarily visits the larger inventory once.
    scaled = R / 'scaled-children.xml'
    scaled.write_bytes(E.tostring(generate(14, 26, depth=3, siblings=2)))
    text, _, messages = bench(scaled, trace_path, 'scaled-trace')
    scaled_roots = Counter(re.findall(r'STYLE_ROOT (\S+)', messages))
    scaled_evidence = {'helper_entries': messages.count('LINK_HELPER_ENTRY'), 'shared_context_builds': messages.count('LINK_CONTEXT_BUILD'), 'old_child_copies': messages.count('OLD_CHILD_COPY'), 'style_rules_per_root': dict(scaled_roots)}
    (R / 'scaled-construction-counts.json').write_text(json.dumps(scaled_evidence, indent=2))
    check(text.count(r'\href{') == 14, 'scaled trace emits every link')
    if not args.baseline:
        check(scaled_evidence['helper_entries'] == 14 and scaled_evidence['shared_context_builds'] == 1 and len(scaled_roots) == 2 and set(scaled_roots.values()) == {26}, 'doubling links and rules still builds one context and one key per tree')
    else:
        check(len(scaled_roots) > len(roots) and scaled_evidence['old_child_copies'] >= 28, 'baseline context/key construction grows with link siblings')
    # Observe actual returned nodes and real keys; expected context comes from
    # generate()'s independently fixed public document structure.
    probe = R / 'context-probe.xsl'
    probe.write_text(f'''<xsl:stylesheet version="2.0" xmlns:xsl="{XSL}" xmlns:dbk="{D}" xmlns:css="{C}" xmlns:xml2tex="http://transpect.io/xml2tex">
      <xsl:import href="{sheet.as_uri()}"/>
      <xsl:template match="/" mode="probe"><xsl:variable name="nodes" select="xml2tex:replace-recursive-linktext(//dbk:link/dbk:phrase)"/>
        <out roots="{{count($nodes/root(.))}}" rules="{{sum(for $r in $nodes/root(.) return count($r//css:rule))}}">
          <xsl:for-each select="$nodes"><n parent="{{local-name(..)}}" chapter="{{ancestor::dbk:chapter/@xml:id}}" english="{{lang('en')}}" id-hits="{{count(key('item-by-id','chapter'))}}" style-hits="{{count(key('style',@role))}}"/></xsl:for-each>
        </out>
      </xsl:template></xsl:stylesheet>''')
    value, _, _ = bench(input_path, probe, 'context-probe', mode='probe')
    doc = E.fromstring(value.encode())
    if not args.baseline:
        check(doc.get('roots') == '1' and doc.get('rules') == '13', 'returned siblings share one CSS inventory')
        check(len(doc) == 14 and all(dict(n.attrib) == {'parent': 'link', 'chapter': 'chapter', 'english': 'true', 'id-hits': '1', 'style-hits': '1'} for n in doc), 'all copied children retain parent, inherited language, ancestor ID and current-tree keys')
        plain = R / 'plain-links.xml'
        plain.write_bytes(E.tostring(generate(7, 0, depth=0)))
        _, _, messages = bench(plain, trace_path, 'plain-links')
        check('LINK_CONTEXT_BUILD' not in messages, 'plain-text-only links avoid a context copy')
    else:
        check(doc.get('roots') == '14' and all(n.get('id-hits') == '0' and n.get('english') == 'false' for n in doc), 'baseline loses original ID and inherited language context')
    if args.measure:
        samples = {}
        for rules in (1000, 0):
            source = R / f'measure-R{rules}.xml'
            source.write_bytes(E.tostring(generate(400, rules)))
            text, rows, _ = bench(source, sheet, f'measure-R{rules}', repeats=4)
            check(text.count(r'\href{') == 400 and all(text.count(f'Link{i:04d}Child0') == 1 for i in range(400)), 'measurement output retains every link')
            samples[str(rules)] = {'first_s': rows[0]['wall_s'], 'later_median_s': statistics.median(s['wall_s'] for s in rows[1:]), 'later_alloc_mib': statistics.median(s['thread_alloc_bytes'] for s in rows[1:]) / 2**20}
        (R / 'measurements.json').write_text(json.dumps(samples, indent=2))
        print(json.dumps(samples, indent=2))
    (R / 'result.json').write_text(json.dumps({'baseline': args.baseline, 'checks': checks, 'result': 'PASS'}, indent=2))


if __name__ == '__main__':
    main()
