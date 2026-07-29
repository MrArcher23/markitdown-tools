# markitdown-tools

Conjunto de scripts sobre **[MarkItDown](https://github.com/microsoft/markitdown)** para convertir **documentos, audio y subtítulos a Markdown limpio** (ideal para leer con LLMs o archivar como texto). Todo **100% local** (sin API, sin nube).

> 📖 **Guía completa de instalación y uso (paso a paso, con los scripts explicados):** [`GUIA_DEL_PROYECTO.md`](GUIA_DEL_PROYECTO.md) — incluye instrucciones para Windows (WSL2).
>
> 🤖 **¿Eres un agente de IA (Claude Code, Cursor…)?** Empieza por [`AGENTS.md`](AGENTS.md) — capacidades, flags, límites y comportamientos no obvios.

## ¿Qué hace?

| Caso de uso | Script | Descripción |
|---|---|---|
| **Documentos → Markdown** (con reparador) | `convertir_pdf.py` | PDF y también **docx, pptx, xlsx, html…** (vía MarkItDown). En PDFs repara ligaduras rotas (fi/fl/ff) y tabuladores; autodetecta idioma |
| **Lote → Markdown** | `batch_convert.py` | Una carpeta entera, en paralelo; solo los archivos que aún no tienen `.md` |
| **OCR de PDF → Markdown** | `ocr_pdf.py` | Para PDFs escaneados o con capa de texto corrupta (RapidOCR, offline) |
| **Audio → Markdown** | `transcribir_audio.py` | Transcribe con **faster-whisper** (modelo `large-v3-turbo`) en **GPU (~30× tiempo real)** o CPU, **sin ffmpeg** del sistema (PyAV); autodetecta idioma |
| **Subtítulos → Markdown** | `subs_a_md.py` | Subtítulos json3 de YouTube (yt-dlp) → párrafos limpios |
| **Markdown → PDF** | `md_a_pdf.py` | El sentido inverso, con estilo (WeasyPrint) |

## ¿Por qué, si MarkItDown ya convierte?

- **Reparador de ligaduras en PDF:** muchos PDFs (típicamente de libros) exportan `fi`/`fl`/`ff` como carácter nulo → "di erent", "con ict". El script las reconstruye eligiendo por **frecuencia de palabra real** la correcta. Es el principal valor agregado sobre MarkItDown plano.
- **OCR de respaldo:** cuando el PDF es escaneado o su capa de texto está corrupta y la extracción normal falla.
- **Transcripción local de calidad:** faster-whisper `large-v3-turbo`, con aceleración GPU y sin depender de `ffmpeg` del sistema.

## Instalación rápida

Requiere [`uv`](https://docs.astral.sh/uv/). En resumen (ver la guía para el detalle y las partes opcionales):

```bash
uv venv --python=3.12 .venv
uv pip install --python .venv/bin/python 'markitdown[all]' wordfreq   # documentos (PDF/Office/HTML)
uv pip install --python .venv/bin/python faster-whisper av             # audio
```

Ejemplo:

```bash
.venv/bin/python convertir_pdf.py "documento.pdf"      # -> documento.md (también docx/pptx/xlsx/html)
.venv/bin/python transcribir_audio.py "audio.mp3"      # -> audio.md
```

Consulta [`GUIA_DEL_PROYECTO.md`](GUIA_DEL_PROYECTO.md) para OCR, subtítulos, MD→PDF, GPU y Windows.

## Notas

- **Privacidad:** ningún script sube datos a internet (salvo la descarga inicial de modelos de Whisper y `yt-dlp` para subtítulos).
- **Diarización (experimental):** `transcribir_audio.py` incluye un flag `--diarize` para etiquetar hablantes (pyannote); **no está cubierto por la guía** y requiere dependencias extra (torch/pyannote) más un token de HuggingFace.
- `INVESTIGACION_AUDIO_A_MD.md` documenta la investigación del mejor stack local de transcripción (faster-whisper y alternativas).

## Créditos y licencia

Basado en **MarkItDown** (Microsoft, licencia MIT), que se usa como dependencia. Este proyecto se distribuye bajo licencia **MIT** — ver [`LICENSE`](LICENSE).
