# Critique v1: ramses-popups (1:55, 1080x1920)

Independent critic, round 1. Judged from qa/k2 and qa/t2 frames. Root causes are traced to `build/build.py`, which generates `edit/`.

## 1. Rubric score (taste.md §6)

| Criterion | Wt | Score | Why |
|---|---|---|---|
| Hook (0-3 s) | 20% | **5** | The headline is good ("EL TRUCO DEL SÚPER / que los FRESAS no saben" plus the strawberry), but frame 0 is an empty procedural "paper" page with a grey caption pill. Only 3 words have built by 0.3 s, and his face does not appear until 1.5-1.9 s. Nothing in the first second would stop someone scrolling. |
| Idea | 15% | **6** | The idea sentence exists and passes the competitor test: his own board, the strawberry struck out live. But the board never grows on screen. Every piece blurs away (`leave()`), the paper behind the splits at 69-94 s is empty apart from the current graphic, and the bubble wipes the AI diagram. The collage appears only at 98 s, so it reads as a recap rather than a payoff. |
| Pacing | 15% | **5** | 61.85-68.87 s is a 7.0 s dead stretch (no graphic, no camera move). 15.8-20.7 s runs 4.9 s with no change (max_static 4.4). Between 6.0 and 10.1 s there is no change for 4.1 s (the first-15 s rule asks for one every 3 s). The video runs 1:55 against a 30-60 s profile target. |
| Motion | 15% | **5** | The morphs are eased and smooth, but: the cream `#frame` border fades in by opacity and shows as a dirty grey band mid-morph (69.1, 78.3, 81.4, 94.2). Hard cuts land inside moving cards (78.078, 93.994). Every piece and every caption exits or enters with the same blur dissolve. Captions jump instead of following the layout. No transition is snappier than the rules allow, so no cap. |
| Readability | 15% | **3 (capped)** | Captions cover his forehead and hair (see B1/B2), which triggers the cap. Without the cap it would be about 5: a grey pill on cream paper at about 2.8:1 contrast, board labels at 27-30 px, caption chunks of 0.26-0.35 s, and an uncaptioned spoken span. |
| Sound | 10% | **6** | The master has voice from 0 s with no per-second dropouts (RMS between -16 and -31 dBFS). Integrated -17.6 LUFS and true peak -0.5 dBFS before finalize, so finalize must limit to -1. There are 25 sparse SFX, all tied to actions, no whooshes. The "light bed" the direction asks for is missing. Not checked by ear, and no backtest yet. |
| Ending | 10% | **7** | The source ending is preserved, the handwritten "Dios te bendiga." works, and the strawberry callback lands. The sign-off finishes writing at about 114.1 s and holds only about 0.7 s. "aquí están mis gems" has no visual. |

**Weighted: 1.00 + 0.90 + 0.75 + 0.75 + 0.45 + 0.60 + 0.70 = 5.15 → 5.2 / 10** (Readability capped at 3). Not shippable.

## 2. Blocking issues

**B1. A caption sits across his forehead in full frame, 78.23-79.86 s.** The caption "te recomiendo que" sits on his eyebrows and hairline (frame t2/frame-36-at-78.7s.png).
- Root cause: `build_captions()` picks y once per group from `layout_at(group_start)`. `main()` pads both split windows (`p1 + 0.35`, `i1 + 0.35`). A group that starts at 78.23, inside the padded window, keeps `top:792px` after `layout_js()` has returned `#layout` to scale 1 (77.95 → 78.65). At scale 1, y 792 is the forehead. File: `edit/compositions/captions.html` `#cg92` (also `#cg91`).
- Fix: see Top 1. Do not choose caption y per group.

**B2. Captions on his hair and forehead during the split morphs.** This also breaks the user's "abajo de la barbilla" request for about 22 s.
- 69.25-69.6 "pesos extra" (`#cg80`), 81.31-81.9 "automatización con" (`#cg94`, frame-41-at-81.4s.png), 93.83-94.23 "de esta" (`#cg103`). The y jumps from 1462 to 792 in one frame while the card is still around 0.85-0.95 scale.
- In the stable splits (69.6-78.2 and 81.9-93.8), every caption sits **above** his head on the ceiling (`split: 792`). The client rule R-ramses-captions-chin and feedback fb-0002 both say under the chin. The plan's "documented exception" contradicts what the user answered.
- 69.0 s: the translucent "AHORRO EN EL SÚPER $0" tag covers the top of his head (frame-20-at-69s.png). `build_pesos()` sticks `#p-tag` at 68.97, but `layout_js()` only starts shrinking at 68.87 and takes 0.7 s, so the full-frame keepout (y ≥ 560) still applies there. The counter also shows "$0", which he never says.
- Fix: see Top 1. Also start the split morph 0.5 s before the pesos and IA graphics stick, so pieces only land on a card that has already shrunk.

**B3. "DELSÚPER" typo on the final board, 98-114.8 s** (the last 17 s, including the last frame).
- Root cause: in `build_board()`, the mini ransom loop runs `if ch == " ": continue` and inserts `<br/>` only after "TRUCO", so the space between DEL and SÚPER is lost.
- Fix: for the second space, emit a spacer such as `<span style="display:inline-block;width:20px"></span>`.

**B4. The finale's collage pieces are cut off at the frame edge.**
- 100.3-103 s: the "$2,000 EXTRA" tag's red bar and "ChatGPT" run off the right edge (frame-14-at-101s.png), and "Grok" drops into the right-rail zone (y about 1185). Root cause: `main()` sets `BOARD_PANS[0] = (…, 70, 46, 1.0)`, a +70 px x pan applied to both `#world` and `#bw`, and the right column in `build_board()` already sits at `left:826px; width:190px; rotate(4deg)`, ending at about 1020 px.
- 10.1-13.5 s: in `build_mama()`, `#mama-tag` at `left:610px` (50 px marker, about 470 px wide) runs to x about 1080, so "RANCHO" touches the frame edge (frame-02-at-11.8s.png).
- Fix: keep every board piece within x ≤ 1015 at the most extreme pan position. Either pull the right column to `left ≤ 760`, or replace the translate pan with a scale of about 1.08 around the strawberry (`transformOrigin` at the strawberry's position). Move `#mama-tag` to `left: 520px`.

**B5. Spoken words with no caption, then caption flashes, 94.23-96.12 s.**
- Root cause: in `transcript.clean.json`, w296-w306 have smeared timestamps ("manera," 110.66-113.76, "por ejemplo" 113.76-117.68). `build_captions()` keeps a word only when its start falls inside `RANGES`, so the kept span 111.25-112.10 has no words, and "manera" is dropped from "de esta". After that, `#cg104-#cg106` last 0.35, 0.29 and 0.26 s.
- Fix: re-align source 108-119 s (`whisper-cli -ml 1 -sow` on that window, or snap to the `cut_check.py` onsets). In `build_captions()`, merge any group shorter than 0.5 s into its neighbour.

**B6. Frame 0 is an empty page** (frame-00-at-0.3s.png). See Top 2.

## 3. Top 3 to fix first

1. **One caption line under the chin, in every layout (B1 and B2).** In `layout_js()`, anchor the split to the chin line instead of the bottom: `tl.set("#layout", { transformOrigin: "50% 1460px" })` in place of `"50% 100%"`. At scale 0.74 the chin then stays at about 1453, the face top moves to about 794, and the card spans y 380-1800. The card's bottom border becomes visible, so it finally reads as a pinned photo.

   Then, in `build_captions()`, drop the `"split": 792` branch and use y 1462 everywhere. Delete the `+0.35` padding in `main()`. All the current graphics bottoms (tag 618, libros label about 690, IA names about 660, bubble 730) stay above the new face top (about 794). Start each split morph 0.5 s before its graphic sticks.

   Re-snapshot 69.0-69.7, 78.0-80.0, 81.0-82.0 and 93.8-94.6.

2. **Hook: a face and a full title on frame 0, on real paper.** In `build_hook()`, set `#hook-l1`, `#hook-l2` and `#hook-fresa` visible at t=0: drop the 0.08 s fade and the blur stagger, and keep only the FRESAS wipe and the sticker slap as motion. Replace `#hook-paper` (an empty page for 1.35 s) with a full-frame still of his first good face frame (around source 1.4-1.6 s, the same approach as `q-still`). His face is then on screen from frame 0 and the live shot takes over at 1.35. If the paper reveal is kept, make it a torn strip that has slid away by 0.4 s.

   Also replace the ground. `assets.py facets()` produces Voronoi "low-poly" facets that read as generated wallpaper, not his pin-01 crumpled grid paper, and that ground is on screen for about 45 s (hook, both splits, board). Use `crumple()` plus the grid only, or a real scan of a crumpled grid sheet.

3. **Make the finale and the captions on cream legible (B3, B4).** In `build_captions()`, the `.cg .in` pill is `rgba(18,18,18,.38)`. On cream it turns into a grey pill at about 2.8:1 contrast (0-1.35 s and 98-114.8 s), and it is also off-plan: the plan asks for `style: paper_strip`, and the reference reels use no box.
   - Switch captions to an opaque cream torn strip: the `.paper` class plus a `torn()` clip, ink text, italic keyword. It reads on both the footage and the board.
   - Stop the chained 0.1 s fade-out and 0.12 s blur-in between back-to-back chunks. About 25% of frames currently catch a half-faded caption (1.3, 31.8, 52.6, 78.2, 94.2, 98.9 s). Cut directly when the gap is under 0.15 s.
   - In `build_board()`, raise the board labels from 27-30 px to 34 px or more. Give the chiste strip enough width that it does not wrap "por / AHORRAR".
   - Fix DELSÚPER and the edge clipping (B3, B4).
   - Extend the hold in `TOTAL = VIDEO_END + 0.8` to about 2.0 s, so "Dios te bendiga." stays fully written for at least 1.5 s.

Next after these:
- **The board doesn't grow (Idea).** In `build_mama/truco/cartas/chiste/pesos/ia`, replace the blur `leave()` with a "pin away" move: shrink to about 0.5 and drift toward the piece's board slot. Show the pieces earned so far, pinned in the paper margins, during the 69-94 s splits.
- **Dead stretch at 61.85-68.87 s (Pacing).** Add a beat in `camera_js()` or a small polaroid callback on "mucho queso y jamón".

## 4. Transitions

| Transition | Clean? | Frame-by-frame findings |
|---|---|---|
| Paper slide-up, 1.2-1.9 | Mostly | No flash or black edge, and the face is not cropped by text. The paper's bottom edge is ruler-straight with no shadow, so it reads as a wipe, not torn paper. The caption fades in as a grey ghost at 1.3. The "que los FRESAS no saben" strip (bottom about 545) touches the top of his hair at 1.7-3.5. |
| Freeze in, 29.1-29.5 | Yes | The B&W still matches the live 29.2 frame, so the hand does not jump. The `#q-flash` at 0.85 is barely visible. Labels arrive after 29.5. |
| Freeze out, 31.7-32.1 | Acceptable | 31.8: labels, circles and arrow are a half-opacity blur smear. 31.9: one bare B&W frame. 32.0: colour returns with the hand already in a V sign, because the live video kept running underneath. Cutting to colour on the frame the labels leave would be cleaner. |
| Split in, 68.8-69.7 | **No** | 69.0: translucent "$0" tag over his head. 69.1-69.2: grey half-faded border. 69.3: caption jumps from his chest to his hair. The counter races during the morph, so two motions compete. |
| Split out, 77.9-78.7 | **No** | 77.9-78.0: pieces blur out, leaving an empty card on blank paper. 78.078: a cut plus `set #cam 1.08` inside the growing card, so the face size jumps between 78.0 and 78.1. 78.3-78.4: grey border. 78.4 onward: caption on his forehead until 79.86. |
| Split in, 81.0-82.0 | **No** | The hub label over full-frame footage is fine. 81.31-81.9: the caption sits on his hair and forehead while the card is still around 0.9 scale. 81.4-81.5: grey border. The caption "automatización" repeats the hub label word for word. |
| Split out, 93.8-94.6 | **No** | 93.8: the bubble has left, leaving an empty card. 93.994: a cut inside the morph, then another cut plus a 1.08 punch at 94.861 (three events in 0.9 s). 94.2: "de esta" over his hair. 94.23-95.18: no caption while he talks. |
| Board pull-back, 98.0-99.3 | Mostly | The 2:1 board-to-card scale is consistent and the ground origin matches, with no black edges. Fragments are cropped at the frame edges mid-move, which is fine for a camera move. 98.9: the next caption ghosts in over the card's bottom edge as a low-contrast grey pill. After it lands: the 100.3-103 pan clips "$2,000", "DELSÚPER" is visible throughout, and the EMPAQUETADO card's "A♦" corner overlaps the "EM". |

## 5. Checklist

- [ ] **Faces never covered.** Fails at 78.23-79.86 (forehead), 69.25-69.6, 81.31-81.9 and 93.83-94.23 (hair), and 69.0 (tag over his head).
- [ ] **Text readable at phone size.** Main labels (48-128 px) are fine. Board labels are 27-30 px. The grey pill on cream is about 2.8:1. Chunks of 0.26-0.35 s are too short. Speech at 94.2-95.2 has no caption.
- [x] **Nothing important in the top 168 px.** Only the tip of the LA BARRA arrow reaches y about 160 (29.3-31.9), plus transient fragments during the pull-back.
- [~] **Nothing under the right rail (x > 850, y > 1150).** Captions top out at x of about 830. The board's "Grok" dips to y about 1185 during the 100.3-103 pan.
- [x] **Captions never over the mouth.** True, but they do go over the forehead and eyes (see the first item).
- [~] **No generated-edit tells.** No whoosh, word-pop, emoji, glitch or "¿Sabías que…?". Softer tells remain: the same blur dissolve on every exit and every caption, a $0 → $1,000 count-up ticker, procedural low-poly "paper", and a template-style translucent pill.
- [~] **Pop-ups feel like his Pinterest board and the reference reels.** The A-cards (pins 20 and 21), B&W with red marker (23, 25), cobalt halftone books (33, 38), ransom letters (03), ben-day burst (43) and strawberry are all true to his board. Where it falls short:
  - the ground is not his crumpled grid paper;
  - the captions are boxed, unlike @iamsarahsnow;
  - the card-shrink is bottom-anchored and bleeds off frame with square corners, unlike @artzenmedia's rounded, fully framed card;
  - the handwritten sign-off (@joshguvi) is cramped onto a busy board and holds about 0.7 s.
- [ ] **User's "under the chin" request.** About 22 s of split captions sit above his head.
