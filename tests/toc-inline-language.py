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
    return section.split(end, 1)[0].replace("↩", "")


def require_fragments(output: str, expected: tuple[str, ...]) -> None:
    for fragment in expected:
        assert fragment in output, f"Missing TeX fragment {fragment!r}"


def check_tex(tex: str, route: str) -> None:
    title = entry(tex, "tpTocTitle", "TitleStart", "TitleEnd")
    require_fragments(title, (
        r"\foreignlanguage{ngerman}{Titelwort}",
        r"\href{https://example.org/@team/profil}{https://example.org/@team/profil}",
        r"\href{mailto:team@example.org}{mailto:team@example.org}",
        r"\href{https://example.org/@team/contact}{\foreignlanguage{ngerman}{\textit{Kontakt}}}",
        rf"\url{{{LONG_URI}}}",
        r"\foreignlanguage{ngerman}{{\textbf{Verweis}}}",
        r"\textsuperscript{\textit{ASameTop B}}",
        r"\textsubscript{\textbf{A\foreignlanguage{ngerman}{Tief}B}}",
    ))
    require_fragments(tex, (r"Note\hypertarget{ref-02}{}", r"\hyperlink{ref-02}{7}"))
    if route == "customer":
        subtitle = entry(tex, "tpTocSubtitle", "SubtitleStart", "SubtitleEnd")
        require_fragments(subtitle, (
            r"\foreignlanguage{ngerman}{Untertitelwort}",
            r"\href{https://example.org/@team/info}{https://example.org/@team/info}",
            r"\href{mailto:info@example.org}{info@example.org}",
            r"\href{mailto:info@example.org}{\foreignlanguage{ngerman}{\textbf{Anfrage}}}",
            r"\textsubscript{\textit{ASameBottom B}}",
            r"\textsuperscript{\textit{\textbf{A\foreignlanguage{ngerman}{Hoch}B}}}",
        ))
    else:
        assert r"\tpTocSubtitle{\protect\foreignlanguage{english}{SubtitleStart" not in tex


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("route", choices=("standard", "customer"))
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
    render(source, rendered, whole_book=True, style=style)
    check_tex((rendered / "xml2tex.tex").read_text(), route)
    mapping = Path("/opt/transpect/a9s/common/xml2tex/latex.conf.xml")
    print(f"{route} TOC passed with mapping {hashlib.sha256(mapping.read_bytes()).hexdigest()}")
    print(f"Fixture {hashlib.sha256(source.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
