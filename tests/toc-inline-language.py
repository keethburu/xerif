"""Exercise both TOCs through the pinned Scripello renderer."""

import argparse
import hashlib
from pathlib import Path
from shutil import copyfile

from scripello.styles.compiler import CompiledStyle
from scripello.xerif import render


PACKAGE = r"""
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{scripello-style}
\DeclareOption{layout=c}{}
\ProcessOptions\relax
\RequirePackage{scripello-default}
\RequirePackage{etoolbox}
\robustify\hyperlink
"""
LONG_URI = "https://example.org/~abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmn/abschnitt"
BASE_MAPPING_SHA256 = "93b768899c6aaaef6436e4d422866e98040792ec4317559a215d7d34cda2575b"


class StandardTocStyle(CompiledStyle):
    def write(self, directory: Path) -> None:
        super().write(directory)
        layout = directory / "style-layout.xml"
        override = '<xsl:variable name="create-customer-toctitles" select="false()"/>'
        layout.write_text(layout.read_text().replace("</set>", override + "\n</set>"))


def entry(tex: str, macro: str, start: str, end: str) -> str:
    prefix = rf"\{macro}{{\protect\foreignlanguage{{english}}{{{start}"
    assert tex.count(prefix) == 1, prefix
    section = tex.split(prefix, 1)[1]
    assert end in section, end
    return section.split(end, 1)[0]


def require_fragments(output: str, expected: tuple[str, ...]) -> None:
    for fragment in expected:
        assert fragment in output, f"Missing TeX fragment {fragment!r}"


def compare_native_links(output: str, compatibility: str, targets: tuple[str, ...]) -> None:
    for target in targets:
        original = [line for line in compatibility.splitlines() if target in line]
        actual = [line for line in output.splitlines() if target in line]
        assert len(original) == 1, f"Missing or ambiguous compatibility link {target!r}"
        assert actual == original, f"Native TeX changed for {target}: {actual!r} != {original!r}"


def check_tex(tex: str, compatibility: str, route: str) -> None:
    title = entry(tex, "tpTocTitle", "TitleStart", "TitleEnd")
    compare_native_links(title, entry(compatibility, "tpTocTitle", "TitleStart", "TitleEnd"), (
        r"\href{https://example.org/@team/profil}",
        r"\href{mailto:team@example.org}",
        r"\href{https://example.org/@query?",
        r"\href{https://example.org/@profile/",
        r"\href{https://example.org/\%D0",
        rf"\url{{{LONG_URI}}}",
    ))
    require_fragments(title, (
        r"\foreignlanguage{ngerman}{Titelwort}",
        r"\href{https://example.org/@team/contact}{\foreignlanguage{ngerman}{\textit{Kontakt}}}",
        r"\foreignlanguage{ngerman}{Profil",
        r"\foreignlanguage{ngerman}{{\textbf{Verweis}}}",
        r"\textsuperscript{\textit{ASameTop B}}",
        r"\textsubscript{\textbf{A\foreignlanguage{ngerman}{Tief} B}}",
    ))
    require_fragments(tex, (r"Note\hypertarget{ref-02}{}", r"\hyperlink{ref-02}{7}"))
    if route == "customer":
        subtitle = entry(tex, "tpTocSubtitle", "SubtitleStart", "SubtitleEnd")
        compare_native_links(subtitle, entry(compatibility, "tpTocSubtitle", "SubtitleStart", "SubtitleEnd"), (
            r"\href{https://example.org/@team/info}",
            r"\href{mailto:info@example.org}{info@",
            r"\href{https://example.org/@subtitle?",
            r"\href{https://example.org/@selection/",
            r"\href{https://example.org/\%D0",
        ))
        require_fragments(subtitle, (
            r"\foreignlanguage{ngerman}{Untertitelwort}",
            r"\href{mailto:info@example.org}{\foreignlanguage{ngerman}{\textbf{Anfrage}}}",
            r"\foreignlanguage{ngerman}{Auswahl",
            r"\textsubscript{\textit{ASameBottom B}}",
            r"\textsuperscript{\textit{\textbf{A\foreignlanguage{ngerman}{Hoch} B}}}",
        ))
    else:
        assert r"\tpTocSubtitle" not in tex


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("route", choices=("standard", "customer"))
    reference = parser.add_mutually_exclusive_group(required=True)
    reference.add_argument("--compatibility-base", action="store_true")
    reference.add_argument("--compatibility-tex", type=Path)
    args = parser.parse_args()
    output: Path = args.output
    route: str = args.route
    inputs = output / "inputs"
    inputs.mkdir(parents=True)
    source = inputs / "book.xml"
    copyfile(Path(__file__).with_suffix(".xml"), source)
    style_type = StandardTocStyle if route == "standard" else CompiledStyle
    style = style_type(
        package=PACKAGE,
        parameters={"running-header": "yes"},
        manifest={
            "identity": "toc-inline-language",
            "template_id": "toc-inline-language",
            "variant": route,
            "effective": {"body": {"role": "body"}},
        },
        fonts={},
        compile_ms=0,
    )
    rendered = output / "render"
    mapping = Path("/opt/transpect/a9s/common/xml2tex/latex.conf.xml")
    mapping_hash = hashlib.sha256(mapping.read_bytes()).hexdigest()
    if args.compatibility_base:
        assert mapping_hash == BASE_MAPPING_SHA256, "Use the pinned image without a mapping overlay for the base"
    render(source, rendered, whole_book=True, style=style)
    compatibility_tex: Path | None = args.compatibility_tex
    if compatibility_tex is not None:
        check_tex((rendered / "xml2tex.tex").read_text(), compatibility_tex.read_text(), route)
        print(f"{route} TOC passed with mapping {mapping_hash}")
    else:
        print(f"{route} compatibility base rendered with mapping {mapping_hash}")
    print(f"Fixture {hashlib.sha256(source.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
