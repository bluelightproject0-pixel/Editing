"""Genera la composición HyperFrames del job ramses-popups a partir del plan y la transcripción.

Uso (desde projects/ramses-popups):
    python3 build/build.py                 # versión completa  -> edit/
    VARIANT=short python3 build/build.py   # versión corta ~60 s -> edit-short/
Escribe <proyecto>/index.html, <proyecto>/compositions/*.html y build/sfx_cues[-short].json.

Todos los tiempos se calculan desde tiempos de la FUENTE con las duraciones reales de cada tramo del
corte maestro, así voz, pop ups y subtítulos quedan en sincronía exacta.
Ronda 2 (crítica v1): subtítulos siempre bajo la barbilla; split anclado a la barbilla; cara + título
completo en el cuadro 0; subtítulos en tira de papel sin desvanecidos encadenados; pop ups que salen
"volando" hacia su lugar en el tablero; tablero con texto >= 34 px y sin piezas cortadas; cierre de 2 s.
"""
import json
import os
import random
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANT = os.environ.get("VARIANT", "long")
SHORT = VARIANT == "short"
PROJ = "edit-short" if SHORT else "edit"
EDIT = os.path.join(ROOT, PROJ)
COMP = os.path.join(EDIT, "compositions")
SEGS = os.path.join(ROOT, "build", "segs-short" if SHORT else "segs")
CUES_OUT = os.path.join(ROOT, "build", "sfx_cues-short.json" if SHORT else "sfx_cues.json")
os.makedirs(COMP, exist_ok=True)

W, H = 1080, 1920
if SHORT:
    RANGES = [(0.00, 5.95), (12.75, 15.53), (34.72, 40.45), (42.05, 63.30), (93.80, 108.12), (122.75, 126.22), (133.45, 138.95)]
else:
    RANGES = [(0.00, 5.95), (12.75, 40.45), (42.05, 86.40), (93.85, 109.75), (111.25, 112.10), (117.32, 120.20), (122.75, 138.95)]


def seg_durs():
    out = []
    for i in range(len(RANGES)):
        d = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=duration",
                            "-of", "csv=p=0", os.path.join(SEGS, f"s{i}.mp4")], capture_output=True, text=True).stdout.strip()
        out.append(float(d))
    return out


DURS = seg_durs()
STARTS = [round(sum(DURS[:i]), 4) for i in range(len(DURS))]
VIDEO_END = round(sum(DURS), 3)
TOTAL = round(VIDEO_END + 2.0, 2)


def has(src):
    return any(a - 1e-6 <= src <= b + 0.05 for a, b in RANGES)


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
.dr { stroke-dasharray: 1; stroke-dashoffset: 1; }
"""


def ragged(seed, j=1.6, n=7):
    """clip-path con bordes de papel recortado a mano (determinista)."""
    r = random.Random(seed)
    pts = [(i * 100 / n, r.uniform(0, j)) for i in range(n + 1)]
    pts += [(100 - r.uniform(0, j), i * 100 / n) for i in range(1, n + 1)]
    pts += [(100 - i * 100 / n, 100 - r.uniform(0, j)) for i in range(1, n + 1)]
    pts += [(r.uniform(0, j), 100 - i * 100 / n) for i in range(1, n)]
    return "polygon(" + ", ".join(f"{x:.2f}% {y:.2f}%" for x, y in pts) + ")"


def torn(seed, depth=7, n=24):
    """Tira de papel rasgada arriba y abajo."""
    r = random.Random(seed)
    top = [(i * 100 / n, r.uniform(0, depth)) for i in range(n + 1)]
    bot = [(100 - i * 100 / n, 100 - r.uniform(0, depth)) for i in range(n + 1)]
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


SFX = []  # cues de sonido en tiempo de salida
HOSTS = []  # (name, start, dur, z, track)


def cue(key, t, vol):
    SFX.append({"key": key, "t": round(t, 3), "vol": vol})


def add_host(name, start, dur, z=30):
    HOSTS.append((name, round(start, 3), round(dur, 3), z, 2 + len(HOSTS)))


# ---------------------------------------------------------------- movimientos (JS)
def stick(sel, t, rot0=8, rot1=-2, dur=0.42):
    return (f'    tl.fromTo("{sel}", {{ opacity: 0, scale: 1.16, rotation: {rot0}, y: -18 }}, '
            f'{{ opacity: 1, scale: 1, rotation: {rot1}, y: 0, duration: {dur}, ease: "expo.out" }}, {t:.3f});\n')


def leave(sel, t, dur=0.22, stagger=0.04):
    return (f'    tl.to("{sel}", {{ opacity: 0, scale: 0.96, filter: "blur(6px)", duration: {dur}, ease: "power2.in", '
            f'stagger: {stagger} }}, {t:.3f});\n')


def pin_away(sel, t, dx, dy, rot=0, scale=0.8, dur=0.45):
    """Sale 'volando' hacia su lugar en el tablero (fuera de cuadro): la pieza se va a pegar, no se borra."""
    return (f'    tl.to("{sel}", {{ x: "+={dx}", y: "+={dy}", rotation: {rot}, scale: {scale}, duration: {dur}, '
            f'ease: "power3.in" }}, {t:.3f});\n')


def draw(sel, t, dur=0.45, ease="power1.inOut", stagger=0.0):
    return (f'    tl.fromTo("{sel}", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: {dur}, ease: "{ease}", '
            f'stagger: {stagger} }}, {t:.3f});\n')


def wipe(sel, t, dur=0.22):
    return (f'    tl.fromTo("{sel}", {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: {dur}, '
            f'ease: "power1.out" }}, {t:.3f});\n')


# Lugares en el tablero final (coordenadas del tablero, antes del pull-back). Al empezar el pull-back el
# tablero está a escala 2 alrededor de (540, 960): un punto p del tablero se ve en 540 + (p - 540) * 2.
def board_to_screen(x, y):
    return 540 + (x - 540) * 2, 960 + (y - 960) * 2


# ================================================================ escenas
def build_hook():
    body = f"""
    <div id="hook-l1" class="pc paper anton lbl" style="left:70px;top:250px;font-size:84px;clip-path:{ragged(11)};">El truco del súper</div>
    <div id="hook-l2" class="pc paper lbl" style="left:96px;top:366px;clip-path:{ragged(12)};display:flex;align-items:baseline;gap:18px;">
      <span class="serif" style="font-size:56px;font-style:italic;">que los</span>
      <span id="hook-fresas" class="marker red" style="font-size:96px;position:relative;">FRESAS
        <svg viewBox="0 0 300 30" style="position:absolute;left:-6px;bottom:-14px;width:300px;height:30px;">
          <path id="hook-u" class="dr" pathLength="1" d="M4 18 C90 8 200 10 296 14" fill="none" stroke="{RED}" stroke-width="8" stroke-linecap="round"/></svg>
      </span>
      <span class="serif" style="font-size:56px;font-style:italic;">no saben</span></div>
    <img id="hook-fresa" class="pc" src="assets/img/fresa.svg" style="left:846px;top:232px;width:180px;height:198px;" />
    <div id="hook-tape" class="tape" style="left:884px;top:222px;transform:rotate(-12deg);"></div>
"""
    # todo visible desde el cuadro 0; solo se dibuja el subrayado y la fresa se asienta
    js = '    tl.fromTo("#hook-fresa", { scale: 1.1, rotation: -12 }, { scale: 1, rotation: -7, duration: 0.35, ease: "expo.out" }, 0);\n'
    js += draw("#hook-u", 0.35, 0.3)
    js += leave("#hook-l1, #hook-l2", 3.45, 0.22, 0.05)
    tx, ty = board_to_screen(155, 360)
    js += pin_away("#hook-fresa, #hook-tape", 3.55, round(tx - 936), round(ty - 331), -8, 0.9, 0.42)
    scene("hook", body, "", js)
    add_host("hook", 0, 4.0, 30)
    cue("paper-slap", 0.02, 0.22)
    cue("marker", 0.35, 0.14)


def build_mama():
    t0 = o(16.92) - 0.05
    rancho = o(18.32) - t0
    dur = 3.5
    body = f"""
    <div id="mama-tag" class="pc paper lbl marker" style="left:520px;top:380px;font-size:50px;clip-path:{ragged(21)};">Mamá del rancho</div>
    <div class="tape" id="mama-tape" style="left:680px;top:362px;transform:rotate(6deg);"></div>
    <svg id="mama-hat" class="pc" viewBox="0 0 240 150" style="left:610px;top:256px;width:210px;height:131px;">
      <g fill="none" stroke="{RED}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">
        <path class="dr" pathLength="1" d="M10 92 C24 118 60 128 120 128 C180 128 216 118 230 92 C214 104 190 108 166 106"/>
        <path class="dr" pathLength="1" d="M74 106 C50 108 26 104 10 92"/>
        <path class="dr" pathLength="1" d="M70 104 C66 70 70 34 92 22 C104 16 112 30 120 30 C128 30 136 16 148 22 C170 34 174 70 170 104"/>
        <path class="dr" pathLength="1" d="M74 86 C104 94 136 94 166 86"/>
      </g></svg>
"""
    js = stick("#mama-tag", 0.0, 7, -4, 0.42)
    js += '    tl.fromTo("#mama-tape", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0.25);\n'
    js += draw("#mama-hat .dr", rancho - 0.12, 0.24, stagger=0.16)
    tx, ty = board_to_screen(430, 355)
    js += pin_away("#mama-tag, #mama-tape, #mama-hat", dur - 0.48, round(tx - 760), round(ty - 400), -3, 0.85)
    scene("mama", body, "", js)
    add_host("mama", t0, dur)
    cue("paper-slap", t0, 0.30)
    cue("marker", t0 + rancho - 0.1, 0.20)


def ransom(word_lines, seed, size_choices, x0, y0, line_h, gap=14, char_w=0.62):
    r = random.Random(seed)
    styles = [("#F7F4EC", INK), (INK, "#F7F4EC"), (COBALT, "#F7F4EC"), (RED, "#F7F4EC"), ("#F7F4EC", RED), ("#F5C400", INK)]
    out = []
    for li, line in enumerate(word_lines):
        x = x0[li] if isinstance(x0, (list, tuple)) else x0
        y = y0 + li * line_h
        for ch in line:
            if ch == " ":
                x += int(size_choices[0] * 0.38)
                continue
            bg, fg = styles[r.randrange(len(styles))]
            size = r.choice(size_choices)
            out.append((ch, x, y + r.randint(-6, 6), bg, fg, size, r.uniform(-7, 7), li))
            x += int(size * char_w) + gap
    return out


def build_truco():
    t0 = o(27.56) - 0.06
    super_t = o(28.30) - t0
    dur = 2.7
    letters = ransom(["TRUCO", "DEL SÚPER"], 31, [86, 92, 98, 104], [96, 150], 296, 122)
    body = ""
    for i, (ch, x, y, bg, fg, size, rot, li) in enumerate(letters):
        body += (f'    <div class="pc anton rl rl{li}" style="left:{x}px;top:{y}px;font-size:{size}px;background:{bg};color:{fg};'
                 f'padding:8px 12px 4px;clip-path:{ragged(100 + i, 3.5, 4)};transform:rotate({rot:.1f}deg);">{ch}</div>\n')
    js = ('    tl.fromTo("#truco .rl0", { opacity: 0, y: -26, scale: 1.25 }, '
          '{ opacity: 1, y: 0, scale: 1, duration: 0.24, ease: "power4.out", stagger: 0.05 }, 0.06);\n')
    js += (f'    tl.fromTo("#truco .rl1", {{ opacity: 0, y: -26, scale: 1.25 }}, '
           f'{{ opacity: 1, y: 0, scale: 1, duration: 0.24, ease: "power4.out", stagger: 0.045 }}, {super_t - 0.2:.3f});\n')
    tx, ty = board_to_screen(805, 345)
    js += pin_away("#truco .rl", dur - 0.5, round(tx - 470), round(ty - 400), 0, 0.7, 0.45)
    scene("truco", body, "", js)
    add_host("truco", t0, dur)
    cue("paper-slap", t0 + 0.06, 0.30)


def build_queso():
    t0 = o(36.0)
    dur = 2.75
    body = f"""
    <img id="q-still" class="pc" src="assets/img/cheese_36_bw.jpg" style="left:0;top:0;width:{W}px;height:{H}px;border:0 solid #FBF8F1;" />
    <div id="q-flash" class="pc" style="inset:0;background:#fff;opacity:0;"></div>
    <svg id="q-svg" class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
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
    js += draw("#q-c1", 0.18, 0.38)
    js += draw("#q-c2", 0.48, 0.34)
    js += stick("#q-emp", 0.36, -6, -3, 0.4)
    js += stick("#q-barra", 0.9, 6, 2, 0.4)
    js += draw("#q-arrow", 1.05, 0.28)
    js += draw("#q-head", 1.3, 0.16)
    # la foto congelada se vuelve la polaroid del tablero: se encoge y vuela a su lugar, abajo sigue el video
    js += f'    tl.to("#q-emp, #q-barra, #q-svg", {{ opacity: 0, duration: 0.14, ease: "power2.in" }}, {dur - 0.62:.3f});\n'
    tx, ty = board_to_screen(150, 655)
    js += (f'    tl.to("#q-still", {{ x: {round(tx - 540)}, y: {round(ty - 960)}, scale: 0.36, rotation: -6, borderWidth: 26, '
           f'duration: 0.5, ease: "power3.in" }}, {dur - 0.5:.3f});\n')
    scene("queso", body, "", js)
    add_host("queso", t0, dur, 25)
    cue("click", t0, 0.38)
    cue("marker", t0 + 0.18, 0.20)
    cue("marker", t0 + 1.05, 0.16)


def card(cid, x, y, suit, suit_color, title, title_color, mark, mark_color):
    return f"""
    <div id="{cid}" class="pc card" style="left:{x}px;top:{y}px;">
      <div class="corner tl" data-layout-allow-overlap data-layout-ignore><span class="anton" style="color:{suit_color}">A</span><span style="color:{suit_color}">{suit}</span></div>
      <div class="corner br" data-layout-allow-overlap data-layout-ignore><span class="anton" style="color:{suit_color}">A</span><span style="color:{suit_color}">{suit}</span></div>
      <div class="ct marker" style="color:{title_color}">{title}</div>
      <div class="cm marker" style="color:{mark_color}">{mark}</div>
    </div>"""


def build_cartas():
    t0 = o(46.30) - 0.05
    barra = o(49.60) - t0
    dur = round(o(51.54) + 0.5 - t0, 3)
    css = """
.card { width: 424px; height: 262px; border-radius: 20px; background: #FBF8F1 url("assets/img/paper_tile.png");
        border: 3px solid #121212; box-sizing: border-box; }
.card .corner { position: absolute; display: flex; flex-direction: column; align-items: center; font-size: 30px; line-height: 1.12; gap: 2px; }
.card .corner.tl { left: 14px; top: 10px; } .card .corner.br { right: 14px; bottom: 10px; transform: rotate(180deg); }
.card .ct { position: absolute; left: 0; right: 0; top: 60px; text-align: center; font-size: 48px; }
.card .cm { position: absolute; left: 0; right: 0; top: 130px; text-align: center; font-size: 72px; }
"""
    body = card("c-emp", 70, 292, "&#9830;", RED, "EMPAQUETADO", INK, "$$$", RED)
    body += card("c-barra", 588, 298, "&#9827;", COBALT, "LA BARRA", COBALT, "$", COBALT)
    body += f"""
    <svg id="c-svg" class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
      <g fill="none" stroke="{RED}" stroke-width="12" stroke-linecap="round">
        <path id="c-x1" class="dr" pathLength="1" d="M96 320 C220 400 350 480 486 540"/>
        <path id="c-x2" class="dr" pathLength="1" d="M478 306 C360 380 230 460 100 534"/>
      </g></svg>
"""
    js = '    tl.fromTo("#c-emp", { x: -560, rotation: -24 }, { x: 0, rotation: -6, duration: 0.55, ease: "expo.out" }, 0.0);\n'
    js += f'    tl.fromTo("#c-barra", {{ x: 560, rotation: 26 }}, {{ x: 0, rotation: 5, duration: 0.55, ease: "expo.out" }}, {barra - 0.05:.3f});\n'
    js += draw("#c-x1", barra + 0.38, 0.22)
    js += draw("#c-x2", barra + 0.58, 0.22)
    js += f'    tl.to("#c-emp", {{ opacity: 0.6, duration: 0.3, ease: "power2.out" }}, {barra + 0.6:.3f});\n'
    js += f'    tl.to("#c-barra", {{ scale: 1.08, duration: 0.5, ease: "expo.out" }}, {barra + 0.4:.3f});\n'
    # salen hacia la columna izquierda del tablero (donde quedan pegadas al final)
    js += pin_away("#c-emp, #c-svg", dur - 0.5, -640, 260, -14, 0.8, 0.45)
    js += pin_away("#c-barra", dur - 0.46, -1100, 300, -10, 0.8, 0.45)
    scene("cartas", body, css, js)
    add_host("cartas", t0, dur)
    cue("card", t0, 0.34)
    cue("card", t0 + barra - 0.05, 0.34)
    cue("marker", t0 + barra + 0.38, 0.20)


def build_chiste():
    t0 = o(58.49) - 0.05
    words = [("El", 58.49), ("chiste", 58.63), ("no", 58.99), ("es", 59.13), ("AHORRAR", 59.27), ("POR", 59.78), ("AHORRAR", 60.00)]
    dur = round(o(63.27) + 0.35 - t0, 3)
    l1 = " ".join(f'<span class="cw" id="cw{i}">{w}</span>' for i, (w, t) in enumerate(words[:4]))
    l2 = " ".join(f'<span class="cw" id="cw{i + 4}">{w}</span>' for i, (w, t) in enumerate(words[4:]))
    body = f"""
    <div id="ch-all" class="pc" style="left:0;top:0;width:{W}px;height:{H}px;">
      <div id="ch-strip" class="pc paper" style="left:70px;top:276px;width:940px;height:250px;clip-path:{torn(61)};"></div>
      <div class="pc marker" style="left:110px;top:306px;font-size:56px;white-space:nowrap;color:{INK};">{l1}</div>
      <div class="pc marker" style="left:110px;top:388px;font-size:66px;white-space:nowrap;color:{INK};">{l2}</div>
      <svg class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
        <path id="ch-u" class="dr" pathLength="1" d="M112 476 C330 466 600 472 900 460" fill="none" stroke="{RED}" stroke-width="10" stroke-linecap="round"/>
      </svg>
    </div>
"""
    css = ".cw { display: inline-block; }\n"
    js = stick("#ch-strip", 0.0, -3, -1.2, 0.4)
    for i, (w, t) in enumerate(words):
        js += wipe(f"#cw{i}", max(0.12, o(t) - t0), 0.2)
    js += draw("#ch-u", o(60.40) - t0, 0.45)
    js += pin_away("#ch-all", dur - 0.45, 0, -560, -2, 0.85, 0.42)
    scene("chiste", body, css, js)
    add_host("chiste", t0, dur)
    cue("marker", t0 + 0.1, 0.18)
    cue("marker", o(60.40), 0.16)


def build_pesos():
    """Split: la foto ya está encogida cuando la etiqueta se pega."""
    t0 = o(77.40) - 0.08
    dos = o(78.88) - t0
    inv = o(83.20) - t0
    lib = o(83.75) - t0
    dur = round(o(85.85) - t0, 3)
    body = f"""
    <div id="p-tag" class="pc" style="left:96px;top:300px;width:452px;height:300px;">
      <div class="paper" style="position:absolute;inset:0;clip-path:{ragged(71, 1.2)};"></div>
      <div style="position:absolute;left:0;right:0;top:0;height:64px;background:{RED};clip-path:{ragged(72, 1.0)};"></div>
      <div class="anton" style="position:absolute;left:0;right:0;top:12px;text-align:center;color:#F7F4EC;font-size:40px;">Ahorro en el súper</div>
      <div id="p-num" class="anton" style="position:absolute;left:0;right:0;top:86px;text-align:center;color:{INK};font-size:128px;">$1,000</div>
      <div id="p-extra" class="marker" style="position:absolute;right:28px;bottom:14px;font-size:46px;color:{RED_TXT};">extra</div>
    </div>
    <img id="p-libros" class="pc" src="assets/img/libros.svg" style="left:650px;top:352px;width:330px;height:252px;" />
    <div id="p-lbl" class="pc paper anton lbl cobalt" style="left:690px;top:600px;font-size:48px;clip-path:{ragged(73)};">Libros</div>
    <svg id="p-svg" class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
      <g fill="none" stroke="{RED}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round">
        <path id="p-arrow" class="dr" pathLength="1" d="M540 452 C580 402 610 400 640 434"/>
        <path id="p-head" class="dr" pathLength="1" d="M612 434 L644 438 L640 406"/>
      </g></svg>
"""
    js = stick("#p-tag", 0.0, -8, -3, 0.45)
    js += ('    const num = { v: 1000 };\n'
           '    const fmt = () => { document.querySelector("#p-num").textContent = "$" + Math.round(num.v).toLocaleString("en-US"); };\n'
           f'    tl.fromTo(num, {{ v: 1000 }}, {{ v: 2000, duration: 0.55, ease: "power2.out", onUpdate: fmt }}, {dos:.3f});\n')
    js += wipe("#p-extra", dos + 0.45, 0.25)
    js += draw("#p-arrow", inv, 0.3)
    js += draw("#p-head", inv + 0.28, 0.14)
    js += stick("#p-libros", lib, 10, 3, 0.45)
    js += stick("#p-lbl", lib + 0.22, -6, -2, 0.36)
    js += pin_away("#p-tag", dur - 0.5, 900, -200, 4, 0.7, 0.45)
    js += pin_away("#p-libros, #p-lbl, #p-svg", dur - 0.46, 700, 0, -5, 0.7, 0.45)
    scene("pesos", body, "", js)
    add_host("pesos", t0, dur)
    cue("tick", t0 + dos, 0.20)
    cue("paper-slap", t0, 0.28)
    cue("paper-slap", t0 + lib, 0.30)
    return t0, round(t0 + dur, 3)


def build_ia(end_src, bubble_until=None):
    t0 = o(97.12) - 0.08
    names = [("Claude", 99.01, 120, 470, -5), ("ChatGPT", 99.89, 700, 462, 4), ("Gemini", 101.37, 190, 600, 3), ("Grok", 102.09, 720, 598, -4)]
    bro = o(104.12) - t0
    dur = round((bubble_until if bubble_until else o(end_src)) - t0, 3)
    hub_x, hub_y = 540, 346
    body = f"""
    <div id="ia-net" class="pc" style="left:0;top:0;width:{W}px;height:{H}px;">
      <div id="ia-hub" class="pc paper anton lbl" style="left:{hub_x - 290}px;top:{hub_y - 48}px;width:580px;text-align:center;font-size:76px;clip-path:{ragged(81)};">Automatización</div>
      <svg class="pc" viewBox="0 0 {W} {H}" style="left:0;top:0;width:{W}px;height:{H}px;">
        <g fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round">
"""
    for i, (n, t, x, y, rot) in enumerate(names):
        cx, cy = x + 120, y + 30
        body += f'          <path id="ia-l{i}" class="dr" pathLength="1" d="M{hub_x} {hub_y + 50} Q{(hub_x + cx) / 2} {cy - 60} {cx} {cy - 10}"/>\n'
    body += "        </g></svg>\n"
    for i, (n, t, x, y, rot) in enumerate(names):
        body += (f'      <div id="ia-n{i}" class="pc paper marker lbl" style="left:{x}px;top:{y}px;font-size:58px;clip-path:{ragged(90 + i)};">{n}</div>\n'
                 f'      <div class="tape" id="ia-t{i}" style="left:{x + 60}px;top:{y - 18}px;transform:rotate({rot * 2}deg);width:96px;height:30px;"></div>\n')
    body += "    </div>\n"
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
        Oye bro, esto está <span style="color:{RED_TXT}">más barato</span> aquí</div>
    </div>
"""
    js = stick("#ia-hub", 0.0, -5, -1, 0.45)
    for i, (n, t, x, y, rot) in enumerate(names):
        tt = o(t) - t0
        js += draw(f"#ia-l{i}", tt - 0.12, 0.22)
        js += stick(f"#ia-n{i}", tt, rot * 2, rot, 0.38)
        js += f'    tl.fromTo("#ia-t{i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.08 }}, {tt + 0.18:.3f});\n'
    # el diagrama se va a pegar a la columna derecha del tablero; luego entra el globo
    js += pin_away("#ia-net", bro - 0.5, 760, 120, 3, 0.6, 0.45)
    js += (f'    tl.fromTo("#ia-bro", {{ opacity: 0, scale: 0.6, rotation: -6 }}, {{ opacity: 1, scale: 1, rotation: -2, duration: 0.5, '
           f'ease: "back.out(1.4)" }}, {bro:.3f});\n')
    js += leave("#ia-bro", dur - 0.3, 0.22, 0)
    scene("ia", body, "", js)
    add_host("ia", t0, dur)
    cue("paper-slap", t0, 0.28)
    cue("pop", o(99.01), 0.20)
    cue("paper-slap", t0 + bro, 0.30)
    return t0, round(t0 + dur, 3)


# ---------------------------------------------------------------- tablero final (pull-back)
BOARD_CSS = """
.mcard { width: 252px; height: 150px; border-radius: 12px; background: #FBF8F1 url("assets/img/paper_tile.png");
         border: 3px solid #121212; box-sizing: border-box; }
.mcard .ct { position: absolute; left: 22px; right: 4px; top: 34px; text-align: center; font-size: 34px; }
.mcard .cm { position: absolute; left: 0; right: 0; top: 78px; text-align: center; font-size: 46px; }
.mcard .corner { position: absolute; left: 9px; top: 5px; font-size: 22px; line-height: 1; display: flex; flex-direction: column; align-items: center; }
.mname { position: absolute; padding: 4px 12px 2px; font-size: 34px; white-space: nowrap; }
"""


def build_board(t_start, pans):
    nada = o(125.07) - t_start
    dios = o(138.27) - t_start
    dur = round(TOTAL - t_start, 3)
    has_mama, has_truco, has_pesos = has(16.92), has(27.56), has(77.40)
    has_ayudar = has(131.36)
    body = f'    <div id="bw" class="pc" style="left:0;top:0;width:{W}px;height:{H}px;">\n'
    body += f"""
      <img class="pc" src="assets/img/fresa.svg" style="left:70px;top:262px;width:170px;height:187px;transform:rotate(-8deg);" />
      <svg id="b-x" class="pc" viewBox="0 0 200 200" style="left:56px;top:262px;width:200px;height:200px;">
        <g fill="none" stroke="{RED}" stroke-width="14" stroke-linecap="round">
          <path class="dr" pathLength="1" d="M18 26 C70 80 130 140 182 182"/>
          <path class="dr" pathLength="1" d="M182 20 C130 76 70 136 20 186"/></g></svg>
"""
    if has_mama:
        body += f'      <div class="pc paper marker lbl" style="left:250px;top:304px;font-size:36px;padding:10px 18px 8px;transform:rotate(-3deg);clip-path:{ragged(201)};">Mamá del rancho</div>\n'
    if has_truco:
        letters = ransom(["TRUCO", "DEL SÚPER"], 97, [40, 44], [740, 700], 268, 60, gap=6, char_w=0.6)
        for i, (ch, x, y, bg, fg, size, rot, li) in enumerate(letters):
            body += (f'      <div class="pc anton" style="left:{x}px;top:{y}px;font-size:{size}px;background:{bg};color:{fg};padding:4px 6px 2px;'
                     f'transform:rotate({rot:.1f}deg);">{ch}</div>\n')
    body += f"""
      <div class="pc paper marker" style="left:236px;top:404px;width:608px;padding:12px 18px 10px;font-size:34px;line-height:1.1;text-align:center;transform:rotate(-2deg);clip-path:{torn(202, 6)};">
        El chiste no es<br/><span style="color:{RED_TXT}">ahorrar por ahorrar</span></div>
      <div class="pc" style="left:40px;top:528px;width:212px;padding:12px 12px 44px;background:#FBF8F1;transform:rotate(-6deg);">
        <img src="assets/img/cheese_36_bw.jpg" style="display:block;width:188px;height:220px;object-fit:cover;object-position:60% 52%;" />
        <svg viewBox="0 0 188 220" style="position:absolute;left:12px;top:12px;width:188px;height:220px;">
          <ellipse cx="132" cy="120" rx="34" ry="22" fill="none" stroke="{RED}" stroke-width="5"/></svg>
        <div class="marker" style="position:absolute;left:0;right:0;bottom:6px;text-align:center;font-size:30px;color:{RED_TXT};">empaquetado</div>
      </div>
      <div class="pc mcard" style="left:28px;top:856px;transform:rotate(8deg);">
        <div class="corner anton" data-layout-ignore style="color:{RED_TXT}">A<span>&#9830;</span></div>
        <div class="ct anton">Empaquetado</div><div class="cm marker" style="color:{RED_TXT}">$$$</div>
        <svg viewBox="0 0 252 150" style="position:absolute;inset:0;width:252px;height:150px;"><g stroke="{RED}" stroke-width="8" stroke-linecap="round">
          <path d="M14 18 L238 132"/><path d="M238 16 L16 134"/></g></svg>
      </div>
      <div class="pc mcard" style="left:34px;top:1018px;transform:rotate(-4deg);">
        <div class="corner anton" data-layout-ignore style="color:{COBALT}">A<span>&#9827;</span></div>
        <div class="ct anton cobalt">La barra</div><div class="cm marker cobalt">$</div>
      </div>
"""
    ry = 520
    if has_pesos:
        body += f"""
      <div class="pc paper" style="left:800px;top:{ry}px;width:180px;height:136px;transform:rotate(4deg);clip-path:{ragged(203, 1.2)};">
        <div style="height:28px;background:{RED};"></div>
        <div class="anton" style="text-align:center;font-size:54px;margin-top:6px;color:{INK};">$2,000</div>
        <div class="marker" style="text-align:right;margin-right:12px;font-size:30px;color:{RED_TXT};">extra</div>
      </div>
      <img class="pc" src="assets/img/libros.svg" style="left:798px;top:{ry + 152}px;width:184px;height:141px;transform:rotate(-5deg);" />
"""
        ry += 312
    body += f"""
      <div class="pc" style="left:796px;top:{ry}px;width:190px;height:290px;transform:rotate(3deg);">
        <div class="paper anton" style="position:absolute;left:-6px;top:0;width:200px;text-align:center;font-size:26px;letter-spacing:0;padding:9px 2px 7px;clip-path:{ragged(204)};" data-layout-ignore>Automatización</div>
        <div class="paper marker mname" style="left:0;top:58px;">Claude</div>
        <div class="paper marker mname" style="left:10px;top:114px;">ChatGPT</div>
        <div class="paper marker mname" style="left:0;top:170px;">Gemini</div>
        <div class="paper marker mname" style="left:30px;top:226px;">Grok</div>
      </div>
"""
    if has_ayudar:
        body += f"""
      <div id="b-nota" class="pc paper marker lbl" style="left:70px;top:1200px;font-size:38px;transform:rotate(-3deg);clip-path:{ragged(205)};">Ayudarnos entre nosotros</div>
      <div id="b-nota-t" class="tape" style="left:230px;top:1184px;transform:rotate(5deg);"></div>
"""
    body += f"""
      <div id="b-firma-p" class="pc paper" style="left:230px;top:1290px;width:640px;height:118px;transform:rotate(-3deg);clip-path:{torn(206)};"></div>
      <div id="b-firma" class="pc marker" style="left:270px;top:1306px;font-size:70px;color:{RED_TXT};transform:rotate(-3deg);white-space:nowrap;">Dios te bendiga.</div>
    </div>
"""
    js = '    tl.fromTo("#bw", { scale: 2, transformOrigin: "540px 960px" }, { scale: 1, duration: 1.2, ease: "power2.inOut" }, 0);\n'
    js += draw("#b-x .dr", nada + 0.25, 0.2, stagger=0.16)
    for (t, x, y, d) in pans:
        js += f'    tl.to("#bw", {{ x: {x}, y: {y}, duration: {d}, ease: "power2.inOut" }}, {t - t_start:.3f});\n'
    if has_ayudar:
        ayudar = o(131.36) - t_start
        js += stick("#b-nota", ayudar, -9, -3, 0.42)
        js += '    tl.fromTo("#b-nota-t", { opacity: 0 }, { opacity: 1, duration: 0.08 }, ' + f"{ayudar + 0.2:.3f});\n"
        cue("paper-slap", t_start + ayudar, 0.28)
    js += stick("#b-firma-p", dios - 0.25, -6, -3, 0.35)
    js += wipe("#b-firma", dios - 0.05, 0.9)
    scene("board", body, BOARD_CSS, js)
    add_host("board", t_start, dur, 30)
    cue("paper-slide", t_start, 0.30)
    cue("marker", t_start + nada + 0.25, 0.22)
    cue("chime", t_start + nada + 0.7, 0.22)
    cue("marker", t_start + dios - 0.05, 0.18)


# ================================================================ subtítulos
HIGHLIGHT = {"fresas", "fresa", "barra", "barato", "invertir", "libros", "automatización", "chiste", "ahorrar",
             "rancho", "huevo", "claude", "chatgpt", "gemini", "grok", "baratas", "cómoda", "éxito", "dinero"}


def build_captions(sign_t):
    words = json.load(open(os.path.join(ROOT, "transcript.clean.json"), encoding="utf-8"))
    ws = []
    for w in words:
        s = w["start"]
        for (a, b) in RANGES:
            if a - 0.02 <= s < b - 0.05:
                ws.append({"text": w["text"].replace("gemini", "Gemini"), "s": o(max(s, a)), "e": o(min(w["end"], b))})
                break
    ws = [w for w in ws if w["s"] < sign_t - 0.05]  # la firma final va escrita a mano
    groups, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        chars = sum(len(x["text"]) + 1 for x in cur)
        if (nxt is None or nxt["s"] - w["e"] >= 0.15 or w["text"][-1:] in ",.?!" or len(cur) >= 3 or
                chars + len(nxt["text"]) > 20):
            groups.append(cur)
            cur = []
    # grupos de menos de 0.5 s se funden con el anterior (si caben)
    merged = []
    for g in groups:
        d = g[-1]["e"] - g[0]["s"]
        if merged and d < 0.5 and g[0]["s"] - merged[-1][-1]["e"] < 0.3 and \
                sum(len(x["text"]) + 1 for x in merged[-1] + g) <= 26:
            merged[-1] = merged[-1] + g
        else:
            merged.append(g)
    groups = merged
    times = [[max(0.06, g[0]["s"] - 0.04), g[-1]["e"] + 0.25] for g in groups]
    for gi in range(len(times) - 1):
        times[gi][1] = min(times[gi][1], times[gi + 1][0])
    times[-1][1] = min(times[-1][1], TOTAL)
    body, js = "", ""
    for gi, g in enumerate(groups):
        s, e = times[gi]
        parts = []
        for w in g:
            core = w["text"].strip(",.?!¿¡").lower()
            t = w["text"].rstrip(",.")
            parts.append(f"<em>{t}</em>" if core in HIGHLIGHT else t)
        body += (f'    <div class="cg" id="cg{gi}"><span class="in paper" style="clip-path:{torn(500 + gi, 9, 10)};">'
                 f'{" ".join(parts)}</span></div>\n')
        prev_close = gi > 0 and s - times[gi - 1][1] < 0.3
        next_close = gi + 1 < len(times) and times[gi + 1][0] - e < 0.3
        js += f'    tl.set("#cg{gi}", {{ opacity: 1, visibility: "visible" }}, {s:.3f});\n'
        if not prev_close:
            js += f'    tl.fromTo("#cg{gi} .in", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.1, ease: "power2.out" }}, {s:.3f});\n'
        if not next_close:
            js += f'    tl.to("#cg{gi} .in", {{ opacity: 0, duration: 0.12, ease: "power2.in" }}, {e - 0.12:.3f});\n'
        js += f'    tl.set("#cg{gi}", {{ opacity: 0, visibility: "hidden" }}, {e:.3f});\n'
    css = f"""
.cg {{ position: absolute; left: 0; top: 1462px; width: 1080px; text-align: center; opacity: 0; visibility: hidden; overflow: visible; }}
.cg .in {{ display: inline-block; max-width: 900px; padding: 12px 30px 16px; color: #121212;
          font-family: "EB Garamond", serif; font-weight: 600; font-size: 58px; line-height: 1.08; }}
.cg em {{ font-style: italic; font-weight: 600; color: {RED_TXT}; }}
"""
    scene("captions", body, css, js)
    HOSTS.append(("captions", 0, TOTAL, 40, 1))
    return len(groups)


# ================================================================ raíz
FULL = {"scale": 1, "y": 0, "rotation": 0}
SPLIT = {"scale": 0.74, "y": 128, "rotation": -1.2}   # anclado a la barbilla: la barbilla queda en y ~1458
BOARD = {"scale": 0.5, "y": 0, "rotation": -2}


def state(st, dur, t, ease="power2.inOut"):
    return (f'    tl.to("#card", {{ scale: {st["scale"]}, y: {st["y"]}, rotation: {st["rotation"]}, duration: {dur}, '
            f'ease: "{ease}" }}, {t:.3f});')


def camera_js():
    """Punch-ins en #cam desde tiempos de fuente (se omiten los que caen fuera de la versión)."""
    k = [f'    tl.fromTo("#cam", {{ scale: 1 }}, {{ scale: 1.04, duration: 4.4, ease: "sine.inOut" }}, {o(1.40):.3f});']

    def add(fmt, src):
        if has(src):
            k.append(fmt(o(src)))

    for i in range(1, len(STARTS)):  # cada corte se tapa alternando encuadre
        k.append(f'    tl.set("#cam", {{ scale: {1.08 if i % 2 else 1.0} }}, {STARTS[i]:.3f});')
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.0, duration: 1.6, ease: "sine.inOut" }}, {t:.3f});', 21.0)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.04, duration: 3.4, ease: "sine.inOut" }}, {t + 1.0:.3f});', 27.56)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.16, duration: 0.6, ease: "power2.out" }}, {t - 0.5:.3f});', 32.82)
    add(lambda t: f'    tl.set("#cam", {{ scale: 1.0 }}, {t:.3f});', 33.92)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.16, duration: 0.6, ease: "power2.out" }}, {t:.3f});', 51.0)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.03, duration: 1.2, ease: "sine.inOut" }}, {t:.3f});', 52.8)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.09, duration: 0.6, ease: "power2.out" }}, {t:.3f});', 67.33)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.02, duration: 1.2, ease: "sine.inOut" }}, {t:.3f});', 69.0)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.09, duration: 0.6, ease: "power2.out" }}, {t:.3f});', 73.62)   # mucho queso
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.02, duration: 1.2, ease: "sine.inOut" }}, {t:.3f});', 75.3)
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.12, duration: 0.6, ease: "power2.out" }}, {t:.3f});', 104.12)  # oye bro
    add(lambda t: f'    tl.to("#cam", {{ scale: 1.03, duration: 1.2, ease: "sine.inOut" }}, {t:.3f});', 106.0)
    return "\n".join(k) + "\n"


def layout_js(splits, board_t, pans):
    L = ['    tl.set("#card", { transformOrigin: "50% 50%" }, 0);']
    for (a, b) in splits:
        L.append(state(SPLIT, 0.6, a))
        if b is not None:
            L.append(state(FULL, 0.7, b))
    L.append(f'    tl.set("#ground", {{ scale: 2, transformOrigin: "740px 1280px" }}, {board_t - 0.2:.3f});')
    L.append(f'    tl.to("#ground", {{ scale: 1, duration: 1.2, ease: "power2.inOut" }}, {board_t:.3f});')
    L.append(state(BOARD, 1.2, board_t))
    for (t, x, y, d) in pans:
        L.append(f'    tl.to("#world", {{ x: {x}, y: {y}, duration: {d}, ease: "power2.inOut" }}, {t:.3f});')
    return "\n".join(L) + "\n"


def build_root(splits, board_t, pans):
    hosts = ""
    for name, s, d, z, track in HOSTS:
        kind = "captions" if name == "captions" else "graphics"
        hosts += (f'      <div id="{name}" data-composition-id="{name}" data-composition-src="compositions/{name}.html" '
                  f'data-start="{s}" data-duration="{d}" data-track-index="{track}" data-track-kind="{kind}" '
                  f'data-width="{W}" data-height="{H}" style="z-index:{z};"></div>\n')
    open_end = o(1.40)
    html = f"""<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #121212; }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
      #world {{ position: absolute; inset: 0; z-index: 1; }}
      #ground {{ position: absolute; left: -200px; top: -320px; width: {W + 400}px; height: {H + 640}px; object-fit: cover; }}
      #card {{ position: absolute; inset: 0; }}
      #border {{ position: absolute; inset: -26px; background: #F7F4EC url("assets/img/paper_tile.png"); }}
      #layout {{ position: absolute; inset: 0; overflow: hidden; }}
      #cam {{ position: absolute; inset: 0; transform-origin: 50% 45%; }}
      #cam video, #cam img {{ position: absolute; inset: 0; width: {W}px; height: {H}px; object-fit: cover; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
      <div id="world">
        <img id="ground" class="clip" src="assets/img/paper_grid.jpg" data-start="0" data-duration="{TOTAL}" data-track-index="0" data-layout-allow-overflow />
        <div id="card">
          <div id="border"></div>
          <div id="layout">
            <div id="cam">
              <video id="take" class="clip" src="assets/cut.mp4" muted data-start="0" data-duration="{VIDEO_END}" data-track-index="1"></video>
              <img id="open" class="clip" src="assets/img/open.jpg" data-start="0" data-duration="{open_end}" data-track-index="2" />
              <img id="hold" class="clip" src="assets/img/last.jpg" data-start="{round(VIDEO_END - 0.04, 3)}" data-duration="{round(TOTAL - VIDEO_END + 0.04, 3)}" data-track-index="3" />
            </div>
          </div>
        </div>
      </div>
{hosts}      <audio id="master" src="assets/audio/master.wav" data-start="0" data-duration="{TOTAL}" data-track-index="20"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{camera_js()}{layout_js(splits, board_t, pans)}      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    with open(os.path.join(EDIT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    # cuadro de apertura: su cara (src 1.40) para que el cuadro 0 ya tenga cara + título
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.40", "-i", os.path.join(EDIT, "assets", "cut.mp4"), "-frames:v", "1",
                    "-q:v", "2", os.path.join(EDIT, "assets", "img", "open.jpg")], check=True)
    build_hook()
    if has(16.92):
        build_mama()
    if has(27.56):
        build_truco()
    build_queso()
    build_cartas()
    build_chiste()
    splits = []
    if has(77.40):
        p0, p1 = build_pesos()
        splits.append((p0 - 0.6, min(p1 - 0.1, STARTS[3] - 0.75)))
    board_t = o(123.13) - 0.12
    if SHORT:
        # la burbuja se queda hasta el corte y la foto pasa directo del split al tablero
        i0, i1 = build_ia(None, bubble_until=STARTS[5] - 0.05)
        splits.append((i0 - 0.6, None))
        pans = [(o(125.07) + 0.2, 30, 24, 1.0), (o(133.6), 0, 0, 1.6)]
    else:
        i0, i1 = build_ia(109.0)
        splits.append((i0 - 0.6, min(i1 - 0.1, STARTS[4] - 0.75)))
        pans = [(o(125.07) + 0.2, 30, 24, 1.0), (o(127.6), 0, 0, 2.0), (o(131.36) - 0.2, 24, -30, 1.1), (o(134.2), 0, 0, 2.0)]
    build_board(board_t, pans)
    n = build_captions(o(138.27))
    build_root(splits, board_t, pans)
    SFX.sort(key=lambda c: c["t"])
    json.dump({"total": TOTAL, "video_end": VIDEO_END, "cues": SFX}, open(CUES_OUT, "w"), indent=1)
    print(f"[{VARIANT}] total {TOTAL}s  video {VIDEO_END}s  hosts {len(HOSTS)}  caption groups {n}  sfx {len(SFX)}")
    print("splits", splits, "board", board_t)


if __name__ == "__main__":
    main()
