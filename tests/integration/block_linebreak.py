"""Exercise the installed real xml2tex and LuaLaTeX path (local toolchain only).

Run in a Scripello check image with the CURRENT xerif source mounted at
/opt/transpect/a9s/common. See README.md beside this file. No source assertions,
mocked transforms, or expected-failure mode: the uncorrected figure case fails.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

import pymupdf
from scripello import xerif


def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 16, 16, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\x00' + b'\x18\x70\xc0' * 16) * 16))
            + chunk(b'IEND', b''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--cases', nargs='+', default=['inline', 'figure', 'masked', 'body'])
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    assets = args.output / 'assets'
    assets.mkdir()
    (assets / 'square.png').write_bytes(png())
    image = ('<mediaobject><imageobject><imagedata fileref="assets/square.png" '
             'css:width="16pt" css:height="16pt"/></imageobject></mediaobject>')
    cases = {
        'inline': '<para>InlineAlpha<br/>InlineBeta</para>',
        'figure': '<para>' + image + '<br/></para>',
        # Text after the block resumes horizontal mode: this masks the old failure.
        'masked': '<para>' + image + 'MaskAlpha<br/>MaskBeta</para>',
        'body': '<para>Ordinary body text remains complete.</para>',
    }
    results = {}
    for name in args.cases:
        inputs = args.output / (name + '-inputs')
        inputs.mkdir()
        source = inputs / 'input.xml'
        source.write_text('<hub xmlns="http://docbook.org/ns/docbook" '
                          'xmlns:css="http://www.w3.org/1996/css" version="5.0" xml:lang="en">'
                          '<chapter xml:lang="en"><info><title>Break regression</title></info>'
                          '<para>BodyBefore</para>' + cases[name]
                          + '<para>BodyAfter</para></chapter></hub>')
        output = args.output / name
        record = {'fixture_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        results[name] = record
        try:
            xerif.render(source, output, whole_book=False)
            with pymupdf.open(output / 'output.pdf') as pdf:
                text = '\n'.join(page.get_text() for page in pdf)
                for token in ('BodyBefore', 'BodyAfter'):
                    assert text.count(token) == 1, (name, token, text)
                if name in ('inline', 'masked'):
                    prefix = 'Inline' if name == 'inline' else 'Mask'
                    positions = []
                    for token in (prefix + 'Alpha', prefix + 'Beta'):
                        hits = [(i, rect.y0) for i, page in enumerate(pdf) for rect in page.search_for(token)]
                        assert len(hits) == 1, (token, hits)
                        positions.append(hits[0])
                    assert positions[1][0] > positions[0][0] or (
                        positions[1][0] == positions[0][0] and positions[1][1] > positions[0][1] + 5
                    ), positions
                    record['line_positions'] = positions
                if name in ('figure', 'masked'):
                    images = [rect for page in pdf for entry in page.get_images()
                              for rect in page.get_image_rects(entry[0])]
                    assert images and all(rect.width > 0 and rect.height > 0 for rect in images)
                    record['image_count'] = len(images)
                if name == 'body':
                    assert text.count('Ordinary body text remains complete.') == 1, text
                record['text'] = text
                record['pages'] = len(pdf)
                record['words'] = [page.get_text('words') for page in pdf]
            record['passed'] = True
        except Exception as error:
            record['passed'] = False
            record['error'] = str(error)
        finally:
            (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name, 'PASS' if record['passed'] else 'FAIL', flush=True)
    assert all(r['passed'] for r in results.values()), results


if __name__ == '__main__':
    main()
