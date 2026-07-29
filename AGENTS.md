# AGENTS.md — Contexto para agentes de IA

> Documento de referencia para un agente (Claude Code, Cursor, etc.) que opera este repositorio.
> Describe **qué puede y qué no puede hacer** la herramienta, cómo invocarla y sus comportamientos no obvios.
> Para instalar desde cero: [`GUIA_DEL_PROYECTO.md`](GUIA_DEL_PROYECTO.md). Para el resumen humano: [`README.md`](README.md).

## 1. Qué es

Colección de **6 scripts CLI independientes** en Python que convierten documentos, audio y subtítulos a **Markdown limpio** (pensado para consumo por LLMs). Se apoyan en [MarkItDown](https://github.com/microsoft/markitdown) (instalado como dependencia desde PyPI) y añaden lo que este no cubre: reparación tipográfica de PDFs, OCR, transcripción de audio y agrupado en párrafos legibles.

**Todo corre en local.** No hay API, servidor ni servicio en la nube. Las únicas salidas a internet son: descarga inicial de los modelos de Whisper (primera transcripción) y `yt-dlp` al bajar subtítulos.

## 2. Mapa de decisión (entrada → script)

| Si el usuario trae… | Usa | Nota |
|---|---|---|
| Un PDF con texto | `convertir_pdf.py` | Camino por defecto |
| Un `.docx`, `.pptx`, `.xlsx`, `.html` | `convertir_pdf.py` | Mismo script, pese al nombre |
| Una **carpeta** de PDFs | `batch_convert.py` | Solo `.pdf` (ver §5) |
| Un PDF **escaneado** o cuyo `.md` salió vacío/corrupto | `ocr_pdf.py` | Requiere deps de OCR |
| Audio o video con voz (`.mp3`, `.m4a`, `.wav`, `.mp4`, `.webm`, `.ogg`) | `transcribir_audio.py` | GPU si hay; si no, CPU |
| Un video de YouTube **con subtítulos** | `yt-dlp` → `subs_a_md.py` | Más rápido que transcribir |
| Un video de YouTube **sin subtítulos** | `yt-dlp -x` → `transcribir_audio.py` | Baja el audio y transcribe |
| Un `.md` que quiere como PDF | `md_a_pdf.py` | Sentido inverso |

**Regla de oro:** para PDFs intenta siempre `convertir_pdf.py` primero. Si el `.md` resultante sale **vacío o casi vacío**, el PDF es escaneado → recurre a `ocr_pdf.py`.

## 3. Capacidades por script

Todos escriben el progreso a `stderr` y la **ruta del `.md` generado a `stdout`** (útil para encadenar).

### `convertir_pdf.py` — Documentos → Markdown
- **Entrada:** cualquier formato de MarkItDown (pdf, docx, pptx, xlsx, html…). **Salida:** `.md`.
- **Flags:** `-o/--output` · `--no-fix` (sin reparaciones) · `--lang {auto,es,en}` (def. `auto`).
- **Valor añadido:** reconstruye **ligaduras** (`fi`/`fl`/`ff`/`ffi`/`ffl`) que ciertos PDFs exportan como carácter nulo, eligiendo por frecuencia real de palabra (`wordfreq` + diccionario del sistema si existe). Normaliza tabuladores usados como separadores. **Ambas reparaciones solo se activan si detecta el defecto**; un archivo sano no se toca.
- **Deps:** `markitdown[all]`, `wordfreq`.

### `batch_convert.py` — Lote → Markdown
- **Entrada:** una carpeta (recursivo). Sin argumento usa el directorio actual. **Salida:** un `.md` por archivo.
- **Comportamiento:** salta los que ya tienen `.md`; ≤8 MB en paralelo (4 hilos), >8 MB secuencial; timeout 30 min por archivo; imprime progreso y resumen.
- **Invoca a `convertir_pdf.py`**, que debe estar en la misma carpeta.
- **Límite:** ⚠️ **solo procesa `.pdf`** (ver §5).

### `ocr_pdf.py` — OCR de PDF → Markdown
- **Entrada:** PDF escaneado o con capa de texto corrupta. **Salida:** `.md` (`-o` es **obligatorio**).
- **Flags:** `--title` · `--scale` (def. `2.0`; mayor = más nítido y lento) · `--start` / `--end` (rango de páginas, 0-based, fin exclusivo).
- **Cómo funciona:** rasteriza con `pypdfium2` → OCR con RapidOCR (offline) → reordena por coordenadas → une renglones en párrafos (deshace cortes con guion) → quita números de página.
- **Deps:** `rapidocr-onnxruntime`, `pypdfium2`.

### `transcribir_audio.py` — Audio → Markdown
- **Entrada:** audio o video con pista de audio. **Salida:** `.md` en párrafos.
- **Flags:** `-o` · `--model` (def. **`large-v3-turbo`**) · `--device {auto,cuda,cpu}` (def. `auto`) · `--compute` (def. `int8_float16` en GPU, `int8` en CPU) · `--lang` (def. autodetecta) · `--title` · `--gap` (ms de pausa que corta párrafo, def. `2000`) · `--max-words` (def. `110`).
- **Rendimiento de referencia:** ~30× tiempo real en una RTX 3060 (6 GB). Ej.: 60 min de audio ≈ 2 min de cómputo.
- **Deps:** `faster-whisper`, `av`. GPU opcional: `nvidia-cudnn-cu12`, `nvidia-cublas-cu12`, `nvidia-cuda-nvrtc-cu12`.
- **Experimental:** `--diarize` (+ `--min-speakers`/`--max-speakers`/`--hf-token`) etiqueta hablantes con pyannote. **No cubierto por la guía**: exige `torch` + `pyannote.audio>=3.1,<4` y un token de HuggingFace. No lo propongas por defecto.

### `subs_a_md.py` — Subtítulos → Markdown
- **Entrada:** archivo `.json3` de yt-dlp. **Salida:** `.md` (`-o` **obligatorio**).
- **Flags:** `--title` · `--url` (nota de fuente) · `--gap` (def. `2000`) · `--max-words` (def. `110`).
- **También es librería:** `transcribir_audio.py` importa su `build_paragraphs()`. **Debe estar presente aunque solo uses audio.**

### `md_a_pdf.py` — Markdown → PDF
- **Uso:** `md_a_pdf.py ENTRADA.md [SALIDA.pdf]` (posicional, sin flags). Sin salida, usa el mismo nombre con `.pdf`.
- **Deps:** `markdown`, `weasyprint` (WeasyPrint requiere librerías del sistema Pango/Cairo).

## 4. Entorno y convenciones

- **Gestor: `uv`, NO `pip`.** El venv no trae `pip`. Instalar siempre así:
  ```bash
  uv pip install --python .venv/bin/python <paquete>
  ```
- **Intérprete:** `./.venv/bin/python` (Python 3.12). En Windows nativo sería `.venv\Scripts\python.exe`, pero **la vía recomendada en Windows es WSL2** (ver guía §3.1).
- **Instalación por partes:** el bloque de documentos es el mínimo; audio, OCR y MD→PDF son opcionales. Instala solo lo que el usuario vaya a usar.
- **No se necesita `ffmpeg` del sistema:** el audio se decodifica con **PyAV**, que trae sus propios códecs.
- **GPU:** el script detecta CUDA solo (`ctranslate2.get_cuda_device_count()`) y añade las rutas de los wheels `nvidia-*` a `LD_LIBRARY_PATH` re-ejecutándose (`_bootstrap_cuda_libs`). **No exportes variables a mano.**

## 5. Límites conocidos (no prometas esto)

- **`batch_convert.py` solo recoge `.pdf`**, aunque `convertir_pdf.py` acepte Office/HTML. Para lote de `.docx` etc., itera tú mismo sobre `convertir_pdf.py`.
- **No hay OCR automático de respaldo:** si un PDF es escaneado, `convertir_pdf.py` devuelve un `.md` vacío sin avisar de que se necesita OCR. Comprueba el tamaño del resultado y decide.
- **La diarización no está soportada** en la instalación estándar (ver arriba). Además, `torch` con CUDA entra en conflicto con la versión de cuDNN que usa faster-whisper; la combinación conocida que funciona es `torch` **CPU-only** + cuDNN 9 para el ASR.
- **El reparador de ligaduras** puede dejar palabras "sin confirmar" (nombres propios, términos raros): las reporta a `stderr` para revisión manual.
- **Los subtítulos automáticos de YouTube** traen errores de reconocimiento; no son una transcripción fiel.
- **Sin interfaz gráfica, sin API, sin modo servidor.** Son scripts CLI de un archivo a la vez (salvo `batch_convert.py`).

## 6. Comandos de referencia

```bash
# Documentos
.venv/bin/python convertir_pdf.py "documento.pdf"
.venv/bin/python convertir_pdf.py "presentacion.pptx" -o salida.md
.venv/bin/python batch_convert.py "/ruta/carpeta"

# OCR (escaneados)
.venv/bin/python ocr_pdf.py "escaneado.pdf" -o escaneado.md --scale 2.0

# Audio
.venv/bin/python transcribir_audio.py "audio.mp3"
.venv/bin/python transcribir_audio.py "audio.m4a" --device cpu --model small

# YouTube con subtítulos
.venv/bin/yt-dlp --skip-download --write-auto-subs --sub-langs es --sub-format json3 -o "v.%(ext)s" "URL"
.venv/bin/python subs_a_md.py "v.es.json3" -o v.md --title "Título" --url "URL"

# YouTube sin subtítulos (baja audio y transcribe)
.venv/bin/yt-dlp -f bestaudio -o "v.%(ext)s" "URL"     # sin -x: PyAV lee webm/m4a directo
.venv/bin/python transcribir_audio.py "v.webm"

# Markdown -> PDF
.venv/bin/python md_a_pdf.py "documento.md"
```

## 7. Verificación del entorno

```bash
.venv/bin/python -c "import markitdown, wordfreq; print('base OK')"
.venv/bin/python -c "import ctranslate2; print('GPUs CUDA:', ctranslate2.get_cuda_device_count())"
```

## 8. Uso responsable

Estas herramientas están pensadas para material sobre el que se tienen derechos o de acceso legítimo: documentos propios, normativa, grabaciones de reuniones, entrevistas y contenido con licencia. No las uses para reproducir obras protegidas por derechos de autor (p. ej. letras de canciones o libros completos) fuera de lo que permita la ley aplicable.

## 9. Otros documentos

- [`GUIA_DEL_PROYECTO.md`](GUIA_DEL_PROYECTO.md) — instalación paso a paso, incluye tutorial de WSL2 y el código completo de cada script.
- [`INVESTIGACION_AUDIO_A_MD.md`](INVESTIGACION_AUDIO_A_MD.md) — comparativa del panorama de ASR local (por qué faster-whisper, alternativas, benchmarks).
