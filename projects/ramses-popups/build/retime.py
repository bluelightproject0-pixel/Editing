"""Re-alinea palabras que Whisper estiró sobre pausas (src 108-124 s), usando los arranques de energía
medidos a 30 ms. Reparte cada grupo de palabras dentro de su tramo con voz, en proporción a sus letras.
Uso: python3 build/retime.py   (reescribe transcript.clean.json)"""
import json

SPANS = [  # (primera palabra, n palabras, inicio, fin) — tramos con voz medidos en analysis/voice16k.wav
    ("y", 4, 108.16, 108.74),          # y de esta manera,
    ("por", 2, 111.30, 111.95),        # por ejemplo
    ("yo", 12, 117.51, 120.08),        # yo tengo una, ya si puedes mejorar la posibilidad de vivir una
    ("vida", 2, 122.85, 123.57),       # vida cómoda,
    ("para", 2, 123.60, 123.93),       # para todos
]
w = json.load(open("transcript.clean.json", encoding="utf-8"))
for first, n, a, b in SPANS:
    i = next(k for k, x in enumerate(w) if x["text"].lower().startswith(first) and a - 12 < x["start"] < b + 3
             and (first != "por" or w[k + 1]["text"].startswith("ejemplo")))
    grp = w[i:i + n]
    total = sum(len(x["text"]) for x in grp)
    t = a
    for x in grp:
        d = (b - a) * len(x["text"]) / total
        x["start"], x["end"] = round(t, 3), round(t + d, 3)
        t += d
    print(first, "->", " ".join(x["text"] for x in grp), a, b)
json.dump(w, open("transcript.clean.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
