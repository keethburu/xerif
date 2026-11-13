"""Validate the complete mapping against Scripello's installed XML2TeX grammar.

The external grammar is the oracle: a valid XSLT instruction can still be
unsupported configuration content. The landed heading backport is an optional
negative control and must fail at its explicit document constructor.
"""

import argparse
import hashlib
from pathlib import Path

from lxml import etree as E


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SHA256 = "7c0832c800373fcdaac8df87b41ce2adbe4b5156c5d57500a8a1d5e1064a5181"
XSLT_SCHEMA_SHA256 = "0afc65c7279525740072bc3b829f0bf5cc331ec3584d2e1a6fa08b4218d6f89e"
LANDED_SHA256 = "eeee850453b3539e433725c3c14a18e60e652430a3c586e032a4d906949c2229"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "xml2tex/latex.conf.xml")
    parser.add_argument("--landed-config", type=Path)
    args = parser.parse_args()
    for path, checksum in (
        (args.schema, SCHEMA_SHA256),
        (args.schema.with_name("xslt2.rng"), XSLT_SCHEMA_SHA256),
    ):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum, path
    schema = E.RelaxNG(file=str(args.schema))
    schema.assertValid(E.parse(str(args.config)))
    print("PASS complete mapping accepted by installed XML2TeX schema")
    if args.landed_config is not None:
        assert hashlib.sha256(args.landed_config.read_bytes()).hexdigest() == LANDED_SHA256
        assert not schema.validate(E.parse(str(args.landed_config))), "Landed backport unexpectedly accepted"
        # Check the validator's error contract, not the implementation's text.
        assert any(
            error.type_name == "RELAXNG_ERR_EXTRACONTENT"
            and error.message == "Element variable has extra content: document"
            for error in schema.error_log
        ), str(schema.error_log)
        print("PASS landed backport rejected at unsupported document constructor")


if __name__ == "__main__":
    main()
