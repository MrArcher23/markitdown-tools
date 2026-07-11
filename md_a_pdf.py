#!/usr/bin/env python3
"""Convierte un archivo Markdown a PDF (md -> HTML -> PDF con WeasyPrint).

El sentido inverso de este proyecto (que normalmente pasa PDF -> Markdown).

Uso:
    python md_a_pdf.py ENTRADA.md [SALIDA.pdf]

Si no se indica SALIDA, se genera junto a la entrada con extensión .pdf.

Dependencias (en el .venv):
    uv pip install markdown weasyprint
"""
import sys
from pathlib import Path

import markdown
from weasyprint import HTML

CSS = """
@page {
    size: A4;
    margin: 2cm 2.2cm 2.2cm 2.2cm;
    @bottom-center { content: counter(page); color: #9aa0a6; font-size: 9pt; }
}
body {
    font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #232629;
}
h1 { font-size: 23pt; color: #0b5c4f; margin: 0 0 .15em; line-height: 1.15; }
h2 { font-size: 14pt; color: #0b5c4f; margin: 1.35em 0 .45em;
     border-bottom: 1px solid #e4e7e6; padding-bottom: .18em; }
h3 { font-size: 12pt; color: #0b5c4f; margin: 1em 0 .3em; }
p  { margin: .5em 0; }
strong { color: #0b3b34; }
em { color: #33383b; }
ul, ol { margin: .45em 0 .45em 1.1em; padding-left: .6em; }
li { margin: .28em 0; }
blockquote {
    margin: .85em 0; padding: .55em .95em;
    background: #f3f8f7; border-left: 3px solid #0b5c4f;
    color: #454b4d;
}
blockquote p { margin: .2em 0; }
hr { border: none; border-top: 1px solid #e0e3e2; margin: 1.25em 0; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: .7em 0; }
th, td { border: 1px solid #dfe3e2; padding: .38em .55em; text-align: left; vertical-align: top; }
th { background: #0b5c4f; color: #fff; }
tr:nth-child(even) td { background: #f7faf9; }
code { font-family: "DejaVu Sans Mono", monospace; background: #eef1f0;
       padding: .05em .3em; border-radius: 3px; font-size: .88em; }
a { color: #0b5c4f; }
"""


def convertir(entrada: Path, salida: Path) -> None:
    texto = entrada.read_text(encoding="utf-8")
    cuerpo = markdown.markdown(
        texto,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )
    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        f"<title>{entrada.stem}</title><style>{CSS}</style></head>"
        f"<body>{cuerpo}</body></html>"
    )
    HTML(string=html, base_url=str(entrada.parent)).write_pdf(str(salida))
    print(f"PDF generado: {salida}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    entrada = Path(sys.argv[1]).expanduser().resolve()
    if not entrada.exists():
        print(f"No existe la entrada: {entrada}")
        return 1
    salida = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) > 2
        else entrada.with_suffix(".pdf")
    )
    salida.parent.mkdir(parents=True, exist_ok=True)
    convertir(entrada, salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
