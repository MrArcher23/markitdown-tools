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
