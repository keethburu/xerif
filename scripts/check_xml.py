#!/usr/bin/env python3
"""Check tracked XML sources for well-formedness without fetching dependencies."""

import argparse
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
XML_SUFFIXES = {".xml", ".xsl", ".xpl", ".xhtml", ".xmp", ".xsd", ".rng", ".sch"}


def tracked_xml():
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True, stdout=subprocess.PIPE, timeout=10,
    )
    return [ROOT / path for path in result.stdout.decode("utf-8").split("\0")
            if Path(path).suffix.lower() in XML_SUFFIXES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path,
                        help="explicit files to check; defaults to tracked XML sources")
    args = parser.parse_args()
    paths = args.paths or tracked_xml()
    if not paths:
        parser.error("no XML sources found")
    failed = False
    for path in paths:
        try:
            ET.parse(path)
        except (ET.ParseError, OSError) as error:
            print(f"{path}: {error}", file=sys.stderr)
            failed = True
    print(f"Checked {len(paths)} XML files")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
