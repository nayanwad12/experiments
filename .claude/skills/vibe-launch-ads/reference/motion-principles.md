# Motion principles and recipes (motion_kit)

## Easing: pick by intent

| intent | easing | typical duration |
|---|---|---|
| things arriving (UI, text in) | `ease_out_cubic`, `ease_out_expo` | 0.3–0.5 s |
| playful arrival with overshoot | `ease_out_back`, `spring(t)` | 0.4–0.6 s |
| things leaving | `ease_in_cubic`, `ease_in_back` | 0.2–0.35 s (exits are faster than entrances) |
| moving across the screen | `ease_in_out_cubic`, `ease_in_out_expo` | 0.5–0.9 s |
| landing / dropping | `ease_out_bounce` | 0.6–0.9 s |
| wobble / attention | `ease_out_elastic`, `noise1(t)` | short |
| never | linear motion for anything that starts or stops | (only for constant drifts and scrolls) |

```python
k = ease_out_back(prog(t, start=1.2, dur=0.45))      # 0 -> 1 (overshoots)
x = lerp(-300, 540, k)
```

## Timing rules

- **Stagger** groups: 60–120 ms between items (`stagger(t, i, start, each=0.08, dur=0.4)`).
- **Anticipation:** a 5–10 % squash/backwards move before a big move.
- **Overshoot and settle** for anything that should feel alive; **hard cuts** for anything that should feel punchy.
- **Hold** important frames ≥ 1 s. Viewers need reading time (0.3 s/word + 0.5 s).
- **Beat-lock**: entrances on beats (`TL.beat(n)`), big changes on bars, pulses via `pulse(t, BPM)`.
- Keep one focal point moving at a time. If everything moves, nothing reads.

## Kinetic typography recipes

| effect | how |
|---|---|
| word-by-word slam | each word `scale = 1.6 -> 1.0` with `ease_out_back`, +impact SFX, tiny camera shake |
| stagger rise | letters/words `y += (1-k)*60U`, `alpha = k`, staggered 40 ms |
| highlight bar | rounded rect width grows with `ease_out_expo` behind one key word, text colour flips |
| typewriter / prompt | `s[:int(chars_per_s * lt)]` + blinking caret (`int(t*2)%2`) + `typing` SFX |
| counter | `f"{int(lerp(0, 1250, ease_out_expo(k))):,}"` |
| strike-through | line width grows over the word, then the word drops away |
| slot machine | vertical list of words scrolling with `ease_out_expo`, masked by a clip rect |
| masked reveal | `c.clipRect(...)` then slide the text up from below the mask edge |

## Camera

```python
c.save()
s = 1 + 0.06 * ease_in_out_cubic(prog(t, 2, 4))          # slow push-in
sx = 8 * U * noise1(t * 7) * shake                        # handheld / impact shake
c.translate(W/2 + sx, H/2); c.scale(s, s); c.translate(-W/2, -H/2)
... draw scene ...
c.restore()
```
Impact shake: amplitude `exp(-8 * (t - hit))` for 0.4 s after the hit.

## Transitions catalogue

| transition | build |
|---|---|
| hard cut on beat | best default for social |
| whip pan | both scenes slide by `±W` with `ease_in_out_expo` over 0.25 s + motion streaks + whoosh |
| circle / iris wipe | `c.clipPath(circle(r(t)))` revealing the next scene |
| shape wipe | brand-colour rectangle sweeps across, next scene revealed behind it |
| zoom-through | scale scene A up 1→4 while fading, scene B scales 0.6→1 |
| glitch | 2–4 frames of RGB split (offset R and B channels in numpy) + slice displacement + glitch SFX |
| match cut | the same shape/colour in the same place across two scenes |

## Finishing (post)

- `grain(arr, 0.03)` and `vignette(arr, 0.3)` via `S.render(..., post=fn)` for a filmic feel.
- Motion blur: render 2–4 sub-frames at `t + i/(fps*n)` and average them (slower; use for fast motion only).
- Drop shadows (`shadow()`) separate layers. Keep the light direction consistent (shadows go down/right).

## Common mistakes

- Text overflow → measure with `text_width` and auto-fit.
- Everything the same speed → vary: fast in, hold, faster out.
- Too many fonts/colours → 2 fonts, 1 accent.
- Animating with `t` directly (e.g. `x = t * 100`) → use `prog` + easing so you control start and end.
