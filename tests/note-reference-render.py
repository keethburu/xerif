"""Exercise real Hub -> TeX -> PDF output, with the rendered note as oracle.

The fixture is original CC0 text. Repeats must agree with the original mark;
explicit hyperlink contents must survive, even if they look like note numbers.
"""
import re
from pathlib import Path
from pypdf import PdfReader
from scripello import xerif
from scripello.styles import compile_style, dgb_style

running_style = compile_style(dgb_style(), 'small')

failures = []
for policy, per_chapter, second_start, style in (('footnotes', 'no', 1, None),
                                                 ('endnotes', 'no', 5, None),
                                                 ('endnotes', 'yes', 1, None),
                                                 ('footnotes', 'yes', 1, running_style)):
    xerif.RENDER_PARAMETERS['notes-type'] = policy
    xerif.RENDER_PARAMETERS['notes-per-chapter'] = per_chapter
    case = policy + '-per-chapter-' + per_chapter
    out = Path('/work') / case
    xerif.render(Path('/subject/tests/note-reference-hub.xml'), out, whole_book=True, style=style)
    pages = [page.extract_text() for page in PdfReader(out / 'output.pdf').pages]
    text = '\n'.join(pages)
    compact_text = re.sub(r'\s+', '', text)
    print(case, text, flush=True)
    def check(condition, detail):
        if not condition:
            failures.append((case, detail))
    def mark(name):
        match = re.search(re.escape(name) + r'([0-9]+)', compact_text)
        check(match is not None, ('missing marker', name))
        return match.group(1) if match else None
    for original, repeats in [('Alpha', ['AlphaRepeat']),
                              ('Beta', ['BetaRepeat', 'BetaAgain', 'BetaPhrase', 'BetaEmpty', 'CrossChapter']),
                              ('TableMark', ['TableRepeat', 'TableAgain']),
                              ('TitleMark', ['TitleRepeat']),
                              ('QuoteMark', ['QuoteRepeat']),
                              ('QuoteTableMark', ['QuoteTableRepeat']),
                              ('Gamma', ['GammaRepeat']), ('Delta', ['DeltaRepeat'])]:
        actual = mark(original)
        for repeat in repeats:
            check(mark(repeat) == actual, ('reference mismatch', original, repeat, actual))
    # Independent numbering-policy controls: a fix must not renumber originals
    # merely to agree with stale reference text. Both existing policies use the
    # same first-chapter sequence. Default endnotes continue across chapters;
    # default footnotes restart. This is observed in the preserved baseline.
    for name, expected in [('Alpha', '1'), ('Extra', '2'), ('Beta', '3'),
                           ('TableMark', '4'), ('Gamma', str(second_start)),
                           ('Delta', str(second_start + 1))]:
        check(mark(name) == expected, ('original policy changed', name, expected))
    for body in ('Alpha note body', 'Extra note body', 'Beta note body',
                 'Table note body', 'Gamma note body', 'Delta note body',
                 'Title quotation body', 'Quotation note body', 'Table quotation body'):
        check(compact_text.count(re.sub(r'\s+', '', body)) == 1, ('note body lost or duplicated', body))
    readable = re.sub(r'-\s*\n\s*', '', text)
    compact = re.sub(r'\s+', '', readable)
    for literal in ('PlainNumber[42]', 'PlainRoman[ix]', 'SupText[notedetails]',
                    'PlainSup[ix]', 'SimilarRole[42]', 'MixedText[seeix]',
                    'MixedLinkFoot[seeix]', 'MixedLinkEnd[seeix]'):
        check(literal in compact, ('explicit link text changed', literal))
    for literal in ('ordinary link text', 'note details', 'mix'):
        check(literal in readable, ('ordinary link text lost', literal))
    for literal in ('Ελληνικά', 'Кириллица', 'Representative float',
                    'Float content sentinel', 'Coverage chapter'):
        check(literal in readable, ('manuscript content lost', literal))
    row_pages = set()
    for number in range(1, 121):
        token = f'ContinuationRow{number:03d}'
        matches = [i for i, page in enumerate(pages) if token in page]
        check(len(matches) == 1, ('continuation row lost or duplicated', token))
        row_pages.update(matches)
    check(len(row_pages) >= 3, 'table did not span multiple pages')
    if style is not None:
        for i in sorted(row_pages)[1:]:
            expected_head = 'Coverage running head' if (i + 1) % 2 else 'chapter 3'
            check(expected_head in pages[i], ('incorrect running head', i + 1, expected_head))
    check('??' not in text, 'unresolved reference in PDF')
    log = (out / 'xml2tex.log').read_text()
    for diagnostic in out.rglob('*.log'):
        check('Missing character:' not in diagnostic.read_text(errors='replace'),
              ('missing glyph diagnostic', str(diagnostic)))
    check('XERIF_NOTE_REFERENCE_AMBIGUOUS' in log, 'missing ambiguity diagnostic')
print('FAILURES:', failures, flush=True)
assert not failures, failures
