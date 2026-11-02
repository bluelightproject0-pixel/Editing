"""Sintetiza los SFX (sin derechos) y mezcla voz + SFX en una sola pista maestra.

Uso (desde projects/ramses-popups): python3 build/mix.py   (VARIANT=short para la versión corta)
Lee build/sfx_cues.json (lo escribe build.py) y edit/assets/cut.mp4; escribe edit/assets/audio/master.wav.
"""
import json
import os
import re
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANT = os.environ.get("VARIANT", "long")
PROJ = "edit-short" if VARIANT == "short" else "edit"
CUES = os.path.join(ROOT, "build", "sfx_cues-short.json" if VARIANT == "short" else "sfx_cues.json")
SFX_DIR = os.path.join(ROOT, PROJ, "assets", "sfx")
OUT = os.path.join(ROOT, PROJ, "assets", "audio", "master.wav")
BUNDLED = os.path.join(ROOT, "..", "..", ".claude", "skills", "media-use", "audio", "assets", "sfx")
os.makedirs(SFX_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

SR = 48000

# fuentes sintéticas: filtergraphs de ffmpeg (lavfi)
SYNTH = {
    # golpe de papel: ráfaga de ruido corta, banda media-alta, caída rápida
    "paper-slap": "anoisesrc=d=0.16:c=pink:a=0.9,highpass=f=700,lowpass=f=7000,afade=t=out:st=0.012:d=0.15:curve=exp",
    # papel deslizándose: ruido filtrado con subida y bajada
    "paper-slide": "anoisesrc=d=0.6:c=pink:a=0.7,bandpass=f=2600:width_type=o:w=2.2,afade=t=in:d=0.18,afade=t=out:st=0.25:d=0.35",
    # marcador sobre papel: ruido agudo con un leve trémolo
    "marker": "anoisesrc=d=0.42:c=white:a=0.5,bandpass=f=4200:width_type=o:w=1.4,tremolo=f=22:d=0.55,afade=t=in:d=0.04,afade=t=out:st=0.3:d=0.12",
    # carta deslizándose y pegando
    "card": "anoisesrc=d=0.22:c=pink:a=0.8,highpass=f=1200,lowpass=f=9000,afade=t=in:d=0.08,afade=t=out:st=0.1:d=0.12:curve=exp",
    # tic del contador
    "tick": "aevalsrc='0.6*sin(2*PI*2100*t)*exp(-60*t)+0.4*sin(2*PI*3300*t)*exp(-80*t)':d=0.5:s=48000,"
            "apulsator=hz=10:amount=1:mode=square,afade=t=out:st=0.35:d=0.15",
}
COPY = {"pop": "pop.mp3", "click": "click.mp3", "chime": "chime.mp3"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    return r


def peak_db(path):
    r = run(["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"])
    m = re.search(r"max_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else 0.0


def make_sfx():
    for key, graph in SYNTH.items():
        raw = os.path.join(SFX_DIR, f"_{key}.wav")
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", graph, "-ac", "2", "-ar", str(SR), raw])
    for key, name in COPY.items():
        run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(BUNDLED, name), "-ac", "2", "-ar", str(SR),
             os.path.join(SFX_DIR, f"_{key}.wav")])
    # todos a pico -6 dBFS para que los volúmenes de los cues sean comparables
    for key in list(SYNTH) + list(COPY):
        raw = os.path.join(SFX_DIR, f"_{key}.wav")
        gain = -6.0 - peak_db(raw)
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"volume={gain:.2f}dB", os.path.join(SFX_DIR, f"{key}.wav")])
        os.remove(raw)


def mix():
    data = json.load(open(CUES))
    total, cues = data["total"], data["cues"]
    inputs = ["-i", os.path.join(ROOT, PROJ, "assets", "cut.mp4")]
    parts = [f"[0:a]aresample={SR},apad=whole_len={int(total * SR)},atrim=0:{total}[v]"]
    labels = ["[v]"]
    for i, c in enumerate(cues):
        inputs += ["-i", os.path.join(SFX_DIR, f"{c['key']}.wav")]
        ms = int(round(c["t"] * 1000))
        parts.append(f"[{i + 1}:a]adelay={ms}|{ms},volume={c['vol']}[s{i}]")
        labels.append(f"[s{i}]")
    parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,atrim=0:{total}[out]")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
         "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", OUT])
    print("master", OUT, "cues", len(cues), "peak", peak_db(OUT), "dB")


if __name__ == "__main__":
    make_sfx()
    mix()
