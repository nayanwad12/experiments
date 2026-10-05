"""scene: starter animation for {{NAME}}. Every frame is a pure function of time t.

    python3 scene.py stills 0.6 2.4 4.4 6.0     # check frames -> out/stills/  (ALWAYS do this first)
    python3 scene.py audio                      # music + sfx -> work/mix.wav
    python3 scene.py draft                      # half-res, half-fps preview -> out/draft.mp4
    python3 scene.py render                     # final -> out/{{NAME}}.mp4
    python3 scene.py render-row row.json out.mp4  # one personalised version (used by vibe/batch.py)

Replace the three scene functions with your own; keep timings in timeline.py.
"""

import json
import os
import sys
from pathlib import Path

import skia

sys.path.insert(0, str(Path(__file__).resolve().parent / "vibe"))
import audio_kit as ak  # noqa: E402
from motion_kit import (Stage, clamp, ease_in_out_cubic, ease_out_back, ease_out_cubic, ease_out_expo,  # noqa: E402
                        lerp, prog, pulse, rgb, rrect, shadow, stagger, text, text_width)

import timeline as TL  # noqa: E402

S = Stage(TL.W, TL.H, fps=TL.FPS, duration=TL.DURATION)
B = S.brand
U = min(TL.W, TL.H) / 1080          # layout unit: 1.0 at 1080 px short side
BG, FG, ACC, ACC2 = rgb(B, "bg"), rgb(B, "fg"), rgb(B, "accent"), rgb(B, "accent2")


def background(c, t):
    c.clear(BG)
    step = 90 * U
    p = rgb(B, "fg", 0.06)
    paint = skia.Paint(Color=p, StrokeWidth=1.5 * U)
    off = (t * 20 * U) % step
    x = -off
    while x < TL.W:
        c.drawLine(x, 0, x, TL.H, paint)
        x += step
    y = -off
    while y < TL.H:
        c.drawLine(0, y, TL.W, y, paint)
        y += step


def s_hook(c, t, lt, dur):
    words = TL.COPY["hook"]
    widest = max(text_width(w, 100, "display") for w in words)
    size = min(200 * U, TL.W * 0.84 / widest * 100)       # fit the longest word inside the frame
    gap = size * 1.02
    y0 = TL.H / 2 - gap * (len(words) - 1) / 2
    bump = 1 + 0.04 * pulse(t, TL.BPM)
    for i, w in enumerate(words):
        k = stagger(lt, i, 0.05, 0.12, 0.45, ease_out_back)
        out = ease_in_out_cubic(prog(lt, dur - 0.35, 0.35))
        y = y0 + i * gap + (1 - k) * 160 * U - out * 220 * U
        col = ACC if i == len(words) - 1 else FG
        if i == len(words) - 1 and k > 0.5:      # highlight bar behind the last word
            wbar = text_width(w, size * bump, "display") + 60 * U
            kk = ease_out_expo(prog(lt, 0.5, 0.35))
            rrect(c, TL.W / 2 - wbar / 2, y - size * 0.58, wbar * kk, size * 1.12, 18 * U, FG)
        text(c, w, TL.W / 2, y, size=size * bump * (0.6 + 0.4 * k), font="display", fill=col,
             alpha=clamp(k * 2) * (1 - out))


def s_message(c, t, lt, dur):
    chips = TL.COPY["chips"]
    size = 64 * U
    h = size * 1.8
    y0 = TL.H / 2 - (len(chips) - 1) * (h + 28 * U) / 2
    out = ease_in_out_cubic(prog(lt, dur - 0.3, 0.3))
    for i, word in enumerate(chips):
        k = stagger(lt, i, 0.25, TL.BEAT / 2, 0.4, ease_out_back)
        w = text_width(word, size, "mono", 0.12) + 90 * U
        x = TL.W / 2 - w / 2 + (1 - k) * (TL.W * 0.6) * (1 if i % 2 else -1) - out * TL.W
        y = y0 + i * (h + 28 * U) - h / 2
        shadow(c, x, y, w, h, h / 2, blur=24 * U, dy=12 * U, alpha=0.18 * k)
        rrect(c, x, y, w, h, h / 2, ACC if i % 2 == 0 else ACC2)
        rrect(c, x, y, w, h, h / 2, FG, stroke=4 * U)
        text(c, word, x + w / 2, y + h / 2, size=size, font="mono", fill=FG, tracking=0.12)


def s_endcard(c, t, lt, dur):
    k = ease_out_expo(prog(lt, 0.0, 0.6))
    c.save()
    r = lerp(0, max(TL.W, TL.H), k)
    c.drawCircle(TL.W / 2, TL.H / 2, r, skia.Paint(Color=FG, AntiAlias=True))
    c.restore()
    title = TL.COPY["end_title"]
    size = min(170 * U, TL.W * 0.84 / text_width(title, 100, "display") * 100)
    kt = ease_out_back(prog(lt, 0.25, 0.5))
    text(c, title, TL.W / 2, TL.H / 2 - 40 * U, size=size * (0.7 + 0.3 * kt), font="display",
         fill=rgb(B, "paper"), alpha=clamp(kt * 2))
    tag = B.get("tagline", "")
    if tag:
        text(c, tag.upper(), TL.W / 2, TL.H / 2 + 90 * U, size=30 * U, font="mono", fill=ACC, tracking=0.14,
             alpha=ease_out_cubic(prog(lt, 0.6, 0.4)))
    kc = ease_out_back(prog(lt, 0.9, 0.45))
    cta = TL.COPY["cta"]
    w = text_width(cta, 48 * U, "mono", 0.14) + 120 * U
    h = 110 * U
    y = TL.H / 2 + 200 * U
    if kc > 0:
        rrect(c, TL.W / 2 - w * kc / 2, y, w * kc, h, h / 2, ACC)
        text(c, cta, TL.W / 2, y + h / 2, size=48 * U * kc, font="mono", fill=FG, tracking=0.14)
    text(c, f"by {B.get('name', '')}".upper(), TL.W / 2, TL.H - 140 * U, size=26 * U, font="mono",
         fill=rgb(B, "paper"), tracking=0.2, alpha=ease_out_cubic(prog(lt, 1.2, 0.5)))


SCENES = {"hook": s_hook, "message": s_message, "endcard": s_endcard}


def draw(c, t):
    background(c, t)
    name, lt, dur = TL.scene_at(t)
    SCENES[name](c, t, lt, dur)


def build_audio():
    Path("work").mkdir(exist_ok=True)
    ak.write_wav("work/music.wav", ak.music_bed(TL.MOOD, seconds=TL.DURATION, bpm=TL.BPM, intro_bars=0))
    Path("work/cues.json").write_text(json.dumps(TL.cues(), indent=1))
    import subprocess
    subprocess.run([sys.executable, "vibe/audio_kit.py", "mix", "work/cues.json", "-o", "work/mix.wav"], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        times = [float(x) for x in sys.argv[2:]] or [s + (e - s) * 0.6 for s, e, _ in TL.SCENES]
        S.stills(draw, times)
    elif cmd == "audio":
        build_audio()
    elif cmd == "draft":
        S.render(draw, "out/draft.mp4", audio="work/mix.wav", draft=True)
    elif cmd == "render":
        if not Path("work/mix.wav").exists():
            build_audio()
        suffix = f"_{TL.W}x{TL.H}" if os.environ.get("VIBE_SIZE") else ""
        S.render(draw, f"out/{{NAME}}{suffix}.mp4", audio="work/mix.wav")
    elif cmd == "render-row":
        # CSV columns named like TL.COPY keys replace that copy; use | to separate list items
        row = json.loads(Path(sys.argv[2]).read_text())
        for k, v in row.items():
            if k in TL.COPY:
                TL.COPY[k] = [x.strip() for x in v.split("|")] if isinstance(TL.COPY[k], list) else v
        if not Path("work/mix.wav").exists():
            build_audio()
        S.render(draw, sys.argv[3], audio="work/mix.wav")
    else:
        sys.exit(__doc__)
