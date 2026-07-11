# markitdown-tools

Conjunto de scripts sobre **[MarkItDown](https://github.com/microsoft/markitdown)** para convertir **PDF, audio y subtítulos a Markdown limpio** (ideal para leer con LLMs o archivar como texto). Todo **100% local** (sin API, sin nube).

> 📖 **Guía completa de instalación y uso (paso a paso, con los scripts explicados):** [`GUIA_DEL_PROYECTO.md`](GUIA_DEL_PROYECTO.md) — incluye instrucciones para Windows (WSL2).

## ¿Qué hace?

| Caso de uso | Script | Descripción |
|---|---|---|
| **PDF → Markdown** (con reparador) | `convertir_pdf.py` | Convierte un PDF y repara ligaduras rotas (fi/fl/ff) y tabuladores; autodetecta idioma |
| **PDF → Markdown en lote** | `batch_convert.py` | Una carpeta entera, en paralelo; solo los PDF que aún no tienen `.md` |
| **OCR de PDF → Markdown** | `ocr_pdf.py` | Para PDFs escaneados o con capa de texto corrupta (RapidOCR, offline) |
| **Audio → Markdown** | `transcribir_audio.py` | Transcribe con faster-whisper (GPU/CPU), sin ffmpeg del sistema (PyAV) |
| **Subtítulos → Markdown** | `subs_a_md.py` | Subtítulos json3 de YouTube (yt-dlp) → párrafos limpios |
| **Markdown → PDF** | `md_a_pdf.py` | El sentido inverso, con estilo (WeasyPrint) |

## Instalación rápida

Requiere [`uv`](https://docs.astral.sh/uv/). En resumen (ver la guía para el detalle y las partes opcionales):

```bash
uv venv --python=3.12 .venv
uv pip install --python .venv/bin/python 'markitdown[all]' wordfreq   # PDF
uv pip install --python .venv/bin/python faster-whisper av             # audio
```

Ejemplo:

```bash
.venv/bin/python convertir_pdf.py "documento.pdf"      # -> documento.md
.venv/bin/python transcribir_audio.py "audio.mp3"      # -> audio.md
```

Consulta [`GUIA_DEL_PROYECTO.md`](GUIA_DEL_PROYECTO.md) para OCR, subtítulos, MD→PDF, GPU y Windows.

## Notas

- **Privacidad:** ningún script sube datos a internet (salvo la descarga inicial de modelos de Whisper y `yt-dlp` para subtítulos).
- `INVESTIGACION_AUDIO_A_MD.md` documenta la investigación del mejor stack local de transcripción (faster-whisper y alternativas).

## Créditos y licencia

Basado en **MarkItDown** (Microsoft, licencia MIT), que se usa como dependencia. Este proyecto se distribuye bajo licencia **MIT** — ver [`LICENSE`](LICENSE).
