"""deliver: per-style files and the 9:16 showcase reel.

  out/IDEABRO_0N_<style>_16x9.mp4   1920x1080 60 fps
  out/IDEABRO_0N_<style>_9x16.mp4   1080x1920 60 fps
  out/IDEABRO_5_styles_9x16.mp4     title card + all five, each labelled
H.264 high, AAC 320k 48 kHz, -14 LUFS, every file under ~28 MB.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from vibelib import ff, loudnorm_filter  # noqa: E402

FONTS = HERE.parent / "fonts"


def name(st, style, fmt):
    return f"IDEABRO_0{st}_{style}_{fmt}.mp4"


def encode(inputs, out, fps, dur, extra=(), crf=16, cap_mb=24.0, maps=("-map", "0:v:0", "-map", "1:a:0")):
    mbps = cap_mb * 8 * 0.95 / dur - 0.33
    ff(*inputs, *extra, *maps, "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-maxrate", f"{mbps:.1f}M",
       "-bufsize", f"{2 * mbps:.1f}M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(fps), "-c:a", "aac",
       "-b:a", "320k", "-ar", "48000", "-t", f"{dur:.3f}", "-movflags", "+faststart", out)
    print("->", out, f"{Path(out).stat().st_size / 1e6:.1f} MB")


def final(st, style, fmt, work, out_dir, fps, dur):
    out_dir = Path(out_dir); out_dir.mkdir(exist_ok=True)
    encode(["-i", work / style / f"{fmt}.mp4", "-i", work / style / "sting.wav"], out_dir / name(st, style, fmt), fps, dur)


# ---------------------------------------------------------------- showcase
def font(file, size):
    return ImageFont.truetype(str(FONTS / file), size)


def label_png(path, num, title, w=1080, h=1920):
    """top-left style label: '01' in amber + the style name, on a soft dark strip for legibility."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    grad = np.zeros((300, w, 4), np.uint8); grad[..., 3] = (np.linspace(150, 0, 300)[:, None]).astype(np.uint8)
    im.alpha_composite(Image.fromarray(grad, "RGBA"), (0, 0))
    d.text((72, 120), f"{num:02d}", font=font("JetBrainsMono-500.ttf", 54), fill=(255, 181, 71, 255))
    d.text((72, 186), title, font=font("Montserrat-Black.ttf", 66), fill=(255, 255, 255, 255))
    im.save(path)


def title_png(path, w=1080, h=1920):
    im = Image.new("RGB", (w, h), (0, 0, 0)); d = ImageDraw.Draw(im)
    def ctext(y, s, f, col):
        bw = d.textlength(s, font=f); d.text(((w - bw) / 2, y), s, font=f, fill=col)
    ctext(760, "5 LOGO", font("Montserrat-Black.ttf", 150), (255, 255, 255))
    ctext(930, "ANIMATIONS", font("Montserrat-Black.ttf", 112), (255, 181, 71))
    ctext(1100, "I D E A B R O   S T U D I O", font("Montserrat-Bold.ttf", 40), (200, 200, 205))
    im.save(path)


def showcase(styles, titles, work, out_dir, fps, T):
    import music as M
    import soundfile as sf
    tmp = work / "showcase"; tmp.mkdir(parents=True, exist_ok=True)
    out_dir = Path(out_dir)
    segs = []
    # title card: 1.4 s, a tick + low thump under it
    INTRO = 1.4
    title_png(tmp / "title.png")
    n = int(INTRO * M.SR); a = np.zeros((n, 2), np.float32)
    th = M.osc_sin(45 * (1 + 2 * np.exp(-np.arange(n) / M.SR * 25)), n) * np.exp(-np.arange(n) / M.SR * 5) * 0.8
    tk = M.filt(M.noise(n), "hp", 3000) * np.exp(-np.arange(n) / M.SR * 70) * 0.5
    a[:, 0] = a[:, 1] = th + tk
    sf.write(tmp / "title.wav", a, M.SR)
    ff("-loop", "1", "-framerate", str(fps), "-i", tmp / "title.png", "-i", tmp / "title.wav",
       "-vf", "fade=in:st=0:d=0.15,fade=out:st=1.2:d=0.2,format=yuv420p", "-c:v", "libx264", "-crf", "14", "-r", str(fps),
       "-c:a", "pcm_s16le", "-ar", "48000", "-t", f"{INTRO}", tmp / "seg0.mov")
    segs.append(tmp / "seg0.mov")
    for st, style in styles.items():
        label_png(tmp / f"label{st}.png", st, titles[st])
        dur = T[style]["dur"]
        ff("-i", work / style / "9x16.mp4", "-i", work / style / "sting.wav", "-loop", "1", "-i", tmp / f"label{st}.png",
           "-filter_complex", f"[2:v]format=rgba,fade=in:st=0.15:d=0.25:alpha=1,fade=out:st=2.6:d=0.4:alpha=1[l];"
                              f"[0:v][l]overlay=0:0:shortest=1,format=yuv420p[v]",
           "-map", "[v]", "-map", "1:a:0", "-c:v", "libx264", "-crf", "14", "-r", str(fps), "-c:a", "pcm_s16le", "-ar", "48000",
           "-t", f"{dur:.3f}", tmp / f"seg{st}.mov")
        segs.append(tmp / f"seg{st}.mov")
    lst = tmp / "list.txt"
    lst.write_text("\n".join(f"file '{s}'" for s in segs))
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", tmp / "joined.mov")
    total = INTRO + sum(T[s]["dur"] for s in styles.values())
    ff("-i", tmp / "joined.mov", "-vn", "-c:a", "pcm_s16le", tmp / "joined.wav")
    ff("-i", tmp / "joined.wav", "-af", loudnorm_filter(tmp / "joined.wav", -14.0, -1.0, 11), "-ar", "48000", tmp / "joined_ln.wav")
    encode(["-i", tmp / "joined.mov", "-i", tmp / "joined_ln.wav"], out_dir / "IDEABRO_5_styles_9x16.mp4", fps, total)
