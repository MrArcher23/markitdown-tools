#!/usr/bin/env python
"""
Convierte un archivo (PDF u otro formato soportado) a Markdown con MarkItDown.

Algunos PDFs (típicamente los que recodifican fuentes, p.ej. OceanofPDF) no mapean
las ligaduras tipográficas fi/fl/ff/ffi/ffl en su tabla ToUnicode, y los extractores
de texto las sustituyen por un carácter marcador (U+0000, U+FFFE o U+FFFD). El
resultado son palabras rotas como "di⟦⟧erent" (different) o "con⟦⟧ict" (conflict).

Este script detecta ese defecto y SOLO entonces reconstruye cada palabra, eligiendo
—por frecuencia real de palabra (wordfreq) y respaldado por /usr/share/dict/words—
la ligadura que produce la palabra correcta. Si no detecta marcadores, no toca nada.

Uso:
    python convertir_pdf.py ENTRADA.pdf [-o SALIDA.md] [--no-fix]
"""
import sys
import re
import argparse
from itertools import product

# Caracteres con que los extractores marcan una ligadura no mapeada
MARKERS = "\x00￾�"
# Ligaduras tipográficas estándar que empiezan con "f" (orden = preferencia ante empates)
LIGATURES = ["fi", "fl", "ff", "ffi", "ffl"]
LIG_PENALTY = {"fi": 0.0, "fl": 0.001, "ff": 0.002, "ffi": 0.003, "ffl": 0.004}

WORD_RE = re.compile(r"[A-Za-z’'" + MARKERS + r"]*[" + MARKERS + r"][A-Za-z’'" + MARKERS + r"]*")


STOPWORDS = {
    "en": {"the", "of", "and", "to", "in", "that", "is", "for", "it", "with", "as", "was", "his"},
    "es": {"de", "la", "que", "el", "en", "y", "los", "del", "se", "las", "por", "un", "para", "con", "una", "su"},
}


def detect_lang(text):
    """Detecta en/es contando stopwords (ignora marcadores de ligadura)."""
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    if not words:
        return "en"
    sample = words[:5000]
    scores = {lang: sum(w in sw for w in sample) for lang, sw in STOPWORDS.items()}
    return max(scores, key=scores.get)


def _load_repairer(lang="en"):
    """Devuelve (fix_text, stats) o lanza si faltan dependencias."""
    from wordfreq import zipf_frequency

    DICT = set()
    dict_paths = ["/usr/share/dict/words"]
    if lang == "es":
        dict_paths = ["/usr/share/dict/spanish", "/usr/share/dict/es", "/usr/share/dict/words"]
    for path in dict_paths:
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                DICT = {w.strip().lower() for w in fh if w.strip()}
            break
        except OSError:
            continue

    stats = {"markers": 0, "tokens": 0, "resolved": 0, "unresolved": []}

    def lookup_core(s):
        s = s.lower().replace("’", "'")
        if s.endswith("'s"):
            s = s[:-2]
        return s.replace("'", "")

    def longest_known_sub(key):
        """Longitud de la subcadena más larga (>=4) que es palabra del diccionario.
        Sirve para desempatar palabras compuestas/raras (p.ej. 'conflictless'
        contiene 'conflict' -> prefiere 'fl' sobre 'fi')."""
        n = len(key)
        best = 0
        for i in range(n):
            for j in range(i + 4, n + 1):
                if (j - i) > best and key[i:j] in DICT:
                    best = j - i
        return best

    def score(combo, core_chars, positions):
        """Devuelve (puntuación, es_confiable, candidato)."""
        chars = list(core_chars)
        for pos, lig in zip(positions, combo):
            chars[pos] = lig
        cand = "".join(chars)
        key = lookup_core(cand)
        z = zipf_frequency(key, lang)
        if z > 0.0:
            base, confident = z, True
        elif key in DICT:
            base, confident = 1.0, True  # palabra válida aunque poco frecuente
        else:
            base, confident = 0.01 * longest_known_sub(key), False
        base -= sum(LIG_PENALTY.get(l, 0.01) for l in combo)
        return base, confident, cand

    def is_sentence_start(text, idx):
        j = idx - 1
        while j >= 0 and text[j] in " \t":
            j -= 1
        return j < 0 or text[j] in ".!?:;\n\r“”\"'(«—"

    def rebuild(token, best_combo, positions, at_sentence_start):
        letters = [c for c in token if c.isalpha()]
        all_upper = bool(letters) and all(c.isupper() for c in letters) and len(letters) > 1
        out = []
        pos_iter = iter(zip(positions, best_combo))
        next_pos = next(pos_iter, (None, None))
        for i, c in enumerate(token):
            if next_pos[0] == i:
                lig = next_pos[1]
                if all_upper:
                    lig = lig.upper()
                elif i == 0 and at_sentence_start:
                    lig = lig[0].upper() + lig[1:]
                out.append(lig)
                next_pos = next(pos_iter, (None, None))
            else:
                out.append(c)
        return "".join(out)

    def replace(m):
        token = m.group()
        stats["tokens"] += 1
        stats["markers"] += sum(token.count(ch) for ch in MARKERS)
        positions = [i for i, c in enumerate(token) if c in MARKERS]
        best_score, best_conf, best_combo = -99.0, False, None
        for combo in product(LIGATURES, repeat=len(positions)):
            s, conf, _cand = score(combo, token, positions)
            if s > best_score:
                best_score, best_conf, best_combo = s, conf, combo
        if best_conf:
            stats["resolved"] += 1
        else:
            # mejor conjetura aplicada (informada por subpalabra), pero sin confirmar
            stats["unresolved"].append(token.replace("\x00", "?").replace("￾", "?").replace("�", "?"))
        return rebuild(token, best_combo, positions, is_sentence_start(m.string, m.start()))

    def fix_text(text):
        return WORD_RE.sub(replace, text)

    return fix_text, stats


def main():
    ap = argparse.ArgumentParser(description="Convierte a Markdown y repara ligaduras de PDF.")
    ap.add_argument("entrada", help="Archivo a convertir (pdf, docx, pptx, xlsx, html, ...)")
    ap.add_argument("-o", "--output", help="Archivo .md de salida (por defecto: junto al original)")
    ap.add_argument("--no-fix", action="store_true", help="No reparar ligaduras (salida cruda)")
    ap.add_argument("--lang", default="auto", help="Idioma para reparar (en, es, auto). Por defecto autodetecta.")
    args = ap.parse_args()

    from markitdown import MarkItDown

    md = MarkItDown(enable_plugins=False)
    text = md.convert(args.entrada).text_content

    has_markers = any(ch in text for ch in MARKERS)
    if has_markers and not args.no_fix:
        lang = detect_lang(text) if args.lang == "auto" else args.lang
        print(f"[idioma] {lang}", file=sys.stderr)
        fix_text, stats = _load_repairer(lang)
        text = fix_text(text)
        print(
            f"[ligaduras] {stats['markers']} marcadores en {stats['tokens']} palabras "
            f"-> {stats['resolved']} reconstruidas con palabra real, "
            f"{len(stats['unresolved'])} sin confirmar.",
            file=sys.stderr,
        )
        if stats["unresolved"]:
            muestra = ", ".join(sorted(set(stats["unresolved"]))[:15])
            print(f"[ligaduras] sin confirmar (revisar): {muestra}", file=sys.stderr)
    elif has_markers:
        print("[aviso] se detectaron marcadores de ligadura pero --no-fix está activo.", file=sys.stderr)

    # Defecto 2: algunos PDFs salen con tabuladores como separadores de palabra.
    # Solo se normaliza si el patrón es masivo (tabs en medio de muchas líneas).
    lines = text.split("\n")
    inline_tab_lines = sum(1 for ln in lines if "\t" in ln.strip())
    if not args.no_fix and inline_tab_lines >= 10:
        n_tabs = text.count("\t")
        text = "\n".join(re.sub(r"[ \t]+", " ", ln).rstrip() for ln in lines)
        print(
            f"[espacios] {n_tabs} tabuladores (en {inline_tab_lines} líneas) "
            f"normalizados a espacios.",
            file=sys.stderr,
        )

    if args.output:
        out_path = args.output
    else:
        import os
        base, _ = os.path.splitext(args.entrada)
        out_path = base + ".md"

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(out_path)


if __name__ == "__main__":
    main()
