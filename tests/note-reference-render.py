"""Render synthetic Hub with the actual CoCoTeX path; run inside the pinned image."""
import re
from pathlib import Path
from pypdf import PdfReader
from scripello import xerif

for policy in ('footnotes', 'endnotes'):
    xerif.RENDER_PARAMETERS['notes-type'] = policy
    out = Path('/work') / policy
    xerif.render(Path('/subject/tests/note-reference-hub.xml'), out, whole_book=True)
    text = '\n'.join(page.extract_text() for page in PdfReader(out / 'output.pdf').pages)
    print(policy, text, flush=True)
    for original, repeats in [('Alpha', ['AlphaRepeat']), ('Beta', ['BetaRepeat', 'BetaAgain']),
                              ('TableMark', ['TableRepeat', 'TableAgain']), ('Gamma', ['GammaRepeat'])]:
        def mark(name):
            match = re.search(re.escape(name) + r'\s*([0-9]+)', text)
            assert match, (policy, name, text)
            return match.group(1)
        actual = mark(original)
        for repeat in repeats:
            assert mark(repeat) == actual, (policy, original, repeat, text)
    for body in ('Alpha note body', 'Beta note body', 'Table note body', 'Gamma note body', 'ordinary link text', 'note details', 'mix'):
        assert body in text, (policy, body, text)
