# Informe: ASR local (audio → Markdown) para tu RTX 3060 6 GB, español MX

> Investigación multi-agente (GitHub + web) con verificación adversarial. Hardware objetivo:
> Intel i7-11800H (16 hilos), 15 GB RAM, NVIDIA RTX 3060 Laptop 6 GB VRAM (CUDA), sin ffmpeg del sistema.

## 1. Resumen ejecutivo

El mejor stack local para tu caso es **faster-whisper con `large-v3-turbo` (int8_float16) en GPU CUDA** como motor por defecto, manteniendo tu pipeline actual (cero dependencia de ffmpeg del sistema gracias a PyAV). Para reuniones con varios hablantes, añade **pyannote.audio fijado en la rama 3.x** como paso de diarización secuencial, alimentándolo con el waveform que PyAV ya decodifica. Si algún día priorizas máxima precisión/velocidad en español y aceptas montar NeMo, **NVIDIA Parakeet-TDT-0.6B-v3** tiene el WER español más bajo verificado (3.45% en FLEURS), pero rompe la simplicidad de tu flujo. La capa de Markdown la sigues resolviendo tú con `subs_a_md.build_paragraphs()`, que es mejor que lo que ofrecen las apps existentes.

---

## 2. Qué se necesita para audio → Markdown: las tres capas

| Capa | Función | Tu situación |
|---|---|---|
| **1. Decodificación de audio** | Convertir mp3/m4a a PCM 16 kHz mono | **PyAV** (incluido en faster-whisper) trae las libs de ffmpeg empaquetadas → NO necesitas ffmpeg del sistema. Esta es tu carta clave: reutilízala para alimentar cualquier otro motor. |
| **2. ASR / transcripción** | Audio → texto con timestamps | Hoy faster-whisper `small` en CPU. Tienes margen para subir mucho. |
| **3. Post-proceso a Markdown** | Párrafos, puntuación, encabezados, hablantes | Tu `subs_a_md.py` ya lo hace. Casi ninguna herramienta del mercado lo hace mejor de forma nativa. |
| **(opcional) Diarización** | "Quién habla cuándo" | Pendiente. pyannote 3.x es el estándar; se cruza por solape temporal con los segmentos del ASR. |

Punto crítico confirmado: tanto NeMo/Parakeet como pyannote pueden recibir un **array/tensor numpy 16 kHz mono ya decodificado**, lo que te permite esquivar por completo el ffmpeg del sistema decodificando con PyAV. Lo que SÍ requiere ffmpeg instalado (y por tanto se complica en tu entorno) es WhisperX, whisper-diarization y diart.

---

## 3. Tabla comparativa de motores ASR

| Motor / modelo | Local | ffmpeg sistema | ¿Cabe en 6 GB? | Español | Diarización | Velocidad | Salida |
|---|---|---|---|---|---|---|---|
| **faster-whisper large-v3-turbo** | Sí | **NO** (PyAV) | **Sí, holgado** (int8 ~1–1.5 GB) | Muy buena (~large-v2) | No nativa | ~6x más rápido que large-v3 | Segmentos + timestamps (word-level opc.) |
| **faster-whisper large-v3** | Sí | **NO** (PyAV) | **Sí** (int8 ~1.2–1.5 GB pico real) | Excelente (Tier 1, ~3–6% WER audio limpio) | No nativa | Sub-tiempo-real en GPU | Igual |
| **faster-whisper small** (actual) | Sí | **NO** | Sí, sobrado | Aceptable, claramente peor | No | Rápido | Igual |
| **distil-whisper-large-v3-es** (CT2) | Sí | **NO** (versión CT2) | **Sí** (~1.5 GB) | 5.11% WER norm. / 10.15% ortográfico (CV16.1) | No | Rápido | Igual |
| **NeMo Parakeet-TDT-0.6B-v3** | Sí | Parcial* | **Sí** (~5 GB óptimo / chunking) | **Mejor: 3.45% FLEURS es** (¡es_419 = LatAm!) | No (NeMo aparte) | Altísima (RTFx 3332) | Texto con puntuación+mayúsculas + timestamps ricos |
| **NeMo Canary-1B-v2** | Sí | Parcial* | Sí, ajustado (~2 GB pesos, chunking) | Muy buena (Fleurs-25 8.40%) + traducción | No | RTFx 749 | Texto + timestamps, export SRT |
| **Canary-Qwen-2.5B** | Sí | Parcial* | **NO** (~5 GB solo pesos) | Limitado (inglés) | No | Lento | Texto (LLM) |
| **Meta MMS (mms-1b-all)** | Sí | Sí (práctica) | Sí (~3–4 GB) | Flojo en alto-recurso; **sin puntuación/timestamps** | No | Rápido (CTC) | Texto crudo CTC (mal para Markdown) |
| **Vosk** | Sí | NO (con WAV) | Sí, mínimo (CPU) | Inferior | Speaker-ID básico | Tiempo real CPU | JSON + timestamps palabra |
| **Moonshine** | Sí | NO | Sí, mínimo (CPU) | Modelo Base es **licencia NO comercial** | No | Latencia mínima CPU | Texto |

\* NeMo: lee WAV/FLAC con libsndfile; mp3/m4a necesitaría ffmpeg **salvo que pases el array numpy decodificado con PyAV** → evitable.

**Lo que cabe cómodo en 6 GB:** todos los faster-whisper, distil-es, Parakeet-v3, Canary-1B-v2 (ajustado), MMS, Vosk, Moonshine. **Lo que NO cabe:** Canary-Qwen-2.5B; y pyannote.audio 4.x (ver §5).

---

## 4. Recomendación afinada a tu hardware (RTX 3060 6 GB, español MX)

**(a) Máxima calidad**
- **Motor:** faster-whisper, modelo **`large-v3`**, `compute_type="int8_float16"` o `"float16"`, `device="cuda"`, `vad_filter=True`.
- Por qué: es la mejor calidad genérica del ecosistema Whisper para español (Tier 1), cabe en int8 (~1.2–1.5 GB pico real medido, no los 2.5–3 GB conservadores), y mantiene tu pipeline sin ffmpeg. Para habla espontánea mexicana con ruido (reuniones), la ventaja de large-v3 sobre small se **amplía**.
- Alternativa si aceptas montar NeMo: **Parakeet-TDT-0.6B-v3**, que tiene el WER español más bajo verificado (3.45%). Dato favorable y verificado: ese FLEURS español es **es_419 (latinoamericano)**, no peninsular — más cercano a tu español de México de lo que se creía. Contras: dependencia pesada de NeMo, chunking manual del audio largo en 6 GB, y pre-decodificar mp3/m4a con PyAV.

**(b) Máxima velocidad**
- **Motor:** faster-whisper, modelo **`large-v3-turbo`**, `int8_float16`, `device="cuda"`.
- Por qué: ~6x más rápido que large-v3 con calidad cercana a large-v2, ~1–1.5 GB VRAM (deja sitio para diarización), y cambio trivial de `model_size`. Es la mejor relación calidad/velocidad para español en tu GPU y mi recomendación como **nuevo modelo por defecto**.

**GPU vs CPU:** usa **GPU (cuda)** para el ASR. Hoy corres en CPU int8 (~12 min por hora de audio); pasar a la 3060 te da un salto grande de velocidad. Nota de orquestación: si dejas el ASR en GPU, ejecuta la diarización **después** (secuencial). Alternativa válida: ASR en CPU + diarización en GPU simultánea, ya que la GPU queda libre — pero en general GPU para ASR rinde más.

---

## 5. Diarización: mejor opción local

**Recomendado: pyannote.audio fijado en la rama 3.x** con el modelo `speaker-diarization-3.1`.

- **Por qué:** es el estándar de facto con mejor DER open-source; es **idioma-agnóstico** (funciona igual en español MX, se mide en DER no WER); pico ~2.6 GB VRAM (cabe holgado en 6 GB, incluso junto a un Whisper); y acepta **waveform en memoria** `{'waveform': tensor, 'sample_rate': 16000}`, lo que te permite alimentarlo con PyAV y **evitar el ffmpeg del sistema**. Integra limpio con tu faster-whisper: solo escribes la lógica de solape temporal por frase.
- **Aviso de versión (importante):** **NO uses pyannote.audio 4.x / modelo community-1 en 6 GB.** Hay una regresión documentada (issue #1963) que dispara la VRAM a >9.5 GB pico (medido con community-1 en el paso `discrete_diarization`). Fija la versión: `pip install 'pyannote.audio>=3.1,<4'`.
- **Token/licencia:** el modelo es **gated en HuggingFace**. Una sola vez debes: (1) aceptar las condiciones (gratis) de `pyannote/speaker-diarization-3.1` **y** de `pyannote/segmentation-3.0`, (2) crear un token en hf.co/settings/tokens, (3) instanciar con `Pipeline.from_pretrained(..., use_auth_token=TOKEN)`. Tras descargar los pesos, la inferencia es 100% local/offline.

**Integración (patrón WhisperX, sin usar WhisperX):**
1. Decodifica el audio una vez con PyAV → array float32 16 kHz mono.
2. ASR con faster-whisper → segmentos `(start, end, text)`.
3. Diarización con pyannote (mismo waveform) → segmentos `(start, end, SPEAKER_xx)`.
4. Asigna a cada frase el hablante con **mayor solape temporal**.
5. Vuelca a Markdown con `**SPEAKER_00:** …`.

**Alternativa sin token HF** (si te molesta el gated): NeMo (Sortformer/MSDD) o el pipeline whisper-diarization (NeMo, sin token). Contras: Sortformer está optimizado a **inglés** (riesgo en español MX) y topa en 4 hablantes; whisper-diarization requiere ffmpeg + Cython y su variante paralela pide ≥10 GB (usa `diarize.py` secuencial). **Descartado:** simple-diarizer (exige fijar nº de hablantes a mano, malo para reuniones).

---

## 6. Capa de Markdown

Conclusión transversal verificada: **casi ninguna herramienta produce "Markdown con párrafos legibles" de forma nativa** (exportan SRT/VTT/TXT/JSON por segmento). Tu `subs_a_md.build_paragraphs()` ya resuelve lo que ellas no. Mantén tu enfoque y añade capas encima:

1. **Puntuación/mayúsculas:** si usas un motor que no las trae (MMS, Vosk), aplica un modelo de restauración de puntuación (tipo el de whisper-diarization / `deepmultilingualpunctuation`) antes de agrupar. Con large-v3/turbo o Parakeet ya vienen nativas, así que este paso es opcional.
2. **Párrafos:** tu heurística por pausas/longitud actual. Funciona.
3. **Hablantes:** tras el merge con pyannote, agrupa frases consecutivas del mismo hablante bajo un encabezado `**SPEAKER_00:**` (o reetiqueta a "Hablante 1", "Mentor", etc.).
4. **Timestamps opcionales:** ya tienes `start/end` por segmento; emítelos como `[mm:ss]` al inicio de párrafo si lo deseas.
5. **Resumen/capítulos (opcional):** fase LLM local **posterior** a liberar la VRAM del ASR (Ollama con modelo 3–7B cuantizado), pidiéndole salida en Markdown con encabezados. Referencias de implementación de "audio→Markdown con hablantes+resumen" 100% local: **ownscribe** (emite Markdown con secciones Summary/Key Points/Action Items) y **Scriberr**.

Flujo final: `PyAV → faster-whisper(GPU) → [pyannote sobre waveform] → merge por solape → build_paragraphs → (opcional) puntuación → (opcional) LLM resumen`.

---

## 7. Plan concreto de próximos pasos

**Decisión sobre ffmpeg:** NO necesitas instalarlo si te quedas en faster-whisper + pyannote alimentado por waveform. Mantén el camino PyAV. (Solo lo necesitarías si optaras por WhisperX / whisper-diarization / diart.)

**Paso 1 — Subir el ASR a GPU y mejor modelo (cambio mínimo):**
En `transcribir_audio.py`, añade un flag `--device` y cambia el modelo por defecto:
```python
# de: WhisperModel("small", device="cpu", compute_type="int8")
# a:
WhisperModel("large-v3-turbo", device="cuda", compute_type="int8_float16")
# con vad_filter=True en transcribe()
```

**Paso 2 — CUDA/cuDNN para CTranslate2 en GPU:**
faster-whisper en GPU necesita las librerías CUDA/cuDNN que CTranslate2 espera. La vía más simple es instalar los wheels de NVIDIA por pip (evita pelear con el CUDA del sistema):
```bash
pip install --upgrade faster-whisper
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```
Verifica que `device="cuda"` carga sin error de cuDNN; si lo hay, suele ser versión de cuDNN. (Este punto conviene **validar en tu equipo**: no se especificaron versiones exactas de cuDNN para tu driver.)

**Paso 3 — Diarización opcional:**
```bash
pip install 'pyannote.audio>=3.1,<4'
```
Acepta los términos de `speaker-diarization-3.1` y `segmentation-3.0` en HF, genera token, y añade un flag `--diarize` que: decodifica con PyAV → corre pyannote sobre el tensor → fusiona con los segmentos del ASR → emite Markdown con hablantes.

**Paso 4 — Evolución de `transcribir_audio.py`:**
- `--device {cpu,cuda}` (default cuda).
- `--model {large-v3-turbo,large-v3,medium,small}` (default large-v3-turbo).
- `--diarize` (off por defecto; on para reuniones/mentorías).
- `--min-speakers/--max-speakers` (opcional, pasados a pyannote).
- Reutiliza tu `subs_a_md.py` para el render final.

**Paso 5 (opcional, futuro) — A/B test español:** convierte un fine-tune es a CT2 y compáralo contra large-v3-turbo base en TU audio real:
```bash
pip install ctranslate2 transformers
ct2-transformers-converter --model adriszmar/whisper-large-v3-turbo-es \
  --output_dir faster-turbo-es --quantization int8_float16
```

---

## 8. Riesgos, contras y afirmaciones inciertas/refutadas

**Refutado en la verificación (corrígelo en tu cabeza):**
- "FLEURS español de Parakeet es castellano/peninsular" → **FALSO**: el split es **es_419 (latinoamericano)**. Esto te favorece (más cercano a México). Lo único cierto es que NVIDIA etiqueta los 25 idiomas como "europeos" por idioma, no por variante grabada.
- "Coqui AI cerró en diciembre 2025 y el repo está archivado" → **FALSO**: cerró en **dic-2023/ene-2024** y el repo NO está formalmente archivado (solo aviso de "no longer maintained"). De todos modos, Coqui se descarta (descontinuado).

**Inciertos / no medidos directamente (sé escéptico):**
- **Acento mexicano espontáneo:** todos los WER estrella (Parakeet 3.45%, Whisper ~3–6%, distil-es 5.11%) provienen de **lectura con audio limpio** (FLEURS/Common Voice). En notas de voz/reuniones reales con ruido, jerga y solapes, el **WER real será varios puntos mayor para TODOS los modelos**. No tomes 3–5% como expectativa. Valida con una muestra tuya antes de migrar todo.
- **VRAM "cabe en 6 GB" de Parakeet/Canary:** son estimaciones extrapoladas de las model cards (que citan RAM mínima, no VRAM máxima) más chunking. No medido en tu GPU.
- **Picos de VRAM exactos:** el pico real de int8 large-v3 es ~1.2–1.5 GB (el 2.5–3 GB era conservador). El issue #1963 tiene inconsistencia interna (título 2.59 GB vs tabla 1.59 GB para 3.x); la conclusión "4.x no cabe en 6 GB" sí es sólida.
- **CUDA/cuDNN en tu equipo:** que faster-whisper arranque en GPU depende de versiones de cuDNN compatibles con tu driver; es el punto más probable de fricción técnica y debes probarlo.
- **Fine-tunes es (adriszmar, Berly00, distil-es):** mejoran sobre Common Voice (lectura), pero **no garantizan** mejor resultado en habla espontánea mexicana; large-v3 base suele generalizar mejor en audio real. Prioriza turbo base; los fine-tunes solo como A/B.
- **Moonshine:** latencias exactas (34/69 ms) y WER ~12% salen del paper v2, no reconfirmados uno a uno. Además, su modelo español es **licencia NO comercial** → descártalo si hay uso comercial.
- **Parakeet "~23º en accuracy / 6.5x más rápido que Canary-Qwen":** proviene de un blog terciario (Northflank) y es una instantánea; el ranking varía en el tiempo.

**Contras operativos a tener presentes:**
- pyannote 3.1 requiere token HF + aceptar gated una vez (paso manual).
- NeMo (si vas por Parakeet) es instalación pesada y frágil, y obliga a chunkear audio largo en 6 GB.
- Ejecuta ASR y diarización **secuenciales** para no sumar picos de VRAM.
- Whisper puede alucinar en silencios → mantén `vad_filter=True`.

---

### Nota metodológica
De los 6 frentes de investigación, los de "familia Whisper" y "fit RTX 3060 6 GB" fallaron en producir salida estructurada validada, por lo que **sus cifras específicas (picos exactos de VRAM, real-time-factor en la 3060) no pasaron por la verificación adversarial independiente** y se apoyan en el conocimiento del sintetizador + contexto de hardware. Las dimensiones de español, diarización, ASR no-Whisper y audio→Markdown sí fueron verificadas. Trata las cifras de §4/§3 sobre VRAM y velocidad como orientativas hasta medirlas en tu equipo (ver §8).
