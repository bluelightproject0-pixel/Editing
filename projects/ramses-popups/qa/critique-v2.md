# Critique v2: ramses-popups (long 1:56 + short 1:01, 1080x1920)

Independent critic, round 2. Judged from `qa/k3` (long) and `qa/s1` (short). Root causes point to `build/build.py` (and `build/assets.py`).
Timing note: the k3/s1 frames (19:38-19:41) come from the build **before** the 19:43 `build.py` edit, which moved the end of the hook cut from about 5.95 to 5.15. In the current build, every long-version timecode after 5 s sits about 0.8 s earlier.

## 1. Score (taste.md §6), LONG version

| Criterion | Wt | Score | Why |
|---|---|---|---|
| Hook | 20% | **7** | Fixed: the face and the full title are on frame 0, on real paper strips, and the strawberry is tied to the end payoff. The problem: 0-1.40 s is a **frozen, motion-blurred still** (`open.jpg`). Frames 0 and 1 s are pixel-identical in the face region while he says "Yo he estado viendo que la…". Nothing moves after 0.65 s. The "que los FRESAS no saben" strip (bottom y≈497) sits on his hair (y≈500-510) until 3.5 s. |
| Idea | 15% | **7** | Pin-aways now head toward their real slots, and the live strike on "no son para nada fresas" lands (101 s). But the board is still never *seen* growing: every piece exits off-frame and the paper margins around the split card (69-77, 81-94) stay empty, so the collage still arrives all at once at 98 s. The "OYE BRO" bubble exits with a blur and has no slot. The books lost their "LIBROS" label. "EMPAQUETADO" appears twice (polaroid caption and card). |
| Pacing | 15% | **6** | No stretch is static for more than 5 s now, but 54.4-67.5 is 13 s of talking head with only two small punch-ins ("mucho queso y jamón" has no visual). 15.0-19.9 runs 4.9 s with no change. In the first 15 s, 5.2-9.3 runs 4.1 s with no change (the target is 3 s). At 1:56, it is long for the profile; the short version covers that. |
| Motion | 15% | **7** | The split now shrinks to the chin with a solid border, and the morphs finish before the cuts. The freeze → polaroid pin-away (31.9) is the best move in the edit. Remaining problems: `stick()` fades opacity in, so pieces arrive as grey ghosts (69.0 tag), and paper doesn't fade. The hook title and the bubble still leave with the blur `leave()`. 93.2-94.9 still has morph → cut → cut in about 1.6 s. Nothing is snappier than the rules allow, so no cap. |
| Readability | 15% | **7** | No faces are covered, so no cap. Cream torn strips with ink EB Garamond at y 1462 read well everywhere and sit under the chin in every layout. Remaining problems: merged groups hit 5-6 words ("en mi trabajo a hacer más" 76.8, "lo pides nomás aquí a la", "ya si puedes mejorar la"), which breaks the brand's 1-3 word rule and pushes wide strips toward the right rail. Captions echo labels ("automatización con" under the AUTOMATIZACIÓN hub, 81.5; "nosotros" under "AYUDARNOS ENTRE NOSOTROS", 108). The board's mini "AUTOMATIZACIÓN" label is 26 px (even smaller after the tweak), and the right column reaches x≈1020 at the 101 s pan. |
| Sound | 10% | **6** | 24 SFX, at most 3 per 10 s, all tied to actions, no whooshes. There is still no bed (R-music-bed). The SFX are synthesized noise and have not been checked by ear. There is no `audio_backtest.py` result yet, so I can't confirm the cap is clear. |
| Ending | 10% | **8** | The source ending is preserved, the strawberry callback works, "Dios te bendiga." is fully written and held for about 1.8 s, and there is no CTA, as asked. "aquí están mis gems" still has no visual. |

**Weighted: 1.40 + 1.05 + 0.90 + 1.05 + 1.05 + 0.60 + 0.80 = 6.85 → 6.9 / 10.** No caps. Up from 5.2. Not yet at the 8 bar.

**SHORT version (61 s), delta.** Yes, it holds as its own piece: hook → cheese POV, freeze and cards (the trick) → "ese dinero lo puedes invertir en algo que te añada más dinero / el chiste no es ahorrar por ahorrar" (the saving idea survives without the $1,000-2,000/books beat) → AI hub and bubble → board, strike and "Dios te bendiga". It is denser, so pacing is about +1. Its board correctly drops mamá, TRUCO, $2,000/libros and AYUDARNOS (the `has()` guards), so **no pop-up or board piece references removed material**. The problems are in the **spoken** cut:
- (a) Seen in the s1 frames: "la verdad o sea la" / "mayoría" dangles before "entonces no saben" (cg5-cg6). `build.py` already ends that range at 5.15, which falls in a −28 to −30 dB gap, so re-snapshot to confirm.
- (b) **"vida cómoda" is orphaned** at about 50.4 s (src 122.85-123.57, the tail of "vivir una vida cómoda", which the short removes). It is merged into the caption "*baratas* aquí vida *cómoda*".
- (c) A stray "o" opens the caption "o mucho éxito y ya sabes" (src 126.11-126.17).
- (d) The board is lopsided: the top-right slot (TRUCO) is empty.

With (b) and (c) fixed, the short scores about 7.1. As shown, it scores about 6.6.

## 2. Remaining blocking issues

**N1. Frozen, blurred face for the first 1.40 s (long and short).** Frame 0 is a mid-whip motion-blurred frame, held completely still while his voice plays.
- Root cause: `main()` grabs `open.jpg` at `-ss 1.40` (still mid-whip), and `build_root()` shows it static for `o(1.40)`. `camera_js()` starts the drift only at `o(1.40)`. (My round-1 "use a still" advice caused this.)
- Fix, preferred: drop `#open` and play the source from 0. Source frame 0 is the packaged-cheese case with real price tags, which is the trick's own evidence under the title, and the whip up to his face by 1.3 s is real motion.
- Minimum fix: grab the still at src about 2.2 (sharp), tween `#cam` 1.0→1.04 from 0, and raise `#hook-l1/l2` 40 px so they clear his hair.

**N2. A sliver of the "Claude" label stays parked on the right edge**, x 1048-1080, y 786-830.
- When: long about 88.2-93.6 (k3 88.6 and 93.2); short about 44.6-50.3.
- Root cause: in `build_ia()`, `pin_away("#ia-net", bro-0.5, 760, 120, 3, 0.6)` scales the full-frame net to 0.6 about its centre, so Claude (left 120) lands at x≈1048 and doesn't clear the frame.
- Fix: dx ≥ 1000. Better, end `pin_away()` with `autoAlpha: 0` at the end of the tween, so no pinned piece can ever linger.

**N3. SHORT only: spoken non-sequitur** "…más baratas aquí. **vida cómoda**, para todos mis seguidores… fresas, **o** / mucho éxito".
- Root cause: short `RANGES` has `(122.75, 126.22)`.
- Fix: `(123.64, 126.10)`. 123.63-123.70 is a −30 dB gap; 126.10 cuts before the "o".
- Then re-run `mix.py` with `VARIANT=short` and re-check `cut_check`.

## 3. Top 3 improvements (ranked)

1. **Let the board grow on screen (Idea +2).**
   - Host `#bw` from the first split onward instead of only at `board_t`. During the splits, hold it at `scale 1.4` (`transformOrigin 540px 960px`, under `#card`). At that scale, each earned piece peeks out of the paper margins around the 0.74 card: strawberry top-left (x −118..120, y −17..245), mamá tag and chiste strip in the top band (y 42-316), the cards on the left edge, and the $2,000/AI column on the right edge (x 898+).
   - Reveal each piece with `tl.set(piece, {autoAlpha:1})` at the moment its pop-up's `pin_away` ends, so the viewer sees it land.
   - At 98 s, tween 1.4→1 instead of 2→1. The pull-back then completes a board the viewer watched fill up.
   - In the same pass: pin the bubble into a slot under the AI column (replace its `leave()`), add "LIBROS" under the mini books, and replace the polaroid caption "empaquetado" with "$359" to remove the duplicate.
2. **Make the ground real crumpled paper.** `assets.py paper_grid()` still reads as generated: `folds()` makes long, straight crease planes, and the 54 px grid is drawn dead-straight over them. Pin-01 has dense small crumples, and its fine grid bends with them.
   - Use `folds(n≈700, L 20-70, Wd 30-90)`.
   - Draw the grid at about a 34 px step, displaced by the height-map gradient (`x += gx*k`, `y += gy*k`), so the lines kink at every crease.
   - Or use a real scan. The ground is on screen for about 40 s.
3. **Captions: 1-3 words, and never echo a label.**
   - In `build_captions()`, the merge allows 26 chars. Merge only if the result is ≤ 3 words and ≤ 18 chars; otherwise keep the short group and extend its end into the gap.
   - While a graphic shows the same word (AUTOMATIZACIÓN hub 81.2-82.5, AYUDARNOS note), drop it from the caption or show the caption without the duplicate.
   - Make `stick()` opaque from frame 1 (animate only scale, rotation and y) so paper pieces don't ghost in.

Next after these: a polaroid callback for "mucho queso y jamón" (about 63-65 s) to break up the 13 s graphic-free stretch; a light bed at −24 dB with ducking; `audio_backtest.py`.

## 4. Round-1 blocking issues

| ID | Resolved? | Evidence |
|---|---|---|
| B1 forehead caption 78.2-79.9 | **yes** | 78.2: "*dinero*" at y 1462 on the chin, full frame |
| B2 captions on hair or above head in splits, tag over head, $0 | **yes** | 69.0-93.2: always under the chin. The tag sits on the card's ceiling and starts at $1,000 |
| B3 "DELSÚPER" | **yes** | Board: "DEL SÚPER" spaced, 99-116 s |
| B4 pieces clipped at frame edge | **yes** | MAMÁ tag ends at x≈1000. Board pans stay in frame. Residual: the AI column reaches x≈1020 (past the 1015 margin, not clipped) |
| B5 uncaptioned speech 94-96, flashes | **yes** | Words re-timed. No caption gap > 1 s anywhere. Two short chunks remain: "para todos mis" 0.31 s (97.77), "ya sabes que" 0.38 s (109.07) |
| B6 empty frame 0 | **partly** | Face and title are on frame 0 now, but the face is a frozen, blurred still for 1.4 s (N1) |
