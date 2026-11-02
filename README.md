# Editing: agente editor de video con taste

Workspace para que Claude Code edite videos como un editor senior. No arma la "edición promedio de
IA": decide el look con un **taste engine** y revisa su propio trabajo con un crítico antes de
mostrártelo.

## Qué hay instalado

Las skills están en `.claude/skills/` y Claude las carga solas al abrir el repo.

| Skill | Qué hace | Fuente | Licencia |
|---|---|---|---|
| `video-director` | El editor. Planea el corte, elige cómo aparece el speaker en cada beat y decide el look con el taste engine. Pasa por 3 checkpoints contigo y **aprende de tu feedback**. | [rsmed31/video-director-skill](https://github.com/rsmed31/video-director-skill) | MIT |
| `hyperframes` | Motor de render: HTML/GSAP → MP4 determinista. Cubre el contrato de composición, subtítulos, overlays, motion y look. | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Apache-2.0 |
| `hyperframes-cli` | Comandos `init`, `check`, `snapshot`, `preview`, `render`, `transcribe`, `beats`… | idem | Apache-2.0 |
| `hyperframes-registry` | Catálogo de efectos, transiciones, estilos de subtítulos y cards ya probados. | idem | Apache-2.0 |
| `media-use` | Música, SFX (trae una librería), voz, imágenes, gradación de color y mezcla de audio. | idem | Apache-2.0 |

Versiones vendorizadas: video-director `a0fac6b` (2026-10-22) y hyperframes `c14d92a` (2026-11-02).

### Dónde está el "taste"

La skill de taste más conocida es [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill),
pero es para **diseño web**, no para video. `video-director` adapta su método al video
(`.claude/skills/video-director/references/taste.md`):

1. **Dials 1–10.** `energy` es el ritmo de corte, `motion` el movimiento de cámara y overlays, y
   `density` cuánto hay en pantalla. Tus palabras los ajustan: "más calmado" o "más punchy". Se
   vuelven metas concretas que `plan_lint.py` verifica.
2. **Direcciones repartidas.** El agente no inventa un look (siempre caería en el default). El
   script reparte 3 de 12 direcciones investigadas y el agente elige la que mejor carga algo único
   del sujeto.
3. **Idea sentence.** "En este video, *[algo que solo tiene este sujeto]* se vuelve *[el recurso de
   la dirección]*". Tiene que pasar el *competitor test*: si también le sirve a la competencia, no
   vale.
4. **Tells prohibidos.** Whoosh en cada corte, subtítulos word-pop multicolor, emojis, punch-in en
   cada frase, ganchos tipo "¿Sabías que…?", stock genérico…
5. **Crítico con rúbrica.** Un subagente que no vio el plan puntúa hook, idea, ritmo, motion,
   legibilidad, sonido y final. Se corrigen los 3 peores problemas, en 3 rondas como máximo.

## Cómo usarlo

1. Crea una carpeta por video en `inputs/<job>/` (p. ej. `inputs/promo-cafe-nov/`) y pon ahí el
   footage, los logos y un `brief.md`. El brief es opcional, pero ayuda:

   ```markdown
   ---
   platform: instagram_reels   # instagram_reels | tiktok | youtube_shorts | youtube
   profile: talking_head_edu   # talking_head_story | product_promo | explainer_faceless | tutorial_screen | music_montage
   brand: mi-marca
   language: es
   goal: que guarden el video
   length: 30-45 s
   cta: Guárdalo
   keep: [el chiste del minuto 1]
   avoid: [la parte donde me equivoco]
   ---
   Lo que quieras contar en texto libre.
   ```

2. Pídele a Claude, por ejemplo: *"edita el video nuevo en inputs"* o *"haz un reel de 30 s de
   inputs/promo-cafe-nov"*.
3. Claude se detiene en tres checkpoints:
   - **A, plan:** la dirección elegida, la idea, la estructura y el costo de cualquier generación
     paga.
   - **K, fotogramas clave:** los stills del hook, de cada layout y del final, antes de renderizar.
   - **B, archivo final:** te entrega el video (`outputs/<job>/<job>-v1.mp4`, cover, `captions.srt`
     y `post.md`) y te pide feedback.
4. Dale feedback con tus palabras ("muy lento", "menos zooms", "siempre subtítulos abajo"). Se
   guarda como reglas en `.claude/skills/video-director/director.yaml`. **Haz commit de ese
   archivo** para que lo aprendido sobreviva entre sesiones.

### Marca

Pon el kit en `brands/<marca>/` (logo, fuentes, `brand.yaml` o guía en PDF), pásale la web de la
marca o descríbela en el chat. Se importa una vez y se reutiliza en todos los videos de ese cliente.

### Archivos de video

Video y audio están en `.gitignore` porque pesan demasiado para git. En sesiones en la nube, sube el
material a la sesión o pide que lo baje de Google Drive. Los MP4 finales se entregan directo o se
suben a Drive.

## Requisitos

- ffmpeg y ffprobe, Node 22+ y Python 3 con `pyyaml`.
- Opcional: `whisper-cli` para transcripción local, y
  [Playwright CLI](https://github.com/microsoft/playwright-cli) para sacar la marca de una web o
  grabar UI.
- La generación con IA (b-roll, imágenes) va por Higgsfield con **Nano Banana Pro** (imagen) y
  **Kling 3.0** (video). Seedance está prohibido por costo. Las reglas completas están en
  `CLAUDE.md`.

## Actualizar las skills

```bash
scripts/update-skills.sh
```

El script baja la última versión de ambos repos y conserva tu `director.yaml`. Revisa el diff y haz
commit.

**Nota de compatibilidad:** `video-director` todavía nombra skills de HyperFrames que se retiraron
en la v0.9 (`/general-video`, `/hyperframes-animation`, etc.). `CLAUDE.md` trae el mapa de a dónde
se movieron, así el agente no se pierde.

## Otras skills que encontré (no instaladas)

| Skill | Por qué no la instalé |
|---|---|
| [browser-use/video-use](https://github.com/browser-use/video-use) (MIT) | Muy buena para cortar footage crudo con varias tomas a partir de la transcripción. Se solapa con video-director y requiere una API key de ElevenLabs. Es buena alternativa si lo tuyo son entrevistas o tomas largas. |
| [nopefallacy/vertical-video-editing-skills](https://github.com/nopefallacy/vertical-video-editing-skills) (MIT) | Look editorial 9:16 muy marcado (serif + sans, papel). Tiene menos taste "decidido" y no aprende de tu feedback. |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | Skills oficiales de Remotion (React → video). Es otro motor; aquí ya usamos HyperFrames. |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT) | Es de diseño web. Su método ya está adaptado a video dentro de video-director. |
