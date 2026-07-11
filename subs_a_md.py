#!/usr/bin/env python
"""Convierte subtítulos de YouTube (json3 de yt-dlp) a Markdown en párrafos limpios.

Pensado para el flujo:
    yt-dlp --skip-download --write-auto-subs --sub-langs en --sub-format json3 -o "X.%(ext)s" URL
    python subs_a_md.py X.en.json3 -o salida.md --title "Título" --url "https://..."

Agrupa el texto en párrafos respetando los finales de oración (.!?) y las pausas del audio,
de modo que el resultado sea legible y bueno para alimentar a un LLM. No incluye marcas de tiempo.
"""
import sys
import re
import json
import argparse

GAP_MS = 2000   # pausa que sugiere fin de párrafo
MAX_WORDS = 110  # tamaño objetivo de párrafo
MIN_WORDS = 30   # no cerrar párrafos demasiado cortos por una pausa


def load_events(path):
    """Devuelve lista de (tStart, tEnd, texto) de los eventos con texto real."""
    data = json.load(open(path, encoding="utf-8"))
    out = []
    for e in data.get("events", []):
        segs = e.get("segs")
        if not segs:
            continue
        txt = "".join(s.get("utf8", "") for s in segs)
        if not txt or txt.isspace():
            continue
        start = e.get("tStartMs", 0)
        end = start + (e.get("dDurationMs", 0) or 0)
        out.append((start, end, txt))
    return out


def clean(text):
    text = text.replace("\n", " ")
    # quita anotaciones de sonido de los subtítulos: [music], [Applause], [Laughter]...
    text = re.sub(r"\[\s*[^\]]{0,25}\s*\]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)  # sin espacio antes de puntuación
    return text.strip()


def build_paragraphs(events, gap_ms=GAP_MS, max_words=MAX_WORDS, min_words=MIN_WORDS):
    paras = []
    buf = []           # piezas de texto del párrafo en curso
    words = 0
    last_end = None
    for start, end, txt in events:
        txt = txt.strip()
        if not txt:
            continue
        # ¿pausa larga? cierra el párrafo si ya tiene cuerpo suficiente
        if last_end is not None and (start - last_end) > gap_ms and words >= min_words:
            paras.append(clean(" ".join(buf)))
            buf, words = [], 0
        buf.append(txt)
        words += len(txt.split())
        last_end = end
        # párrafo lo bastante largo y terminado en oración -> ciérralo
        if words >= max_words and re.search(r"[.!?][\"')\]]?$", txt):
            paras.append(clean(" ".join(buf)))
            buf, words = [], 0
    if buf:
        paras.append(clean(" ".join(buf)))
    return [p for p in paras if p]


def main():
    ap = argparse.ArgumentParser(description="Subtítulos json3 de YouTube -> Markdown en párrafos.")
    ap.add_argument("entrada", help="Archivo .json3 de subtítulos (de yt-dlp)")
    ap.add_argument("-o", "--output", required=True, help="Archivo .md de salida")
    ap.add_argument("--title", default="Transcripción", help="Título del documento")
    ap.add_argument("--url", default="", help="URL de origen (para la nota de fuente)")
    ap.add_argument("--gap", type=int, default=GAP_MS, help="Pausa en ms para cortar párrafo")
    ap.add_argument("--max-words", type=int, default=MAX_WORDS, help="Palabras objetivo por párrafo")
    args = ap.parse_args()

    events = load_events(args.entrada)
    paras = build_paragraphs(events, gap_ms=args.gap, max_words=args.max_words)

    lines = [f"# {args.title}", ""]
    if args.url:
        lines.append(f"> Fuente: {args.url}")
    lines.append("> Transcripción generada a partir de los subtítulos automáticos de YouTube.")
    lines.append("")
    lines.extend(p + "\n" for p in paras)
    text = "\n".join(lines).rstrip() + "\n"

    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(text)

    total_words = sum(len(p.split()) for p in paras)
    print(f"[ok] {len(events)} eventos -> {len(paras)} párrafos, {total_words} palabras", file=sys.stderr)
    print(args.output)


if __name__ == "__main__":
    main()
