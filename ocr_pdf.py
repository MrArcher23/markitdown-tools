#!/usr/bin/env python
"""OCR de un PDF a Markdown usando RapidOCR (offline, sin sudo, sin GPU obligatoria).

Útil para PDFs escaneados o con la capa de texto corrupta (fuente con ToUnicode roto),
donde la extracción normal falla pero el PDF se renderiza bien visualmente.

Flujo: rasteriza cada página con pypdfium2 -> OCR con RapidOCR -> reconstruye orden de
lectura por coordenadas -> une líneas en párrafos -> escribe Markdown.

Uso:
    python ocr_pdf.py ENTRADA.pdf -o SALIDA.md [--title "Título"] [--scale 2.0]
"""
import sys
import re
import argparse


def main():
    ap = argparse.ArgumentParser(description="OCR de PDF a Markdown con RapidOCR.")
    ap.add_argument("entrada", help="PDF a procesar")
    ap.add_argument("-o", "--output", required=True, help="Archivo .md de salida")
    ap.add_argument("--title", default=None, help="Título del documento (def: nombre del archivo)")
    ap.add_argument("--scale", type=float, default=2.0, help="Escala de render (mayor = más nítido y lento)")
    ap.add_argument("--start", type=int, default=0, help="Página inicial (0-based)")
    ap.add_argument("--end", type=int, default=None, help="Página final (exclusiva)")
    args = ap.parse_args()

    import pypdfium2 as pdfium
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    pdf = pdfium.PdfDocument(args.entrada)
    n = len(pdf)
    start = args.start
    end = args.end if args.end is not None else n
    end = min(end, n)

    page_texts = []
    for i in range(start, end):
        img = pdf[i].render(scale=args.scale).to_pil()
        result, _ = ocr(img)
        page_texts.append(assemble_page(result))
        if (i - start + 1) % 10 == 0 or i == end - 1:
            print(f"[ocr] página {i + 1}/{end}", file=sys.stderr, flush=True)

    body = "\n\n".join(t for t in page_texts if t.strip())
    body = postprocess(body)

    import os
    title = args.title or os.path.splitext(os.path.basename(args.entrada))[0]
    out = f"# {title}\n\n> Transcripción por OCR (RapidOCR) del PDF original.\n\n{body}\n"
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"[ok] {end - start} páginas -> {len(out.split())} palabras", file=sys.stderr)
    print(args.output)


def assemble_page(result):
    """Ordena las líneas OCR por posición y las une en párrafos según el salto vertical."""
    if not result:
        return ""
    lines = []
    for box, text, *_ in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        lines.append({"top": min(ys), "bottom": max(ys), "left": min(xs), "text": text.strip()})
    # orden de lectura: por banda vertical y luego horizontal
    lines.sort(key=lambda l: (round(l["top"] / 8), l["left"]))
    lines = [l for l in lines if l["text"] and not re.fullmatch(r"\d{1,4}", l["text"])]  # quita nº de página
    if not lines:
        return ""

    heights = [l["bottom"] - l["top"] for l in lines]
    med_h = sorted(heights)[len(heights) // 2] or 12

    paras, buf, prev_bottom = [], [], None
    for l in lines:
        if prev_bottom is not None and (l["top"] - prev_bottom) > 0.9 * med_h:
            if buf:
                paras.append(join_lines(buf))
                buf = []
        buf.append(l["text"])
        prev_bottom = l["bottom"]
    if buf:
        paras.append(join_lines(buf))
    return "\n\n".join(p for p in paras if p)


def join_lines(buf):
    """Une renglones en un párrafo, deshaciendo cortes de palabra con guion."""
    out = ""
    for ln in buf:
        if not out:
            out = ln
        elif out.endswith("-"):
            out = out[:-1] + ln  # palabra cortada con guion al final de línea
        else:
            out += " " + ln
    return out.strip()


def postprocess(text):
    text = re.sub(r"(\d)\.([A-Za-z])", r"\1. \2", text)  # "2.Even" -> "2. Even"
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


if __name__ == "__main__":
    main()
