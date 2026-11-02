"""Genera la composición HyperFrames del job ramses-popups a partir del plan y la transcripción.

Uso (desde projects/ramses-popups):  python3 build/build.py
Escribe edit/index.html, edit/compositions/*.html y build/sfx_cues.json.
Todos los tiempos se calculan desde tiempos de la FUENTE con las duraciones reales de cada tramo del
corte maestro, para que voz, pop ups y subtítulos queden en sincronía exacta.
"""
import json
import os
import random
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDIT = os.path.join(ROOT, "edit")
COMP = os.path.join(EDIT, "compositions")
os.makedirs(COMP, exist_ok=True)

W, H = 1080, 1920
RANGES = [(0.00, 5.95), (12.75, 40.45), (42.05, 86.40), (93.85, 109.75), (111.25, 112.10), (117.32, 120.20), (122.75, 138.95)]


def seg_durs():
    out = []
    for i in range(len(RANGES)):
        p = os.path.join(ROOT, "build", "segs", f"s{i}.mp4")
        d = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=duration",
                            "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip()
        out.append(float(d))
    return out


DURS = seg_durs()
STARTS = [round(sum(DURS[:i]), 4) for i in range(len(DURS))]
VIDEO_END = round(sum(DURS), 3)
TOTAL = round(VIDEO_END + 0.8, 2)


def o(src):
    """Tiempo de fuente -> tiempo de salida."""
    for (a, b), s in zip(RANGES, STARTS):
        if a - 1e-6 <= src <= b + 0.05:
            return round(s + (src - a), 3)
    raise ValueError(f"src {src} cae en un tramo cortado")


# ---------------------------------------------------------------- estilo compartido
INK, RED, COBALT, PAPER, CREAM = "#121212", "#E3261C", "#2B3FE0", "#F1EEE6", "#F7F4EC"
RED_TXT = "#C61F17"  # rojo para texto chico sobre crema (contraste AA)

SHARED_CSS = """
@font-face { font-family: "Anton"; src: url("assets/fonts/Anton.woff2"); }
@font-face { font-family: "Permanent Marker"; src: url("assets/fonts/PermanentMarker.woff2"); }
.pc { position: absolute; }
.paper { background: #F7F4EC url("assets/img/paper_tile.png"); color: #121212; }
.anton { font-family: "Anton", sans-serif; text-transform: uppercase; line-height: 1; letter-spacing: 0.01em; }
.marker { font-family: "Permanent Marker", cursive; line-height: 1.05; }
.serif { font-family: "EB Garamond", serif; }
.lbl { padding: 16px 24px 12px; white-space: nowrap; }
.tape { position: absolute; width: 132px; height: 38px; background: rgba(233, 222, 190, 0.86); }
.red { color: #E3261C; }
.cobalt { color: #2B3FE0; }
svg { overflow: visible; }
"""


def ragged(seed, j=1.6, n=7):
    """clip-path con bordes de papel recortado a mano (determinista)."""
    r = random.Random(seed)
    pts = []
    for i in range(n + 1):
        pts.append((i * 100 / n, r.uniform(0, j)))
    for i in range(1, n + 1):
        pts.append((100 - r.uniform(0, j), i * 100 / n))
    for i in range(1, n + 1):
        pts.append((100 - i * 100 / n, 100 - r.uniform(0, j)))
    for i in range(1, n):
        pts.append((r.uniform(0, j), 100 - i * 100 / n))
    return "polygon(" + ", ".join(f"{x:.2f}% {y:.2f}%" for x, y in pts) + ")"


def torn(seed):
    """Tira de papel rasgada arriba y abajo."""
    r = random.Random(seed)
    top = [(i * 100 / 24, r.uniform(0, 7)) for i in range(25)]
    bot = [(100 - i * 100 / 24, 100 - r.uniform(0, 7)) for i in range(25)]
    return "polygon(" + ", ".join(f"{x:.2f}% {y:.2f}%" for x, y in top + bot) + ")"


def scene(name, body, css, js):
    html = f"""<template>
  <style>
{SHARED_CSS}
#{name} {{ position: absolute; inset: 0; }}
{css}
  </style>
  <div id="{name}" data-composition-id="{name}" data-width="{W}" data-height="{H}">
{body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{js}
    window.__timelines["{name}"] = tl;
  </script>
</template>
"""
    with open(os.path.join(COMP, f"{name}.html"), "w", encoding="utf-8") as f:
        f.write(html)


SFX = []  # (key, t_out, vol)


def cue(key, t, vol):
    SFX.append({"key": key, "t": round(t, 3), "vol": vol})


# arrival / exit helpers (JS)
def stick(sel, t, rot0=8, rot1=-2, dur=0.42):
    return (f'    tl.fromTo("{sel}", {{ opacity: 0, scale: 1.16, rotation: {rot0}, y: -18 }}, '
            f'{{ opacity: 1, scale: 1, rotation: {rot1}, y: 0, duration: {dur}, ease: "expo.out" }}, {t:.3f});\n')


def leave(sel, t, dur=0.22, stagger=0.04):
    return (f'    tl.to("{sel}", {{ opacity: 0, scale: 0.96, filter: "blur(6px)", duration: {dur}, ease: "power2.in", '
            f'stagger: {stagger} }}, {t:.3f});\n')


def draw(sel, t, dur=0.45, ease="power1.inOut"):
    return (f'    tl.fromTo("{sel}", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: {dur}, ease: "{ease}" }}, {t:.3f});\n')


def wipe(sel, t, dur=0.22, stagger=0.0):
    return (f'    tl.fromTo("{sel}", {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: {dur}, '
            f'ease: "power1.out", stagger: {stagger} }}, {t:.3f});\n')


DRAW_CSS = ".dr { stroke-dasharray: 1; stroke-dashoffset: 1; }\n"  # con pathLength="1"

# ================================================================ escenas
HOSTS = []  # (name, start, dur, z, track)


def add_host(name, start, dur, z=30, track=None):
    HOSTS.append((name, round(start, 3), round(dur, 3), z, track if track is not None else 2 + len(HOSTS)))


# ---------------------------------------------------------------- 1. hook (0 - 3.9)
def build_hook():
    face_in = o(1.35)
    fres = o(3.36)
    body = f"""
    <img id="hook-paper" class="pc" src="assets/img/paper_grid.jpg" style="left:0;top:0;width:{W}px;height:{H}px;" />
    <div id="hook-l1" class="pc paper anton lbl" style="left:84px;top:296px;font-size:80px;clip-path:{ragged(11)};">
      <span class="w">El</span> <span class="w">truco</span> <span class="w">del</span> <span class="w">súper</span></div>
    <div id="hook-l2" class="pc paper lbl" style="left:110px;top:410px;clip-path:{ragged(12)};display:flex;align-items:baseline;gap:18px;">
      <span id="hook-que" class="serif" style="font-size:54px;font-style:italic;">que los</span>
      <span id="hook-fresas" class="marker red" style="font-size:92px;">FRESAS</span>
      <span id="hook-nosaben" class="serif" style="font-size:54px;font-style:italic;">no saben</span></div>
    <img id="hook-fresa" class="pc" src="assets/img/fresa.svg" style="left:842px;top:282px;width:176px;height:194px;" />
    <div id="hook-tape" class="tape" style="left:880px;top:270px;transform:rotate(-12deg);"></div>
"""
    js = ""
    js += '    tl.fromTo("#hook-l1", { opacity: 0 }, { opacity: 1, duration: 0.05 }, 0.08);\n'
    js += ('    tl.fromTo("#hook-l1 .w", { opacity: 0, filter: "blur(6px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.13, '
           'ease: "power2.out", stagger: 0.07 }, 0.1);\n')
    js += stick("#hook-l2", 0.42, 6, -1.5, 0.38)
    js += wipe("#hook-fresas", 0.56, 0.32)
    js += stick("#hook-fresa", 0.78, 14, -7, 0.45)
    js += '    tl.fromTo("#hook-tape", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0.98);\n'
    # el papel sube y revela la cara
    js += (f'    tl.fromTo("#hook-paper", {{ y: 0 }}, {{ y: -{H}, duration: 0.6, ease: "power2.inOut" }}, {face_in - 0.1:.3f});\n')
    js += leave("#hook-l1, #hook-l2", 3.5, 0.22, 0.05)
    js += leave("#hook-fresa, #hook-tape", 3.62, 0.2, 0.0)
    scene("hook", body, "", js)
    add_host("hook", 0, 3.9, 30)
    cue("paper-slap", 0.08, 0.32)
    cue("pop", 0.78, 0.22)
    cue("paper-slide", face_in - 0.1, 0.30)
    return fres


# ---------------------------------------------------------------- 2. mamá del rancho
def build_mama():
    t0 = o(16.92) - 0.05
    rancho = o(18.32) - t0
    dur = 3.45
    body = f"""
    <div id="mama-tag" class="pc paper lbl marker" style="left:610px;top:376px;font-size:50px;clip-path:{ragged(21)};">
      Mamá del rancho</div>
    <div class="tape" id="mama-tape" style="left:760px;top:358px;transform:rotate(6deg);"></div>
    <svg id="mama-hat" class="pc" viewBox="0 0 240 150" style="left:700px;top:252px;width:210px;height:131px;">
      <g fill="none" stroke="{RED}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">
        <path class="dr" pathLength="1" d="M10 92 C24 118 60 128 120 128 C180 128 216 118 230 92 C214 104 190 108 166 106"/>
        <path class="dr" pathLength="1" d="M74 106 C50 108 26 104 10 92"/>
        <path class="dr" pathLength="1" d="M70 104 C66 70 70 34 92 22 C104 16 112 30 120 30 C128 30 136 16 148 22 C170 34 174 70 170 104"/>
        <path class="dr" pathLength="1" d="M74 86 C104 94 136 94 166 86"/>
      </g></svg>
"""
    js = stick("#mama-tag", 0.0, 7, -4, 0.42)
    js += '    tl.fromTo("#mama-tape", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0.25);\n'
    js += '    tl.set("#mama-hat", { opacity: 1 }, 0);\n'
    js += (f'    tl.fromTo("#mama-hat .dr", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 0.26, ease: "power1.inOut", '
           f'stagger: 0.18 }}, {rancho - 0.12:.3f});\n')
    js += leave("#mama-tag, #mama-tape, #mama-hat", dur - 0.3, 0.22, 0.03)
    scene("mama", body, DRAW_CSS, js)
    add_host("mama", t0, dur)
    cue("paper-slap", t0, 0.30)
    cue("marker", t0 + rancho - 0.1, 0.20)


# ---------------------------------------------------------------- 3. truco del súper (letras recortadas)
def build_truco():
    t0 = o(27.56) - 0.06
    super_t = o(28.30) - t0
    dur = 2.6
    r = random.Random(31)
    styles = [("#F7F4EC", INK), (INK, "#F7F4EC"), (COBALT, "#F7F4EC"), (RED, "#F7F4EC"), ("#F7F4EC", RED), ("#F5C400", INK)]
    letters = []
    x = 96
    for word, y, base in (("TRUCO", 300, 0), ("DEL", 420, 1), ("SÚPER", 420, 2)):
        if word == "SÚPER":
            x += 34
        if word == "DEL":
            x = 150
        for ch in word:
            bg, fg = styles[r.randrange(len(styles))]
            size = r.choice([86, 92, 98, 104])
            rot = r.uniform(-7, 7)
            letters.append((ch, x, y + r.randint(-8, 8), bg, fg, size, rot, base))
            x += int(size * 0.62) + 14
    body = ""
    for i, (ch, x, y, bg, fg, size, rot, base) in enumerate(letters):
        body += (f'    <div class="pc anton rl" data-g="{base}" style="left:{x}px;top:{y}px;font-size:{size}px;background:{bg};color:{fg};'
                 f'padding:8px 12px 4px;clip-path:{ragged(100 + i, 3.5, 4)};--r:{rot:.1f}deg;">{ch}</div>\n')
    js = ""
    js += ('    tl.fromTo("#truco .rl[data-g=\\"0\\"]", { opacity: 0, y: -26, scale: 1.25 }, '
           '{ opacity: 1, y: 0, scale: 1, duration: 0.24, ease: "power4.out", stagger: 0.05 }, 0.06);\n')
    js += (f'    tl.fromTo("#truco .rl[data-g=\\"1\\"], #truco .rl[data-g=\\"2\\"]", {{ opacity: 0, y: -26, scale: 1.25 }}, '
           f'{{ opacity: 1, y: 0, scale: 1, duration: 0.24, ease: "power4.out", stagger: 0.045 }}, {super_t - 0.2:.3f});\n')
    js += '    tl.set("#truco .rl", { rotation: (i, el) => parseFloat(el.style.getPropertyValue("--r")) }, 0);\n'
    js += leave("#truco .rl", dur - 0.4, 0.2, 0.015)
    scene("truco", body, "", js)
    add_host("truco", t0, dur)
    cue("paper-slap", t0 + 0.06, 0.30)


# ---------------------------------------------------------------- 4. congelado del queso (src 36.0)
def build_queso():
    t0 = o(36.0)
    dur = 2.7
    body = f"""
    <img id="q-still" class="pc" src="assets/img/cheese_36_bw.jpg" style="left:0;top:0;width:{W}px;height:{H}px;" data-layout-allow-overflow />
    <div id="q-flash" class="pc" style="inset:0;background:#fff;opacity:0;"></div>
    <svg class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
      <g fill="none" stroke="{RED}" stroke-width="9" stroke-linecap="round">
        <path id="q-c1" class="dr" pathLength="1" d="M930 975 C1030 970 1050 1050 1010 1100 C960 1150 840 1130 828 1062 C818 1000 880 972 950 980"/>
        <path id="q-c2" class="dr" pathLength="1" d="M486 858 C580 852 590 930 548 962 C500 990 404 972 400 920 C396 870 450 852 506 862"/>
      </g>
      <g fill="none" stroke="{COBALT}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round">
        <path id="q-arrow" class="dr" pathLength="1" d="M730 300 C740 250 742 210 735 168"/>
        <path id="q-head" class="dr" pathLength="1" d="M708 196 L735 160 L764 192"/>
      </g>
    </svg>
    <div id="q-emp" class="pc paper anton lbl red" style="left:96px;top:458px;font-size:64px;clip-path:{ragged(41)};">Empaquetado</div>
    <div id="q-barra" class="pc anton lbl" style="left:560px;top:304px;font-size:64px;background:{COBALT};color:#F7F4EC;clip-path:{ragged(42)};">La barra</div>
"""
    js = '    tl.fromTo("#q-flash", { opacity: 0.85 }, { opacity: 0, duration: 0.16, ease: "power2.out" }, 0);\n'
    js += '    tl.fromTo("#q-still", { scale: 1 }, { scale: 1.03, duration: 2.7, ease: "sine.inOut" }, 0);\n'
    js += draw("#q-c1", 0.18, 0.38)
    js += draw("#q-c2", 0.48, 0.34)
    js += stick("#q-emp", 0.36, -6, -3, 0.4)
    js += stick("#q-barra", 0.9, 6, 2, 0.4)
    js += draw("#q-arrow", 1.05, 0.28)
    js += draw("#q-head", 1.3, 0.16)
    js += leave("#q-emp, #q-barra", dur - 0.32, 0.2, 0.03)
    js += '    tl.to("#queso svg", { opacity: 0, duration: 0.2, ease: "power2.in" }, ' + f"{dur - 0.3:.3f});\n"
    scene("queso", body, DRAW_CSS, js)
    add_host("queso", t0, dur, 25)
    cue("click", t0, 0.38)
    cue("marker", t0 + 0.18, 0.20)
    cue("marker", t0 + 1.05, 0.16)


# ---------------------------------------------------------------- 5. cartas: empaquetado vs la barra
def card(cid, x, y, rot, suit, suit_color, title, title_color, mark, mark_color, seed):
    return f"""
    <div id="{cid}" class="pc card" style="left:{x}px;top:{y}px;--rot:{rot}deg;">
      <div class="corner tl" data-layout-allow-overlap data-layout-ignore><span class="anton" style="color:{suit_color}">A</span><span style="color:{suit_color}">{suit}</span></div>
      <div class="corner br" data-layout-allow-overlap data-layout-ignore><span class="anton" style="color:{suit_color}">A</span><span style="color:{suit_color}">{suit}</span></div>
      <div class="ct marker" style="color:{title_color}">{title}</div>
      <div class="cm marker" style="color:{mark_color}">{mark}</div>
    </div>"""


def build_cartas():
    t0 = o(46.30) - 0.05
    barra = o(49.60) - t0
    dur = round(o(51.54) + 0.25 - t0, 3)
    css = """
.card { width: 424px; height: 262px; border-radius: 20px; background: #FBF8F1 url("assets/img/paper_tile.png");
        border: 3px solid #121212; box-sizing: border-box; }
.card .corner { position: absolute; display: flex; flex-direction: column; align-items: center; font-size: 30px; line-height: 1.12; gap: 2px; }
.card .corner.tl { left: 14px; top: 10px; } .card .corner.br { right: 14px; bottom: 10px; transform: rotate(180deg); }
.card .ct { position: absolute; left: 0; right: 0; top: 60px; text-align: center; font-size: 48px; }
.card .cm { position: absolute; left: 0; right: 0; top: 130px; text-align: center; font-size: 72px; }
""" + DRAW_CSS
    body = card("c-emp", 70, 292, -6, "&#9830;", RED, "EMPAQUETADO", INK, "$$$", RED, 51)
    body += card("c-barra", 588, 298, 5, "&#9827;", COBALT, "LA BARRA", COBALT, "$", COBALT, 52)
    body += f"""
    <svg class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
      <g fill="none" stroke="{RED}" stroke-width="12" stroke-linecap="round">
        <path id="c-x1" class="dr" pathLength="1" d="M96 320 C220 400 350 480 486 540"/>
        <path id="c-x2" class="dr" pathLength="1" d="M478 306 C360 380 230 460 100 534"/>
      </g></svg>
"""
    js = ('    tl.fromTo("#c-emp", { x: -560, rotation: -24, opacity: 1 }, { x: 0, rotation: -6, duration: 0.55, ease: "expo.out" }, 0.0);\n')
    js += (f'    tl.fromTo("#c-barra", {{ x: 560, rotation: 26, opacity: 1 }}, {{ x: 0, rotation: 5, duration: 0.55, ease: "expo.out" }}, {barra - 0.05:.3f});\n')
    js += draw("#c-x1", barra + 0.38, 0.22)
    js += draw("#c-x2", barra + 0.58, 0.22)
    js += f'    tl.to("#c-emp", {{ opacity: 0.55, duration: 0.3, ease: "power2.out" }}, {barra + 0.6:.3f});\n'
    js += f'    tl.to("#c-barra", {{ scale: 1.08, duration: 0.5, ease: "expo.out" }}, {barra + 0.4:.3f});\n'
    js += (f'    tl.to("#c-emp", {{ x: -560, rotation: -20, duration: 0.3, ease: "power3.in" }}, {dur - 0.32:.3f});\n'
           f'    tl.to("#c-barra", {{ x: 560, rotation: 20, duration: 0.3, ease: "power3.in" }}, {dur - 0.3:.3f});\n')
    js += f'    tl.to("#cartas svg", {{ opacity: 0, duration: 0.15 }}, {dur - 0.32:.3f});\n'
    scene("cartas", body, css, js)
    add_host("cartas", t0, dur)
    cue("card", t0, 0.34)
    cue("card", t0 + barra - 0.05, 0.34)
    cue("marker", t0 + barra + 0.38, 0.20)


# ---------------------------------------------------------------- 6. el chiste no es ahorrar por ahorrar
def build_chiste():
    t0 = o(58.49) - 0.05
    words = [("El", 58.49), ("chiste", 58.63), ("no", 58.99), ("es", 59.13), ("AHORRAR", 59.27), ("POR", 59.78), ("AHORRAR", 60.00)]
    end = o(63.27) + 0.3
    dur = round(end - t0, 3)
    l1 = " ".join(f'<span class="cw" id="cw{i}">{w}</span>' for i, (w, t) in enumerate(words[:4]))
    l2 = " ".join(f'<span class="cw" id="cw{i + 4}">{w}</span>' for i, (w, t) in enumerate(words[4:]))
    body = f"""
    <div id="ch-strip" class="pc paper" style="left:70px;top:292px;width:940px;height:250px;clip-path:{torn(61)};"></div>
    <div id="ch-l1" class="pc marker" style="left:110px;top:322px;font-size:56px;white-space:nowrap;color:{INK};">{l1}</div>
    <div id="ch-l2" class="pc marker" style="left:110px;top:404px;font-size:66px;white-space:nowrap;color:{INK};">{l2}</div>
    <svg id="ch-svg" class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
      <path id="ch-u" class="dr" pathLength="1" d="M112 492 C330 482 600 488 900 476" fill="none" stroke="{RED}" stroke-width="10" stroke-linecap="round"/>
    </svg>
"""
    css = ".cw { display: inline-block; }\n" + DRAW_CSS
    js = stick("#ch-strip", 0.0, -3, -1.2, 0.4)
    for i, (w, t) in enumerate(words):
        js += wipe(f"#cw{i}", max(0.12, o(t) - t0), 0.2)
    js += draw("#ch-u", o(60.40) - t0, 0.45)
    js += leave("#ch-strip, #ch-l1, #ch-l2, #ch-svg", dur - 0.3, 0.22, 0.02)
    scene("chiste", body, css, js)
    add_host("chiste", t0, dur)
    cue("marker", t0 + 0.1, 0.18)
    cue("marker", o(60.40), 0.16)


# ---------------------------------------------------------------- 7. pesos -> libros (split)
def build_pesos():
    t0 = o(77.40) - 0.08
    dos = o(78.88) - t0
    inv = o(83.20) - t0
    lib = o(83.75) - t0
    end = o(86.30)
    dur = round(end - t0, 3)
    body = f"""
    <div id="p-tag" class="pc" style="left:96px;top:318px;width:452px;height:300px;">
      <div class="paper" style="position:absolute;inset:0;clip-path:{ragged(71, 1.2)};"></div>
      <div style="position:absolute;left:0;right:0;top:0;height:64px;background:{RED};clip-path:{ragged(72, 1.0)};"></div>
      <div class="anton" style="position:absolute;left:0;right:0;top:12px;text-align:center;color:#F7F4EC;font-size:40px;">Ahorro en el súper</div>
      <div id="p-num" class="anton" style="position:absolute;left:0;right:0;top:86px;text-align:center;color:{INK};font-size:128px;">$0</div>
      <div id="p-extra" class="marker red" style="position:absolute;right:28px;bottom:14px;font-size:46px;">extra</div>
      <div style="position:absolute;left:30px;top:-8px;width:28px;height:28px;border-radius:50%;background:#d9d2c0;"></div>
    </div>
    <img id="p-libros" class="pc" src="assets/img/libros.svg" style="left:650px;top:370px;width:330px;height:252px;" />
    <div id="p-lbl" class="pc paper anton lbl cobalt" style="left:690px;top:620px;font-size:48px;clip-path:{ragged(73)};">Libros</div>
    <svg class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
      <g fill="none" stroke="{RED}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round">
        <path id="p-arrow" class="dr" pathLength="1" d="M540 470 C580 420 610 418 640 452"/>
        <path id="p-head" class="dr" pathLength="1" d="M612 452 L644 456 L640 424"/>
      </g></svg>
"""
    js = stick("#p-tag", 0.0, -8, -3, 0.45)
    js += ('    const num = { v: 0 };\n'
           '    const fmt = () => { document.querySelector("#p-num").textContent = "$" + Math.round(num.v).toLocaleString("en-US"); };\n'
           f'    tl.fromTo(num, {{ v: 0 }}, {{ v: 1000, duration: 0.6, ease: "power2.out", onUpdate: fmt }}, 0.1);\n'
           f'    tl.fromTo(num, {{ v: 1000 }}, {{ v: 2000, duration: 0.55, ease: "power2.out", onUpdate: fmt, immediateRender: false }}, {dos:.3f});\n')
    js += wipe("#p-extra", dos + 0.45, 0.25)
    js += draw("#p-arrow", inv, 0.3)
    js += draw("#p-head", inv + 0.28, 0.14)
    js += stick("#p-libros", lib, 10, 3, 0.45)
    js += stick("#p-lbl", lib + 0.22, -6, -2, 0.36)
    js += leave("#pesos > *", dur - 0.32, 0.22, 0.02)
    scene("pesos", body, DRAW_CSS, js)
    add_host("pesos", t0, dur)
    cue("tick", t0 + 0.1, 0.20)
    cue("tick", t0 + dos, 0.20)
    cue("paper-slap", t0 + lib, 0.30)
    return t0, round(t0 + dur, 3)


# ---------------------------------------------------------------- 8. automatización (split) + globo "oye bro"
def build_ia():
    t0 = o(97.12) - 0.08
    names = [("Claude", 99.01, 120, 470, -5), ("ChatGPT", 99.89, 700, 462, 4), ("Gemini", 101.37, 190, 600, 3), ("Grok", 102.09, 720, 598, -4)]
    bro = o(104.12) - t0
    end = o(109.60)
    dur = round(end - t0, 3)
    hub_x, hub_y = 540, 346
    body = f"""
    <div id="ia-hub" class="pc paper anton lbl" style="left:{hub_x - 290}px;top:{hub_y - 48}px;width:580px;text-align:center;font-size:76px;clip-path:{ragged(81)};">Automatización</div>
    <svg class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
      <g fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round" stroke-dasharray="1" >
"""
    for i, (n, t, x, y, rot) in enumerate(names):
        cx, cy = x + 120, y + 30
        body += f'        <path id="ia-l{i}" class="dr" pathLength="1" d="M{hub_x} {hub_y + 50} Q{(hub_x + cx) / 2} {cy - 60} {cx} {cy - 10}"/>\n'
    body += "      </g></svg>\n"
    for i, (n, t, x, y, rot) in enumerate(names):
        body += (f'    <div id="ia-n{i}" class="pc paper marker lbl" style="left:{x}px;top:{y}px;font-size:58px;clip-path:{ragged(90 + i)};">{n}</div>\n'
                 f'    <div class="tape ia-t" id="ia-t{i}" style="left:{x + 60}px;top:{y - 18}px;transform:rotate({rot * 2}deg);width:96px;height:30px;"></div>\n')
    body += f"""
    <div id="ia-bro" class="pc" style="left:120px;top:330px;width:840px;height:400px;">
      <svg viewBox="0 0 840 400" style="position:absolute;inset:0;width:840px;height:400px;">
        <defs><pattern id="bd" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(25)">
          <rect width="14" height="14" fill="#F5C400"/><circle cx="7" cy="7" r="3.2" fill="#e0a800"/></pattern></defs>
        <path d="M60 30 L170 70 L250 6 L330 66 L440 10 L520 70 L640 18 L690 90 L800 80 L760 170 L830 250 L720 280 L740 380 L620 330 L520 394 L440 336 L320 392 L250 330 L120 372 L130 280 L20 250 L90 180 L10 110 L120 110 Z"
              fill="url(#bd)" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
        <path d="M150 90 C150 60 180 50 220 50 L640 50 C690 50 710 70 710 100 L710 250 C710 280 690 300 640 300 L360 300 L250 370 L280 300 L220 300 C180 300 150 280 150 250 Z"
              fill="#FBF8F1" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>
      </svg>
      <div class="marker" style="position:absolute;left:180px;top:86px;width:510px;text-align:center;font-size:48px;line-height:1.15;color:{INK};">
        Oye bro, esto está <span class="red">más barato</span> aquí</div>
    </div>
"""
    js = stick("#ia-hub", 0.0, -5, -1, 0.45)
    for i, (n, t, x, y, rot) in enumerate(names):
        tt = o(t) - t0
        js += draw(f"#ia-l{i}", tt - 0.12, 0.22)
        js += stick(f"#ia-n{i}", tt, rot * 2, rot, 0.38)
        js += f'    tl.fromTo("#ia-t{i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.08 }}, {tt + 0.18:.3f});\n'
    js += leave("#ia-hub, #ia > .pc[id^=ia-n], .ia-t", bro - 0.3, 0.2, 0.02)
    js += f'    tl.to("#ia > svg", {{ opacity: 0, duration: 0.2 }}, {bro - 0.3:.3f});\n'
    js += (f'    tl.fromTo("#ia-bro", {{ opacity: 0, scale: 0.6, rotation: -6 }}, {{ opacity: 1, scale: 1, rotation: -2, duration: 0.5, '
           f'ease: "back.out(1.4)" }}, {bro:.3f});\n')
    js += leave("#ia-bro", dur - 0.3, 0.22, 0)
    scene("ia", body, DRAW_CSS, js)
    add_host("ia", t0, dur)
    cue("paper-slap", t0, 0.28)
    cue("pop", o(99.01), 0.20)
    cue("paper-slap", t0 + bro, 0.30)
    return t0, round(t0 + dur, 3)


# ---------------------------------------------------------------- 9. tablero final (pull-back)
BOARD_PIECES_CSS = """
.card { width: 252px; height: 150px; border-radius: 12px; background: #FBF8F1 url("assets/img/paper_tile.png");
        border: 3px solid #121212; box-sizing: border-box; }
.card .ct { position: absolute; left: 0; right: 0; top: 34px; text-align: center; font-size: 28px; letter-spacing: -0.02em; }
.card .cm { position: absolute; left: 0; right: 0; top: 74px; text-align: center; font-size: 40px; }
.card .corner { position: absolute; left: 10px; top: 6px; font-size: 20px; line-height: .95; display: flex; flex-direction: column; align-items: center; }
"""


def build_board(t_start):
    nada = o(125.07) - t_start
    ayudar = o(131.36) - t_start
    dios = o(138.27) - t_start
    dur = round(TOTAL - t_start, 3)
    r = random.Random(97)
    mini = ""
    for i, ch in enumerate("TRUCO DEL SÚPER"):
        if ch == " ":
            continue
        bg, fg = [("#F7F4EC", INK), (INK, "#F7F4EC"), (COBALT, "#F7F4EC"), (RED, "#F7F4EC")][r.randrange(4)]
        mini += (f'<span class="anton" style="display:inline-block;background:{bg};color:{fg};font-size:40px;padding:4px 6px 2px;margin:2px;'
                 f'transform:rotate({r.uniform(-7, 7):.1f}deg);">{ch}</span>')
        if ch == "O" and i == 4:
            mini += "<br/>"
    body = f"""
    <div id="bw" class="pc" style="left:0;top:0;width:{W}px;height:{H}px;">
      <!-- arriba -->
      <img id="b-fresa" class="pc" src="assets/img/fresa.svg" style="left:84px;top:286px;width:170px;height:187px;transform:rotate(-8deg);" />
      <svg id="b-x" class="pc" viewBox="0 0 200 200" style="left:70px;top:290px;width:200px;height:200px;">
        <g fill="none" stroke="{RED}" stroke-width="14" stroke-linecap="round">
          <path class="dr" pathLength="1" d="M18 26 C70 80 130 140 182 182"/>
          <path class="dr" pathLength="1" d="M182 20 C130 76 70 136 20 186"/></g></svg>
      <div class="pc paper marker lbl" style="left:292px;top:330px;font-size:34px;transform:rotate(-3deg);clip-path:{ragged(201)};">Mamá del rancho</div>
      <div class="pc" style="left:648px;top:282px;width:370px;line-height:1;transform:rotate(3deg);">{mini}</div>
      <!-- tira del chiste sobre el borde de la foto -->
      <div class="pc paper marker" style="left:250px;top:418px;width:580px;padding:14px 20px 10px;font-size:30px;text-align:center;transform:rotate(-2deg);clip-path:{torn(202)};">
        El chiste no es <span class="red">ahorrar por ahorrar</span></div>
      <!-- izquierda -->
      <div class="pc" style="left:66px;top:520px;width:200px;padding:10px 10px 34px;background:#FBF8F1;transform:rotate(-6deg);">
        <img src="assets/img/cheese_36_bw.jpg" style="display:block;width:180px;height:220px;object-fit:cover;object-position:60% 52%;" />
        <svg viewBox="0 0 180 220" style="position:absolute;left:10px;top:10px;width:180px;height:220px;">
          <ellipse cx="128" cy="120" rx="34" ry="22" fill="none" stroke="{RED}" stroke-width="5"/></svg>
        <div class="marker" style="position:absolute;left:0;right:0;bottom:4px;text-align:center;font-size:28px;color:{RED_TXT};">empaquetado</div>
      </div>
      <div class="pc card" style="left:30px;top:842px;transform:rotate(8deg);">
        <div class="corner anton" data-layout-ignore style="color:{RED_TXT}">A<span>&#9830;</span></div>
        <div class="ct marker">EMPAQUETADO</div><div class="cm marker" style="color:{RED_TXT}">$$$</div>
        <svg viewBox="0 0 252 150" style="position:absolute;inset:0;width:252px;height:150px;"><g stroke="{RED}" stroke-width="8" stroke-linecap="round">
          <path d="M14 18 L238 132"/><path d="M238 16 L16 134"/></g></svg>
      </div>
      <div class="pc card" style="left:36px;top:1006px;transform:rotate(-4deg);">
        <div class="corner anton" data-layout-ignore style="color:{COBALT}">A<span>&#9827;</span></div>
        <div class="ct marker cobalt">LA BARRA</div><div class="cm marker cobalt">$</div>
      </div>
      <!-- derecha -->
      <div class="pc paper" style="left:826px;top:522px;width:190px;height:132px;transform:rotate(4deg);clip-path:{ragged(203, 1.2)};">
        <div style="height:30px;background:{RED};"></div>
        <div class="anton" style="text-align:center;font-size:56px;margin-top:6px;color:{INK};">$2,000</div>
        <div class="marker" style="text-align:right;margin-right:14px;font-size:28px;color:{RED_TXT};">extra</div>
      </div>
      <img class="pc" src="assets/img/libros.svg" style="left:822px;top:676px;width:196px;height:150px;transform:rotate(-5deg);" />
      <div class="pc" style="left:818px;top:852px;width:200px;height:286px;transform:rotate(3deg);">
        <div class="paper anton" style="position:absolute;left:4px;top:0;width:188px;text-align:center;font-size:27px;padding:8px 4px 6px;clip-path:{ragged(204)};">Automatización</div>
        <div class="paper marker" style="position:absolute;left:0;top:70px;font-size:28px;padding:6px 12px;">Claude</div>
        <div class="paper marker" style="position:absolute;right:0;top:118px;font-size:28px;padding:6px 12px;">ChatGPT</div>
        <div class="paper marker" style="position:absolute;left:8px;top:170px;font-size:28px;padding:6px 12px;">Gemini</div>
        <div class="paper marker" style="position:absolute;right:16px;top:222px;font-size:28px;padding:6px 12px;">Grok</div>
      </div>
      <!-- nota y firma -->
      <div id="b-nota" class="pc paper marker lbl" style="left:84px;top:1196px;font-size:36px;transform:rotate(-3deg);clip-path:{ragged(205)};">
        Ayudarnos entre nosotros</div>
      <div id="b-nota-t" class="tape" style="left:230px;top:1180px;transform:rotate(5deg);"></div>
      <div id="b-firma-p" class="pc paper" style="left:250px;top:1296px;width:640px;height:118px;transform:rotate(-3deg);clip-path:{torn(206)};"></div>
      <div id="b-firma" class="pc marker" style="left:290px;top:1312px;font-size:70px;color:{RED_TXT};transform:rotate(-3deg);white-space:nowrap;">Dios te bendiga.</div>
    </div>
"""
    js = '    tl.fromTo("#bw", { scale: 2, transformOrigin: "540px 960px" }, { scale: 1, duration: 1.2, ease: "power2.inOut" }, 0);\n'
    js += f'    tl.fromTo("#b-x .dr", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 0.2, ease: "power1.inOut", stagger: 0.16 }}, {nada + 0.25:.3f});\n'
    for k, (t, x, y, d) in enumerate(BOARD_PANS):
        js += f'    tl.to("#bw", {{ x: {x}, y: {y}, duration: {d}, ease: "power2.inOut" }}, {t - t_start:.3f});\n'
    js += stick("#b-nota", ayudar, -9, -3, 0.42)
    js += '    tl.fromTo("#b-nota-t", { opacity: 0 }, { opacity: 1, duration: 0.08 }, ' + f"{ayudar + 0.2:.3f});\n"
    js += stick("#b-firma-p", dios - 0.25, -6, -3, 0.35)
    js += wipe("#b-firma", dios - 0.05, 0.9)
    scene("board", body, DRAW_CSS + BOARD_PIECES_CSS, js)
    add_host("board", t_start, dur, 30)
    cue("paper-slide", t_start, 0.30)
    cue("marker", t_start + nada + 0.25, 0.22)
    cue("chime", t_start + nada + 0.7, 0.22)
    cue("paper-slap", t_start + ayudar, 0.28)
    cue("marker", t_start + dios - 0.05, 0.18)


# pans de cámara sobre el tablero: (t_out, x, y, dur) — misma cifra para #world (raíz) y #bw (escena)
BOARD_PANS = []


# ================================================================ subtítulos
HIGHLIGHT = {"fresas", "fresa", "barra", "barato", "barato,", "invertir", "libros", "automatización", "chiste", "ahorrar",
             "rancho", "huevo", "Claude", "ChatGPT", "Gemini", "Grok", "baratas", "cómoda", "éxito", "dinero"}


def layout_at(t, splits, board_t):
    for a, b in splits:
        if a <= t < b:
            return "split"
    if t >= board_t:
        return "board"
    return "full"


def build_captions(splits, board_t, sign_t):
    words = json.load(open(os.path.join(ROOT, "transcript.clean.json"), encoding="utf-8"))
    ws = []
    for w in words:
        s = w["start"]
        for (a, b) in RANGES:
            if a - 0.02 <= s < b - 0.05:
                txt = w["text"].replace("gemini", "Gemini")
                ws.append({"text": txt, "s": o(max(s, a)), "e": o(min(w["end"], b))})
                break
    # no subtitular la firma final (va escrita a mano)
    ws = [w for w in ws if w["s"] < sign_t - 0.05]
    groups, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        chars = sum(len(x["text"]) + 1 for x in cur)
        brk = (nxt is None or nxt["s"] - w["e"] >= 0.15 or w["text"][-1:] in ",.?!" or len(cur) >= 3 or
               chars + len(nxt["text"]) > 20)
        if brk:
            groups.append(cur)
            cur = []
    body, js = "", ""
    for gi, g in enumerate(groups):
        s = max(0.12, g[0]["s"] - 0.04)
        nxt_s = groups[gi + 1][0]["s"] - 0.04 if gi + 1 < len(groups) else TOTAL
        e = min(g[-1]["e"] + 0.25, nxt_s - 0.02)
        lay = layout_at(s, splits, board_t)
        y = {"full": 1462, "split": 792, "board": 1462}[lay]
        parts = []
        for w in g:
            core = w["text"].strip(",.?!¿¡").lower()
            t = w["text"].rstrip(",.")
            if core in {h.lower().strip(",") for h in HIGHLIGHT}:
                parts.append(f'<em>{t}</em>')
            else:
                parts.append(t)
        body += f'    <div class="cg" id="cg{gi}" style="top:{y}px;"><span class="in">{" ".join(parts)}</span></div>\n'
        js += (f'    tl.set("#cg{gi}", {{ opacity: 1, visibility: "visible" }}, {s:.3f});\n'
               f'    tl.fromTo("#cg{gi} .in", {{ opacity: 0, filter: "blur(5px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.12, ease: "power2.out" }}, {s:.3f});\n'
               f'    tl.to("#cg{gi} .in", {{ opacity: 0, duration: 0.1, ease: "power2.in" }}, {e - 0.1:.3f});\n'
               f'    tl.set("#cg{gi}", {{ opacity: 0, visibility: "hidden" }}, {e:.3f});\n')
    css = """
.cg { position: absolute; left: 0; width: 1080px; text-align: center; opacity: 0; visibility: hidden; overflow: visible; }
.cg .in { display: inline-block; max-width: 900px; padding: 6px 22px 10px; border-radius: 16px; background: rgba(18, 18, 18, 0.38);
          font-family: "EB Garamond", serif; font-weight: 600; font-size: 62px; line-height: 1.08; color: #FFFFFF; }
.cg em { font-style: italic; font-weight: 500; font-size: 1.1em; }
"""
    scene("captions", body, css, js)
    HOSTS.append(("captions", 0, TOTAL, 40, 1))
    return len(groups)


# ================================================================ raíz
def camera_js():
    """Punch-ins en #cam y cambios de layout en #layout, desde los tiempos de fuente."""
    k = []
    k.append(f'    tl.fromTo("#cam", {{ scale: 1 }}, {{ scale: 1.04, duration: 4.4, ease: "sine.inOut" }}, {o(1.35):.3f});')
    k.append(f'    tl.set("#cam", {{ scale: 1.10 }}, {STARTS[1]:.3f});')                       # corte c1->c2
    k.append(f'    tl.to("#cam", {{ scale: 1.0, duration: 1.6, ease: "sine.inOut" }}, {o(21.0):.3f});')
    k.append(f'    tl.to("#cam", {{ scale: 1.04, duration: 3.6, ease: "sine.inOut" }}, {o(27.56) + 1.0:.3f});')
    k.append(f'    tl.to("#cam", {{ scale: 1.16, duration: 0.6, ease: "power2.out" }}, {o(32.82) - 0.5:.3f});')  # ni un huevo
    k.append(f'    tl.set("#cam", {{ scale: 1.0 }}, {o(33.92):.3f});')                          # toma del queso
    k.append(f'    tl.set("#cam", {{ scale: 1.0 }}, {STARTS[2]:.3f});')
    k.append(f'    tl.to("#cam", {{ scale: 1.16, duration: 0.6, ease: "power2.out" }}, {o(51.0):.3f});')   # muchísimo más barato
    k.append(f'    tl.to("#cam", {{ scale: 1.03, duration: 1.2, ease: "sine.inOut" }}, {o(52.8):.3f});')
    k.append(f'    tl.to("#cam", {{ scale: 1.09, duration: 0.6, ease: "power2.out" }}, {o(67.33):.3f});')  # algo más
    k.append(f'    tl.to("#cam", {{ scale: 1.02, duration: 1.2, ease: "sine.inOut" }}, {o(69.0):.3f});')
    k.append(f'    tl.set("#cam", {{ scale: 1.08 }}, {STARTS[3]:.3f});')                       # corte c3->c4
    k.append(f'    tl.set("#cam", {{ scale: 1.0 }}, {STARTS[4]:.3f});')
    k.append(f'    tl.set("#cam", {{ scale: 1.08 }}, {STARTS[5]:.3f});')
    k.append(f'    tl.set("#cam", {{ scale: 1.0 }}, {STARTS[6]:.3f});')
    return "\n".join(k) + "\n"


def layout_js(p0, p1, i0, i1, board_t):
    SPLIT = 0.74
    L = []
    L.append('    tl.set("#layout", { transformOrigin: "50% 100%" }, 0);')
    for a, b, din, dout in ((p0 - 0.1, p1, 0.7, 0.7), (i0 - 0.15, i1, 0.8, 0.7)):
        L.append(f'    tl.to("#layout", {{ scale: {SPLIT}, rotation: -1.2, duration: {din}, ease: "power2.inOut" }}, {a:.3f});')
        L.append(f'    tl.to("#frame", {{ opacity: 1, duration: {din}, ease: "power2.inOut" }}, {a:.3f});')
        L.append(f'    tl.to("#layout", {{ scale: 1, rotation: 0, duration: {dout}, ease: "power2.inOut" }}, {b:.3f});')
        L.append(f'    tl.to("#frame", {{ opacity: 0, duration: {dout}, ease: "power2.inOut" }}, {b:.3f});')
    L.append(f'    tl.set("#layout", {{ transformOrigin: "50% 50%" }}, {board_t - 0.2:.3f});')
    L.append(f'    tl.set("#ground", {{ scale: 2, transformOrigin: "740px 1280px" }}, {board_t - 0.2:.3f});')
    L.append(f'    tl.to("#ground", {{ scale: 1, duration: 1.2, ease: "power2.inOut" }}, {board_t:.3f});')
    L.append(f'    tl.to("#layout", {{ scale: 0.5, rotation: -2, duration: 1.2, ease: "power2.inOut" }}, {board_t:.3f});')
    L.append(f'    tl.to("#frame", {{ opacity: 1, duration: 1.2, ease: "power2.inOut" }}, {board_t:.3f});')
    for (t, x, y, d) in BOARD_PANS:
        L.append(f'    tl.to("#world", {{ x: {x}, y: {y}, duration: {d}, ease: "power2.inOut" }}, {t:.3f});')
    return "\n".join(L) + "\n"


def build_root(p0, p1, i0, i1, board_t):
    hosts = ""
    for name, s, d, z, track in HOSTS:
        kind = "captions" if name == "captions" else "graphics"
        hosts += (f'      <div id="{name}" data-composition-id="{name}" data-composition-src="compositions/{name}.html" '
                  f'data-start="{s}" data-duration="{d}" data-track-index="{track}" data-track-kind="{kind}" '
                  f'data-width="{W}" data-height="{H}" style="z-index:{z};"></div>\n')
    html = f"""<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      :root {{ --paper: {PAPER}; --ink: {INK}; --red: {RED}; --cobalt: {COBALT}; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #121212; }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
      #world {{ position: absolute; inset: 0; z-index: 1; }}
      #ground {{ position: absolute; left: -200px; top: -320px; width: {W + 400}px; height: {H + 640}px; object-fit: cover; }}
      #layout {{ position: absolute; inset: 0; overflow: hidden; }}
      #cam {{ position: absolute; inset: 0; transform-origin: 50% 45%; }}
      #cam video, #cam img {{ position: absolute; inset: 0; width: {W}px; height: {H}px; object-fit: cover; }}
      #frame {{ position: absolute; inset: 0; border: 18px solid #F7F4EC; opacity: 0; pointer-events: none; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
      <div id="world">
        <img id="ground" class="clip" src="assets/img/paper_grid.jpg" data-start="0" data-duration="{TOTAL}" data-track-index="0" />
        <div id="layout">
          <div id="cam">
            <video id="take" class="clip" src="assets/cut.mp4" muted data-start="0" data-duration="{VIDEO_END}" data-track-index="1"></video>
            <img id="hold" class="clip" src="assets/img/last.jpg" data-start="{round(VIDEO_END - 0.04, 3)}" data-duration="{round(TOTAL - VIDEO_END + 0.04, 3)}" data-track-index="2" />
          </div>
          <div id="frame"></div>
        </div>
      </div>
{hosts}      <audio id="master" src="assets/audio/master.wav" data-start="0" data-duration="{TOTAL}" data-track-index="20"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{camera_js()}{layout_js(p0, p1, i0, i1, board_t)}      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    with open(os.path.join(EDIT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    global BOARD_PANS
    build_hook()
    build_mama()
    build_truco()
    build_queso()
    build_cartas()
    build_chiste()
    p0, p1 = build_pesos()
    i0, i1 = build_ia()
    board_t = o(123.13) - 0.12
    BOARD_PANS = [(o(125.07) + 0.2, 70, 46, 1.0), (o(127.6), 0, 0, 2.2), (o(131.36) - 0.2, 46, -70, 1.1), (o(134.2), 0, 0, 2.2)]
    build_board(board_t)
    n = build_captions([(p0 - 0.1, p1 + 0.35), (i0 - 0.15, i1 + 0.35)], board_t, o(138.27))
    build_root(p0, p1, i0, i1, board_t)
    SFX.sort(key=lambda c: c["t"])
    json.dump({"total": TOTAL, "video_end": VIDEO_END, "cues": SFX}, open(os.path.join(ROOT, "build", "sfx_cues.json"), "w"), indent=1)
    print(f"total {TOTAL}s  video {VIDEO_END}s  hosts {len(HOSTS)}  caption groups {n}  sfx {len(SFX)}")
    print("splits", (p0, p1), (i0, i1), "board", board_t)


if __name__ == "__main__":
    main()
