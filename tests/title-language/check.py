#!/usr/bin/env python3
"""Real Hub -> xml2tex -> CoCoTeX -> PDF regression; run in the pinned toolchain.

The oracle is the fixture's explicit title/subtitle language contract. Observe
LuaTeX's shipped glyph language IDs, PDF text, and persisted TOC, independently
of the configuration implementation. Output stays in the supplied fresh directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from lxml import etree
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = Path('/opt/transpect')
PARAMETERS = {
    'layout': 'c', 'pubtype': 'mono', 'format': '', 'toc-depth': '3',
    'numbering-depth': '3', 'title-pages': 'no', 'notes-type': 'footnotes',
    'notes-per-chapter': 'no', 'endnotes-with-chapter': 'no',
    'notes-per-chapter-notoc': 'yes', 'running-header': 'yes', 'run-local': 'yes',
}
DB = {'d': 'http://docbook.org/ns/docbook'}
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def command(args, directory, log, timeout=180, allowed=(0,)):
    env = {key: os.environ[key] for key in
           ('PATH', 'PROJECT_DIR', 'SAXON_JAR', 'HEAP', 'LUAINPUTS') if key in os.environ}
    env.update(HOME=str(directory), TMPDIR=str(directory), SOURCE_DATE_EPOCH='0',
               TEXMFOUTPUT=str(directory), CATALOGS=str(ROOT / 'xmlcatalog/catalog.xml'),
               SYSPROPS=f'-Djava.io.tmpdir={directory}', openin_any='p', openout_any='p',
               shell_escape='f', TEXINPUTS=f'.:{HERE}//:{ROOT / "config"}//:{ROOT / "latex"}//:')
    with (directory / log).open('wb') as stream:
        result = subprocess.run(args, cwd=directory, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout)
    assert result.returncode in allowed, f'{args[0]} exited {result.returncode}; see {directory / log}'
    return result.returncode


def emit(directory, *, untagged=False, standard_toc=False, a11y=False):
    schema = etree.RelaxNG(etree.parse(str(ROOT / 'xml2tex/schema/xml2tex.rng')))
    schema.assertValid(etree.parse(str(ROOT / 'a9s/common/xml2tex/latex.conf.xml')))
    directory.mkdir(parents=True)
    (directory / 'debug/status').mkdir(parents=True)
    (directory / 'fonts').symlink_to(ROOT / 'fonts', target_is_directory=True)
    fixture = etree.parse(str(HERE / 'book.xml'))
    if untagged:
        # Keep chapter inheritance and inline formatting; remove only own heading languages.
        for element in fixture.xpath('//d:info/d:title | //d:info/d:subtitle', namespaces=DB):
            element.attrib.pop(XML_LANG, None)
    # Guarantee subsequent pages on which the engine actually prints running heads.
    for chapter in fixture.xpath('/d:hub/d:chapter', namespaces=DB):
        paragraph = chapter.find('d:para', DB)
        for _ in range(115):
            chapter.append(etree.fromstring(etree.tostring(paragraph)))
    source = directory / 'book.xml'
    fixture.write(str(source), encoding='UTF-8', xml_declaration=True)
    params = etree.Element('{http://www.w3.org/ns/xproc-step}param-set')
    for key, value in {**PARAMETERS, **({'a11y': 'true'} if a11y else {})}.items():
        etree.SubElement(params, '{http://www.w3.org/ns/xproc-step}param', name=key, value=value)
    etree.ElementTree(params).write(str(directory / 'params.xml'))
    layout = etree.parse(str(HERE / 'layout.xml'))
    if standard_toc:
        etree.SubElement(layout.getroot(), '{http://www.w3.org/1999/XSL/Transform}variable',
                         name='create-customer-toctitles', select='false()')
    layout.write(str(directory / 'layout.xml'))
    command(['bash', str(ROOT / 'calabash/calabash.sh'), '-i', f'source={source}',
             '-i', f'params={directory / "params.xml"}', '-i', f'conf={directory / "layout.xml"}',
             '-o', f'result={directory / "xml2tex.tex"}', str(ROOT / 'config/render.xpl'),
             f'debug-dir={(directory / "debug").as_uri()}'], directory, 'xml2tex.log')


def compile_pdf(directory):
    shutil.copytree('/opt/scripello/font-cache/.texlive2026', directory / '.texlive2026')
    raw = (directory / 'xml2tex.tex').read_text()
    # Continuous page numbering avoids the existing frontmatter/mainmatter reset.
    (directory / 'output.tex').write_text(raw.replace('\\frontmatter', '').replace('\\mainmatter', ''))
    for iteration in range(3):
        command(['lualatex', '--utc', '--no-shell-escape', '--halt-on-error',
                 '--interaction=nonstopmode', 'output.tex'], directory, f'lualatex-{iteration + 1}.log')
    shutil.rmtree(directory / '.texlive2026')


def observe(directory):
    reader = PdfReader(directory / 'output.pdf', strict=True)
    texts = [page.extract_text() for page in reader.pages]
    (directory / 'pdf-text.json').write_text(json.dumps(texts, ensure_ascii=False, indent=2))
    root = reader.trailer['/Root']
    mark_info = root.get('/MarkInfo')
    semantics = {'document_language': root.get('/Lang'),
                 'marked': bool(mark_info and mark_info.get_object().get('/Marked')),
                 'structure_tree': '/StructTreeRoot' in root}
    (directory / 'pdf-language.json').write_text(json.dumps(semantics, indent=2))
    # Preserve actual accessibility failures. This is a report, never a PDF/UA pass claim.
    jars = list(Path('/opt/verapdf/bin').glob('cli-*.jar'))
    assert len(jars) == 1, 'Missing or ambiguous veraPDF toolchain'
    command(['java', '-Xmx768m', f'-Duser.home={directory}', f'-Djava.io.tmpdir={directory}',
             '-jar', str(jars[0]), '--flavour', 'ua1', '--format', 'xml',
             '--maxfailures', '-1', '--maxfailuresdisplayed', '-1', 'output.pdf'],
            directory, 'pdfua-report.xml', allowed=(0, 1))
    return texts, semantics


def check(directory, *, standard_toc=False):
    log = (directory / 'lualatex-3.log').read_text()
    ids = {name: int(number) for name, number in re.findall(r'LANGUAGE-ID (\w+)=(\d+)', log)}
    assert set(ids) == {'ngerman', 'english', 'french', 'greek', 'hebrew'}, ids
    # Per-page/context strings and language IDs come from actual shipped nodes.
    groups = {}
    for line in (directory / 'glyph-languages.tsv').read_text().splitlines():
        page, context, lang, char = line.split('\t')
        chars, languages = groups.setdefault((int(page), int(context)), ([], []))
        chars.append(char)
        languages.append(int(lang))
    # Glyphs in Latin scripts cannot pass due to script-based font/language fallback.
    expected = [('Internationalization', 'english'), ('Communication', 'french'),
                ('Ελληνικά', 'greek'), ('עברית', 'hebrew'),
                ('Representation', 'english'), ('Organisation', 'french'),
                ('Sprachkontrolle', 'ngerman'), ('Untertitelkontrolle', 'ngerman'),
                ('Wiederherstellung', 'ngerman'), ('Sprachumgebung', 'ngerman')]
    for word, language in expected:
        contexts = (1, 3, 5) if word in ('Internationalization', 'Ελληνικά', 'Representation',
                                        'Sprachkontrolle', 'Wiederherstellung') else (2, 4, 6)
        for context in contexts:
            matches = []
            for (page, kind), (chars, langs) in groups.items():
                if kind != context:
                    continue
                text = ''.join(chars)
                # RTL glyph order can be reversed after shaping.
                for candidate in (word, word.upper(), word[::-1], word.upper()[::-1]):
                    start = text.find(candidate)
                    if start >= 0:
                        matches.append((page, set(langs[start:start + len(candidate)])))
            assert matches, f'{word}: no shipped glyphs for context {context}'
            assert all(values == {ids[language]} for _, values in matches), (word, context, matches, ids)
    # Preserve existing inheritance: the English chapter also records its
    # language in the TOC. This port changes only own heading xml:lang.
    for word, contexts in [('Inheritance', (1, 3, 5)), ('Surroundings', (2, 4, 6))]:
        for context in contexts:
            matches = []
            for (_, kind), (chars, langs) in groups.items():
                start = ''.join(chars).casefold().find(word.casefold())
                if kind == context and start >= 0:
                    matches.append(set(langs[start:start + len(word)]))
            expected_id = ids['english']
            assert matches and all(value == {expected_id} for value in matches), (word, context, matches)
    inherited_body = []
    for (_, context), (chars, langs) in groups.items():
        start = ''.join(chars).find('Inherited')
        if context == 7 and start >= 0:
            inherited_body.append(set(langs[start:start + len('Inherited')]))
    assert inherited_body and all(value == {ids['english']} for value in inherited_body), inherited_body
    # Foreign headings must not change the surrounding German body's hyphenation.
    body_matches = 0
    for (page, context), (chars, langs) in groups.items():
        text = ''.join(chars)
        start = text.find('Umgebungskontrolle')
        if context == 7 and start >= 0:
            body_matches += 1
            assert set(langs[start:start + len('Umgebungskontrolle')]) == {ids['ngerman']}, page
    assert body_matches >= 5, body_matches
    for (_, context), (chars, _) in groups.items():
        if context in (3, 4, 5, 6):
            assert 'Anmerkung' not in ''.join(chars), 'Footnote leaked into TOC or running head'
    texts, semantics = observe(directory)
    assert len(texts) > 6, 'Fixture did not exercise actual continuation-page heads'
    # PDF text is an independent output check; language evidence is the shipped nodes above.
    for word in ('Internationalization', 'Communication', 'Representation', 'Organisation',
                 'Sprachkontrolle', 'Untertitelkontrolle'):
        assert sum(text.casefold().count(word.casefold()) for text in texts) >= 3, word
    toc = (directory / 'output.toc').read_text()
    assert 'Internationalization' in toc and 'Communication' in toc and 'Organisation' in toc
    for filename in ('output.log', 'lualatex-1.log', 'lualatex-2.log', 'lualatex-3.log'):
        assert 'Missing character:' not in (directory / filename).read_text(), filename
    return {'pages': len(texts), 'babel_language_ids': ids, 'pdf_language': semantics,
            'standard_toc': standard_toc}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--untagged', action='store_true')
    parser.add_argument('--emit-only', action='store_true')
    parser.add_argument('--standard-toc', action='store_true')
    parser.add_argument('--a11y', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    emit(output, untagged=args.untagged, standard_toc=args.standard_toc, a11y=args.a11y)
    if args.emit_only:
        return
    compile_pdf(output)
    result = check(output, standard_toc=args.standard_toc)
    result['configuration_sha256'] = hashlib.sha256(
        (ROOT / 'a9s/common/xml2tex/latex.conf.xml').read_bytes()).hexdigest()
    result['fixture_sha256'] = hashlib.sha256((output / 'book.xml').read_bytes()).hexdigest()
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
