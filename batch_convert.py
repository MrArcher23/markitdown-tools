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
