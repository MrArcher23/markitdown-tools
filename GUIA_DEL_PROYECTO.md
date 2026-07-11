# Guía del proyecto — Convertir documentos, audio y subtítulos a Markdown (local)

> **Si eres un agente (Claude Code) leyendo esto:** tu tarea es dejar este set de herramientas
> funcionando en la máquina del usuario. Haz lo siguiente en orden:
> 1. Lee la **sección 3 (Requisitos)** y confirma que se cumplen (pregunta al usuario si falta algo, p. ej. si tiene GPU NVIDIA). **Si el usuario está en Windows, ve primero la sección 3.1 (WSL2).**
> 2. Ejecuta la **sección 4 (Instalación)** paso a paso. Instala solo lo que el usuario vaya a usar (el bloque de PDF es el mínimo; audio, OCR y MD→PDF son opcionales).
> 3. Crea cada archivo de la **sección 5 (Los scripts)** con el nombre exacto indicado, dentro de la carpeta del proyecto.
> 4. Valida con la **sección 7 (Verificación rápida)**.
>
> Todo es **100% local** (sin API, sin nube, sin enviar archivos a ningún servicio). No necesita permisos de root para lo esencial.

---

## 1. ¿Qué es esto?

Un conjunto de scripts sobre **[MarkItDown](https://github.com/microsoft/markitdown)** (Microsoft) para convertir documentos a **Markdown limpio**, pensado para leer con LLMs o archivar como texto. Cubre tres entradas principales — **documentos** (PDF y también docx/pptx/xlsx/html), **audio** y **subtítulos** — más utilidades de **OCR** y el sentido inverso **Markdown → PDF**.

La idea de fondo: MarkItDown ya convierte muchos formatos, pero (a) los PDFs de ciertas fuentes salen con defectos tipográficos, (b) no hace OCR, y (c) no transcribe audio con buena calidad. Estos scripts rellenan esos huecos y dejan una salida Markdown legible.

---

## 2. Alcance y casos de uso

| Caso de uso | Script | Cuándo usarlo | Salida |
|---|---|---|---|
| **Documentos → Markdown** (con reparador) | `convertir_pdf.py` | PDF con texto real (libros, normas, informes) y también **docx/pptx/xlsx/html** (vía MarkItDown). En PDF repara ligaduras rotas y tabuladores. | `.md` junto al original |
| **PDF → Markdown en lote** | `batch_convert.py` | Una carpeta entera de PDFs; convierte solo los que aún no tienen `.md`. | Un `.md` por PDF |
| **OCR de PDF → Markdown** | `ocr_pdf.py` | PDFs **escaneados** (solo imágenes) o con capa de texto corrupta, donde la extracción normal falla. | `.md` (texto reconocido) |
| **Audio → Markdown** | `transcribir_audio.py` | Notas de voz, reuniones, audiolibros (mp3/m4a/wav/mp4…). Transcribe con faster-whisper. | `.md` en párrafos |
| **Subtítulos → Markdown** | `subs_a_md.py` | Subtítulos automáticos de YouTube (json3 de yt-dlp) a texto en párrafos. | `.md` en párrafos |
| **Markdown → PDF** | `md_a_pdf.py` | El sentido inverso: dejar un `.md` como PDF con estilo. | `.pdf` |

**Regla práctica:** para PDFs primero prueba `convertir_pdf.py`; si el `.md` sale **vacío** o con texto claramente corrupto, pásalo por `ocr_pdf.py`.

---

## 3. Requisitos

- **Sistema:** Linux (probado). macOS y WSL2 deberían funcionar con ajustes menores.
- **Python:** no hace falta tenerlo preinstalado de forma especial; se usa **`uv`** para crear un entorno con Python 3.12 (paso 4.1).
- **Disco:** ~2–3 GB para el entorno base; +1–2 GB si usas audio (modelos de Whisper) u OCR.
- **GPU (opcional):** una GPU **NVIDIA con CUDA** acelera mucho la transcripción de audio (≈30× tiempo real). **No es obligatoria**: sin GPU, el audio corre en CPU (más lento). El resto (PDF, OCR, MD→PDF) no usa GPU.

> **Nota sobre `ffmpeg`:** NO se necesita `ffmpeg` del sistema. El audio se decodifica con **PyAV**, que trae sus propios códecs.

### 3.1 ¿Estás en Windows? Instala y usa WSL2 (tutorial)

En Windows, la forma **recomendada y más simple** es correr todo dentro de **WSL2** (el Linux integrado de Windows). Así **toda esta guía funciona tal cual**, sin cambiar ningún comando, e incluso con **GPU** (WSL2 tiene passthrough de CUDA de NVIDIA). Claude Code también corre dentro de WSL2 sin problema.

**Requisitos:** Windows 10 (versión 2004 o superior) o Windows 11. Con menos que eso, actualiza Windows primero (Configuración → Windows Update).

#### ¿Ya tienes WSL2?
Abre PowerShell y ejecuta `wsl -l -v`. Si lista una distro (p. ej. `Ubuntu`) con **VERSION 2**, ya lo tienes → salta al punto **C**. Si el comando no existe o no hay distros, sigue desde **A**.

#### A) Instalar WSL2 (una sola vez)
1. Abre **PowerShell como administrador**: clic derecho en el botón de Inicio → **"Terminal (Administrador)"** (o **"Windows PowerShell (Administrador)"**). Acepta el aviso de permisos.
2. Ejecuta:
   ```powershell
   wsl --install
   ```
   Esto activa WSL2 e instala **Ubuntu** por defecto.
3. **Reinicia** el equipo cuando lo pida.

#### B) Primer arranque de Ubuntu
1. Tras reiniciar, se abre sola una ventana de Ubuntu (o ábrela desde el menú Inicio → **"Ubuntu"**). La primera vez tarda 1–2 minutos en terminar de instalarse.
2. Crea tu **usuario y contraseña de Linux** (no tienen que coincidir con los de Windows). Al escribir la contraseña **no se ve nada en pantalla** — es normal, sigue escribiendo y pulsa Enter.
3. Actualiza el sistema:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

#### C) Cómo iniciarlo después
Abre **"Ubuntu"** desde el menú Inicio, **o** escribe `wsl` en cualquier PowerShell / Terminal de Windows. Se abre la terminal de Linux donde corre todo lo de esta guía.

#### D) Verificar que es WSL2
En PowerShell:
```powershell
wsl -l -v
```
La columna **VERSION** debe decir **2**. Si dijera 1, conviértelo: `wsl --set-version Ubuntu 2`.

> **Si `wsl --install` no funciona** (Windows antiguo o edición restringida): actualiza Windows a la última versión; o instala **"Windows Subsystem for Linux"** y **"Ubuntu"** desde la Microsoft Store; o consulta la guía oficial: https://learn.microsoft.com/windows/wsl/install

**Una vez dentro de Ubuntu, continúa esta guía desde el paso 4** como en cualquier Linux.

- **GPU en WSL2 (opcional):** basta con tener el **driver de NVIDIA para Windows** instalado (el normal, del sitio de NVIDIA). **No** instales el CUDA Toolkit dentro de WSL — el driver de Windows ya expone la GPU. Compruébalo con `nvidia-smi` dentro de Ubuntu; luego el bloque de GPU del paso 4.3 funciona igual.
- **Dónde poner los archivos:** guarda tus documentos dentro del sistema de Linux (`~/…`) para máxima velocidad. Los archivos de Windows están montados en `/mnt/c/…` (p. ej. `/mnt/c/Users/TuUsuario/Downloads/…`), útil si el audio/PDF vive en Windows.

> Si prefieres **Windows nativo** (sin WSL2), casi todo funciona pero cambian: la instalación de `uv` (PowerShell), la ruta del venv (`.venv\Scripts\python.exe`), la GPU de audio (requiere CUDA/cuDNN en el `PATH`, no el mecanismo de esta guía) y MD→PDF (WeasyPrint necesita el runtime GTK3). Por eso se recomienda WSL2.

---

## 4. Instalación paso a paso

Todos los comandos asumen que estás en la carpeta del proyecto. Ajusta la ruta si la cambias.

### 4.1 Instalar `uv` y crear el entorno

`uv` es un gestor de entornos/paquetes rápido (reemplaza a `pip`/`venv`). Este proyecto **no usa `pip`**: siempre `uv pip install --python .venv/bin/python ...`.

```bash
# 1) instalar uv (si no lo tienes)
curl -LsSf https://astral.sh/uv/install.sh | sh
#    reinicia la terminal, o:  source ~/.bashrc

# 2) crear la carpeta del proyecto y el entorno (Python 3.12)
mkdir -p ~/markitdown-tools && cd ~/markitdown-tools
uv venv --python=3.12 .venv
```

A partir de aquí, el intérprete del proyecto es `./.venv/bin/python`.

### 4.2 Base: documentos → Markdown (obligatorio)

```bash
uv pip install --python .venv/bin/python 'markitdown[all]' wordfreq
```

- `markitdown[all]` — el conversor base (PDF, docx, pptx, xlsx, html…).
- `wordfreq` — lo usa el reparador de ligaduras de `convertir_pdf.py`.
- *(Opcional)* diccionario del sistema para mejorar el reparado: en Debian/Ubuntu `sudo apt install wamerican` (crea `/usr/share/dict/words`). Sin él, el reparador igual funciona con `wordfreq`.

### 4.3 Audio → Markdown (opcional)

```bash
uv pip install --python .venv/bin/python faster-whisper av
```

**Para acelerar con GPU NVIDIA** (opcional, muy recomendado si la tienes), añade las librerías CUDA que necesita faster-whisper/CTranslate2:

```bash
uv pip install --python .venv/bin/python nvidia-cudnn-cu12 nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12
```

`transcribir_audio.py` detecta la GPU automáticamente y añade esas librerías al `LD_LIBRARY_PATH` por sí solo (no tienes que exportar nada). Si no hay GPU, cae a CPU sin que hagas nada.

### 4.4 OCR de PDFs escaneados (opcional)

```bash
uv pip install --python .venv/bin/python rapidocr-onnxruntime pypdfium2
```

### 4.5 Markdown → PDF (opcional)

```bash
uv pip install --python .venv/bin/python markdown weasyprint
```

> WeasyPrint necesita algunas librerías del sistema (Pango/Cairo). En Debian/Ubuntu:
> `sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev`.
> Si solo quieres PDF→MD y audio, puedes saltarte este paso.

### 4.6 Subtítulos de YouTube (opcional)

`subs_a_md.py` solo usa la librería estándar de Python. Para **descargar** los subtítulos hace falta `yt-dlp`:

```bash
uv pip install --python .venv/bin/python yt-dlp
```

---

## 5. Los scripts

Crea cada archivo con **el nombre exacto del encabezado**, dentro de la carpeta del proyecto (junto a `.venv/`). Todos comparten el estilo: salida `.md`, mensajes de progreso a `stderr`, y la ruta de salida final a `stdout`.

### 5.1 `convertir_pdf.py` — Documentos (PDF/Office/HTML) → Markdown con reparador de ligaduras

Convierte a Markdown cualquier formato que soporte MarkItDown — **PDF, docx, pptx, xlsx, html…** — y, **solo si detecta el defecto** (típico de PDFs), reconstruye las ligaduras tipográficas (fi/fl/ff…) que algunos exportan como carácter nulo, eligiendo por frecuencia de palabra real la reconstrucción correcta. También normaliza tabuladores usados como separadores. Autodetecta el idioma (es/en).

~~~python
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
~~~

### 5.2 `batch_convert.py` — PDF → Markdown en lote

Recorre una carpeta, convierte **solo los PDF que aún no tienen `.md`**, en paralelo (4 a la vez) y los grandes (>8 MB) de uno en uno. Llama a `convertir_pdf.py` (debe estar en la misma carpeta). Imprime progreso y un resumen.

~~~python
#!/usr/bin/env python
"""Convierte en lote todos los PDFs sin .md bajo una carpeta, usando convertir_pdf.py.

Fase A: archivos <= 8 MB en paralelo (4 a la vez).
Fase B: archivos grandes (> 8 MB) de uno en uno (para no agotar la RAM).
Imprime progreso por archivo y un resumen final.

Uso:
    python batch_convert.py /ruta/a/la/carpeta
"""
import os
import re
import sys
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
# Portable: usa el mismo intérprete que ejecuta este script y busca convertir_pdf.py a su lado.
PY = sys.executable
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "convertir_pdf.py")
BIG = 8 * 1024 * 1024  # umbral "grande"


def pending():
    out = []
    for dp, _, fns in os.walk(ROOT):
        for fn in fns:
            if fn.lower().endswith(".pdf"):
                pdf = os.path.join(dp, fn)
                if not os.path.exists(pdf[:-4] + ".md"):
                    out.append(pdf)
    out.sort(key=os.path.getsize)
    return out


def convert(pdf):
    t0 = time.time()
    info = {"pdf": pdf}
    try:
        r = subprocess.run([PY, SCRIPT, pdf], capture_output=True, text=True, timeout=1800)
        err = r.stderr
    except subprocess.TimeoutExpired:
        info.update(ok=False, secs=round(time.time() - t0, 1), err="timeout (30 min)")
        return info
    md = pdf[:-4] + ".md"
    info["secs"] = round(time.time() - t0, 1)
    info["ok"] = r.returncode == 0 and os.path.exists(md)
    info["words"] = len(open(md, encoding="utf-8").read().split()) if info["ok"] else 0

    def grab(pat):
        m = re.search(pat, err)
        return m.group(1) if m else None

    info["lang"] = grab(r"\[idioma\] (\w+)")
    info["markers"] = grab(r"\[ligaduras\] (\d+) marcadores")
    info["resolved"] = grab(r"-> (\d+) reconstruidas")
    info["unconf"] = grab(r"(\d+) sin confirmar")
    info["tabs"] = grab(r"\[espacios\] (\d+) tab")
    if not info["ok"]:
        lines = err.strip().splitlines()
        info["err"] = lines[-1][:200] if lines else f"returncode={r.returncode}"
    return info


def line(done, total, r):
    name = os.path.basename(r["pdf"])
    name = (name[:52] + "…") if len(name) > 53 else name
    st = "OK   " if r["ok"] else "FALLO"
    extra = []
    if r.get("lang"):
        extra.append(r["lang"])
    if r.get("markers"):
        extra.append(f"lig {r['resolved']}/{r['markers']}" + (f" ({r['unconf']}?)" if r.get("unconf") else ""))
    if r.get("tabs"):
        extra.append(f"tabs {r['tabs']}")
    if r.get("ok"):
        extra.append(f"{r['words']}w")
    if not r["ok"]:
        extra.append(r.get("err", ""))
    print(f"[{done:2d}/{total}] {st} {r['secs']:6.1f}s  {name:<54} {'  '.join(extra)}", flush=True)


def main():
    pdfs = pending()
    small = [p for p in pdfs if os.path.getsize(p) <= BIG]
    large = [p for p in pdfs if os.path.getsize(p) > BIG]
    total = len(pdfs)
    print(f"Pendientes: {total}  (paralelo: {len(small)}, secuencial-grandes: {len(large)})", flush=True)
    results = []
    done = 0

    # Fase A — paralelo
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(convert, p): p for p in small}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            line(done, total, r)

    # Fase B — grandes, de uno en uno
    for p in large:
        r = convert(p)
        results.append(r)
        done += 1
        line(done, total, r)

    print("\n===== RESUMEN =====", flush=True)
    ok = [r for r in results if r["ok"]]
    fail = [r for r in results if not r["ok"]]
    print(f"Convertidos: {len(ok)}/{total}   Fallos: {len(fail)}")
    if fail:
        for r in fail:
            print(f"  ✗ {os.path.basename(r['pdf'])}: {r.get('err')}")


if __name__ == "__main__":
    main()
~~~

### 5.3 `ocr_pdf.py` — OCR de PDF → Markdown

Para escaneados o PDFs con capa de texto corrupta. Rasteriza cada página con pypdfium2, hace OCR con RapidOCR (offline), reordena por coordenadas y une líneas en párrafos.

~~~python
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
~~~

### 5.4 `subs_a_md.py` — Subtítulos (YouTube json3) → Markdown

Convierte subtítulos automáticos `json3` (de yt-dlp) en párrafos limpios respetando pausas y fin de oración. **`transcribir_audio.py` reutiliza sus funciones**, así que este archivo es necesario también para el audio.

~~~python
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
~~~

### 5.5 `transcribir_audio.py` — Audio → Markdown

Transcribe audio con **faster-whisper** (GPU o CPU), sin ffmpeg del sistema (decodifica con PyAV). Por defecto usa el modelo `large-v3-turbo` en GPU; con `--device cpu` corre en CPU. Reutiliza el agrupado en párrafos de `subs_a_md.py` (que debe estar al lado).

> El script incluye un flag opcional `--diarize` (etiquetar hablantes) que requiere un stack adicional (pyannote/torch + token de HuggingFace) **no cubierto en esta guía**. Para transcripción normal, ignóralo.

~~~python
#!/usr/bin/env python
"""Transcribe un archivo de audio a Markdown con faster-whisper (local, sin ffmpeg del sistema).

faster-whisper (CTranslate2 + PyAV) decodifica mp3/wav/m4a/ogg con sus propios códecs, así que
NO necesita ffmpeg del sistema. La salida son párrafos limpios (reutiliza la agrupación de
subs_a_md.py). El idioma se autodetecta (es/en/...).

Uso:
    python transcribir_audio.py audio.mp3 [-o salida.md] [--model large-v3-turbo] [--device auto]
                                 [--diarize] [--min-speakers N] [--max-speakers N] [--lang es]

Modelos recomendados:
    large-v3-turbo  -> mejor balance calidad/velocidad (por defecto)
    large-v3        -> máxima calidad
    medium / small  -> más ligeros

Dispositivo (--device):
    auto  -> usa GPU CUDA si está disponible, si no CPU (por defecto)
    cuda  -> fuerza GPU (necesita los wheels nvidia-cudnn-cu12 / nvidia-cublas-cu12; se auto-cargan)
    cpu   -> fuerza CPU (int8)

Diarización (--diarize): identifica hablantes con pyannote.audio (rama 3.x). Requiere:
    uv pip install 'pyannote.audio>=3.1,<4' torch
    aceptar las condiciones de pyannote/speaker-diarization-3.1 y pyannote/segmentation-3.0 en HF,
    y un token en HF_TOKEN (variable de entorno) o --hf-token. Tras descargar, corre 100% local.
"""
import sys
import os
import argparse


def _bootstrap_cuda_libs():
    """Añade los dirs de librerías de los wheels nvidia-* al LD_LIBRARY_PATH y re-ejecuta.

    CTranslate2 (faster-whisper en GPU) necesita libcudnn/libcublas. Los wheels de pip los
    instalan en site-packages/nvidia/*/lib, pero el linker dinámico solo los ve si están en
    LD_LIBRARY_PATH ANTES de arrancar el proceso. Por eso, si faltan, los añadimos y re-ejecutamos.
    """
    import glob
    import importlib.util

    spec = importlib.util.find_spec("nvidia")
    if spec is None or not spec.submodule_search_locations:
        return  # sin wheels nvidia: o es CPU, o las libs están en el sistema
    base = list(spec.submodule_search_locations)[0]  # .../site-packages/nvidia
    libdirs = sorted(glob.glob(os.path.join(base, "*", "lib")))
    if not libdirs:
        return
    cur = os.environ.get("LD_LIBRARY_PATH", "")
    if all(d in cur.split(":") for d in libdirs):
        return  # ya configurado (probablemente ya re-ejecutamos)
    os.environ["LD_LIBRARY_PATH"] = ":".join(libdirs + ([cur] if cur else []))
    os.execv(sys.executable, [sys.executable] + sys.argv)  # re-exec con el nuevo entorno


def decode_audio(path, target_sr=16000):
    """Decodifica el audio completo con PyAV -> numpy float32 mono a 16 kHz (sin ffmpeg del sistema)."""
    import numpy as np
    import av

    container = av.open(path)
    stream = container.streams.audio[0]
    resampler = av.AudioResampler(format="s16", layout="mono", rate=target_sr)
    chunks = []
    for frame in container.decode(stream):
        for rf in resampler.resample(frame):
            chunks.append(rf.to_ndarray().reshape(-1).astype(np.float32) / 32768.0)
    container.close()
    if not chunks:
        raise RuntimeError("No se pudo decodificar audio del archivo.")
    return np.concatenate(chunks)


def assign_speakers(events, turns):
    """A cada evento (start_ms, end_ms, txt) le asigna el hablante con mayor solape temporal.

    `turns` es lista de (start_s, end_s, speaker_label). Devuelve [(start_ms, end_ms, txt, spk)].
    """
    out = []
    for start_ms, end_ms, txt in events:
        s, e = start_ms / 1000.0, end_ms / 1000.0
        best_spk, best_ov = None, 0.0
        for ts, te, spk in turns:
            ov = min(e, te) - max(s, ts)
            if ov > best_ov:
                best_ov, best_spk = ov, spk
        out.append((start_ms, end_ms, txt, best_spk))
    return out


def relabel_speakers(labeled):
    """Renombra SPEAKER_xx -> 'Hablante 1', 'Hablante 2'... en orden de aparición."""
    mapping = {}
    for *_, spk in labeled:
        if spk is not None and spk not in mapping:
            mapping[spk] = f"Hablante {len(mapping) + 1}"
    return mapping


def _cuda_available():
    """Detecta si CTranslate2 puede usar CUDA (sin requerir torch)."""
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _diarize(audio, token, device, min_speakers, max_speakers):
    """Corre pyannote.audio sobre el waveform en memoria. Devuelve [(start_s, end_s, speaker)]."""
    if not token:
        sys.exit("[error] La diarización requiere un token de HuggingFace. Acepta las condiciones de "
                 "pyannote/speaker-diarization-3.1 y pyannote/segmentation-3.0, crea un token en "
                 "hf.co/settings/tokens y pásalo con --hf-token o la variable HF_TOKEN.")
    try:
        import torch
        from pyannote.audio import Pipeline
    except ImportError:
        sys.exit("[error] Falta pyannote/torch. Instala: uv pip install 'pyannote.audio>=3.1,<4' torch")
    pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=token)
    # La diarización elige su propio dispositivo según lo que vea torch (independiente del ASR):
    # en este entorno torch es CPU-only (para no chocar con el cuDNN 9 que usa faster-whisper en GPU).
    dia_device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"    (pyannote en {dia_device})", file=sys.stderr)
    pipe.to(torch.device(dia_device))
    waveform = torch.from_numpy(audio).unsqueeze(0)  # (1, n)
    kw = {}
    if min_speakers is not None:
        kw["min_speakers"] = min_speakers
    if max_speakers is not None:
        kw["max_speakers"] = max_speakers
    diar = pipe({"waveform": waveform, "sample_rate": 16000}, **kw)
    return [(turn.start, turn.end, spk) for turn, _, spk in diar.itertracks(yield_label=True)]


def _render_with_speakers(labeled, mapping, subs_a_md, gap, max_words):
    """Agrupa eventos consecutivos del mismo hablante y los vuelca con encabezado '**Hablante N:**'."""
    blocks = []
    cur_spk, cur_events = None, []
    for start_ms, end_ms, txt, spk in labeled:
        if spk != cur_spk and cur_events:
            blocks.append((cur_spk, cur_events))
            cur_events = []
        cur_spk = spk
        cur_events.append((start_ms, end_ms, txt))
    if cur_events:
        blocks.append((cur_spk, cur_events))

    out = []
    for spk, evs in blocks:
        name = mapping.get(spk, "Hablante ?")
        paras = subs_a_md.build_paragraphs(evs, gap_ms=gap, max_words=max_words)
        if paras:
            out.append(f"**{name}:** " + paras[0])
            out.extend(paras[1:])
    return "\n\n".join(out)


def main():
    _bootstrap_cuda_libs()

    ap = argparse.ArgumentParser(description="Audio -> Markdown con faster-whisper (local).")
    ap.add_argument("entrada", help="Archivo de audio (mp3, wav, m4a, ogg, ...)")
    ap.add_argument("-o", "--output", help="Salida .md (por defecto: junto al audio)")
    ap.add_argument("--model", default="large-v3-turbo",
                    help="tiny|base|small|medium|large-v3|large-v3-turbo (def: large-v3-turbo)")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"],
                    help="auto (GPU si hay) | cuda | cpu (def: auto)")
    ap.add_argument("--compute", default=None,
                    help="Tipo de cómputo CT2 (def: int8_float16 en cuda, int8 en cpu)")
    ap.add_argument("--lang", default=None, help="Idioma (es, en, ...). Por defecto autodetecta.")
    ap.add_argument("--title", default=None, help="Título del documento")
    ap.add_argument("--gap", type=int, default=2000, help="Pausa (ms) que corta párrafo")
    ap.add_argument("--max-words", type=int, default=110, help="Palabras objetivo por párrafo")
    ap.add_argument("--diarize", action="store_true", help="Identificar hablantes (pyannote, requiere token HF)")
    ap.add_argument("--min-speakers", type=int, default=None, help="Mínimo de hablantes (diarización)")
    ap.add_argument("--max-speakers", type=int, default=None, help="Máximo de hablantes (diarización)")
    ap.add_argument("--hf-token", default=None, help="Token de HuggingFace (o usa la var HF_TOKEN)")
    args = ap.parse_args()

    import subs_a_md  # reutiliza build_paragraphs() y clean()

    device = args.device
    if device == "auto":
        device = "cuda" if _cuda_available() else "cpu"
    compute = args.compute or ("int8_float16" if device == "cuda" else "int8")

    # 1) Decodificar una sola vez (sirve para ASR y, si aplica, diarización)
    print("[1] decodificando con PyAV...", file=sys.stderr)
    audio = decode_audio(args.entrada)
    dur_s = len(audio) / 16000
    print(f"    -> {dur_s/60:.1f} min de audio", file=sys.stderr)

    # 2) Transcripción (ASR)
    import time
    from faster_whisper import WhisperModel
    print(f"[2] cargando {args.model} en {device} ({compute})...", file=sys.stderr)
    model = WhisperModel(args.model, device=device, compute_type=compute)
    t0 = time.time()
    segments, info = model.transcribe(audio, language=args.lang, vad_filter=True, beam_size=5)
    events = [(int(s.start * 1000), int(s.end * 1000), s.text.strip()) for s in segments if s.text.strip()]
    asr_dt = time.time() - t0
    print(f"    -> {len(events)} segmentos en {asr_dt:.1f}s (RTFx {dur_s/asr_dt:.1f}x) | "
          f"idioma {info.language} ({info.language_probability:.2f})", file=sys.stderr)
    del model  # liberar VRAM antes de la diarización

    title = args.title or os.path.splitext(os.path.basename(args.entrada))[0]
    header = (f"# {title}\n\n"
              f"> Transcripción de audio (faster-whisper {args.model}, {device}, idioma {info.language}"
              f"{', con diarización' if args.diarize else ''}).\n\n")

    # 3) Diarización opcional
    if args.diarize:
        print("[3] diarización con pyannote...", file=sys.stderr)
        turns = _diarize(audio, args.hf_token or os.environ.get("HF_TOKEN"),
                         device, args.min_speakers, args.max_speakers)
        labeled = assign_speakers(events, turns)
        mapping = relabel_speakers(labeled)
        print(f"    -> {len(mapping)} hablantes detectados", file=sys.stderr)
        body = _render_with_speakers(labeled, mapping, subs_a_md, args.gap, args.max_words)
    else:
        paras = subs_a_md.build_paragraphs(events, gap_ms=args.gap, max_words=args.max_words)
        body = "\n\n".join(paras)

    out_text = header + body + "\n"
    output = args.output or (os.path.splitext(args.entrada)[0] + ".md")
    with open(output, "w", encoding="utf-8") as fh:
        fh.write(out_text)
    print(f"[ok] {len(out_text.split())} palabras -> {output}", file=sys.stderr)
    print(output)


if __name__ == "__main__":
    main()
~~~

### 5.6 `md_a_pdf.py` — Markdown → PDF

El sentido inverso: renderiza un `.md` a PDF con estilo (WeasyPrint).

~~~python
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
~~~

---

## 6. Cómo correr cada caso (ejemplos)

```bash
# --- Documento único -> Markdown (repara ligaduras si hace falta) ---
.venv/bin/python convertir_pdf.py "documento.pdf"                 # crea documento.md al lado
.venv/bin/python convertir_pdf.py "presentacion.pptx"            # también docx, xlsx, html…
.venv/bin/python convertir_pdf.py "documento.pdf" -o salida.md    # salida explícita
.venv/bin/python convertir_pdf.py "documento.pdf" --no-fix        # sin reparar (crudo)

# --- Carpeta entera de PDFs (solo los que no tienen .md) ---
.venv/bin/python batch_convert.py "/ruta/a/la/carpeta"

# --- OCR (PDF escaneado o con texto corrupto) ---
.venv/bin/python ocr_pdf.py "escaneado.pdf" -o escaneado.md

# --- Audio -> Markdown ---
.venv/bin/python transcribir_audio.py "audio.mp3"                 # GPU si hay; si no, CPU
.venv/bin/python transcribir_audio.py "audio.m4a" --device cpu --model small   # forzar CPU + modelo ligero
.venv/bin/python transcribir_audio.py "audio.mp3" --lang es --title "Mi audio" -o salida.md

# --- Subtítulos de YouTube -> Markdown ---
yt-dlp --skip-download --write-auto-subs --sub-langs es --sub-format json3 -o "video.%(ext)s" "URL_DE_YOUTUBE"
.venv/bin/python subs_a_md.py "video.es.json3" -o video.md --title "Título" --url "URL_DE_YOUTUBE"

# --- Markdown -> PDF ---
.venv/bin/python md_a_pdf.py "documento.md"                       # crea documento.pdf
```

**Modelos de audio (velocidad vs. calidad):** `large-v3-turbo` (por defecto, ideal en GPU) · `large-v3` (máxima calidad) · `medium`/`small` (recomendados en CPU por velocidad). En CPU, empieza con `--model small` y sube si la calidad no basta.

---

## 7. Verificación rápida

```bash
# 1) el entorno responde y MarkItDown está
.venv/bin/python -c "import markitdown, wordfreq; print('base OK')"

# 2) audio (si lo instalaste): ¿ve la GPU? (imprime True/False, ambas válidas)
.venv/bin/python -c "import ctranslate2; print('GPUs CUDA:', ctranslate2.get_cuda_device_count())"

# 3) prueba end-to-end de PDF (usa cualquier PDF con texto)
.venv/bin/python convertir_pdf.py "algun.pdf" && echo "PDF->MD OK"
```

Un PDF convertido correctamente produce un `.md` con miles de caracteres. Si sale **vacío**, el PDF es escaneado → usa `ocr_pdf.py`.

---

## 8. Notas y límites

- **Todo local y privado:** ningún script sube datos a internet (excepto la descarga inicial de modelos de Whisper la primera vez que transcribes, y `yt-dlp` que baja subtítulos de YouTube por diseño).
- **PDF vacío = escaneado:** MarkItDown extrae texto, no hace OCR. Si el `.md` sale vacío, el PDF no tiene capa de texto → `ocr_pdf.py`.
- **Reparador de ligaduras:** solo actúa si detecta el defecto (caracteres nulos donde iban fi/fl/ff…). Un PDF sano no se toca. Reporta a `stderr` las palabras "sin confirmar" por si quieres revisarlas.
- **Audio sin ffmpeg:** gracias a PyAV. Formatos probados: mp3, m4a, wav, mp4 (audio), ogg.
- **GPU:** la primera transcripción descarga el modelo (`large-v3-turbo` ≈ 1.5 GB) y tarda más; las siguientes son rápidas. En CPU, prefiere `--model small`/`medium`.
- **Extensión avanzada (no cubierta):** `transcribir_audio.py --diarize` puede etiquetar hablantes con pyannote, pero requiere instalar torch/pyannote y un token de HuggingFace, y añade complejidad. Se deja fuera de esta guía a propósito para mantener la instalación limpia.
