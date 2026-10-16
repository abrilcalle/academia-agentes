"""Descarga los subtítulos de vídeos de YouTube sobre estrategias de trading.

Busca con yt-dlp (lo mismo que usa Agent-Reach para YouTube), guarda la transcripción en
videos/transcripciones/<id>.txt y un índice en videos/indice.json. No descarga vídeo ni audio.
"""
import glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "videos")
TR = os.path.join(OUT, "transcripciones")
IDX = os.path.join(OUT, "indice.json")

BUSQUEDAS = [
    "estrategia trading bitcoin patron doble suelo",
    "estrategia trading criptomonedas paso a paso",
    "estrategia de trading que funciona backtest",
    "price action estrategia soportes y resistencias",
    "bitcoin trading strategy backtested",
    "best swing trading strategy crypto rules",
    "head and shoulders pattern trading strategy rules",
    "bull flag trading strategy rules",
    "trailing stop loss strategy crypto",
    "4 hour chart trading strategy",
]
POR_BUSQUEDA = int(os.environ.get("VIDEOS_POR_BUSQUEDA", "3"))


def vtt_to_text(path):
    lines, last = [], None
    for ln in open(path, encoding="utf-8", errors="ignore"):
        ln = ln.strip()
        if not ln or "-->" in ln or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or ln.isdigit():
            continue
        ln = re.sub(r"<[^>]+>", "", ln)
        if ln != last:
            lines.append(ln)
            last = ln
    return " ".join(lines)


def main():
    os.makedirs(TR, exist_ok=True)
    idx = json.load(open(IDX)) if os.path.exists(IDX) else {}
    tmp = os.path.join(OUT, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    nuevos, errores = 0, []
    for q in BUSQUEDAS:
        cmd = ["yt-dlp", f"ytsearch{POR_BUSQUEDA}:{q}", "--skip-download", "--write-auto-subs", "--write-subs",
               "--sub-langs", "es.*,en.*", "--sub-format", "vtt", "--match-filter", "duration > 240 & duration < 3600",
               "--print-to-file", "%(id)s\t%(title)s\t%(channel)s\t%(duration)s\t%(view_count)s", os.path.join(tmp, "meta.tsv"),
               "-o", os.path.join(tmp, "%(id)s.%(ext)s"), "--ignore-errors", "--no-warnings", "--sleep-requests", "1"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if p.returncode not in (0, 1):
            errores.append(f"{q}: {p.stderr[-300:]}")
        if p.stderr.strip():
            errores.append(f"{q}: {p.stderr.strip()[-300:]}")
    meta = {}
    mp = os.path.join(tmp, "meta.tsv")
    if os.path.exists(mp):
        for ln in open(mp, encoding="utf-8"):
            parts = ln.rstrip("\n").split("\t")
            if len(parts) >= 5:
                meta[parts[0]] = dict(titulo=parts[1], canal=parts[2], duracion=parts[3], vistas=parts[4])
    for vid, m in meta.items():
        if vid in idx:
            continue
        subs = sorted(glob.glob(os.path.join(tmp, f"{vid}*.vtt")), key=lambda f: (".es" not in f, "orig" not in f))
        if not subs:
            continue
        txt = vtt_to_text(subs[0])
        if len(txt) < 500:
            continue
        open(os.path.join(TR, f"{vid}.txt"), "w", encoding="utf-8").write(txt)
        idx[vid] = dict(**m, url=f"https://www.youtube.com/watch?v={vid}", idioma="es" if ".es" in subs[0] else "en",
                        palabras=len(txt.split()), estado="pendiente")
        nuevos += 1
    json.dump(idx, open(IDX, "w"), ensure_ascii=False, indent=1)
    json.dump(dict(nuevos=nuevos, total=len(idx), errores=errores[-20:]), open(os.path.join(OUT, "ultima_descarga.json"), "w"), ensure_ascii=False, indent=1)
    print(f"Vídeos nuevos: {nuevos}. Total: {len(idx)}. Errores: {len(errores)}")
    for e in errores[-10:]:
        print(" -", e)


if __name__ == "__main__":
    main()
