"""ACID CHROME: the "Vibe Editing" hype reel (1080x1920, 30 fps, 33.75 s, 128 BPM, no narration).

    python3 build.py stills 1.2 8.2 ...   # preview PNGs -> out/web/ (+ out/webrow.png)
    python3 build.py layer                # 3D + HUD at 60 fps in headless Chromium -> work/layer60.mp4 (resumable)
    python3 build.py picture              # 2-sample motion blur (180 deg shutter) -> work/picture.mp4 at 30 fps
    python3 build.py sound                # original track + SFX, -14 LUFS, muxed -> out/vibe_editing_acid_chrome.mp4
    python3 build.py all

The picture timeline is fixed to the bar grid (scene.js) and the music is written to the same grid here.
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REELS = HERE.parent.parent
sys.path.insert(0, str(REELS / "common"))
import music as M  # noqa: E402

BPM = 128
BEAT = 60 / BPM
BAR = 4 * BEAT
DUR = 18 * BAR
A0, B0, C0, D0, E0, F0, G0 = (b * BAR for b in (0, 2, 4, 6, 8, 12, 14))
T_TYPE, CPS, T_ENTER = 0.3, BEAT / 4, 1.5 * BAR
KEYS = [T_TYPE + i * CPS for i in range(len("make it crazy."))]
NO_SLOTS = [D0 + i * 2 * BEAT for i in range(3)]
NO_JUST = D0 + 6 * BEAT
CUTS = []
_t = F0
for i in range(12):
    CUTS.append(_t)
    _t += BEAT if i < 4 else BEAT / 2
OUT = HERE / "out" / "vibe_editing_acid_chrome.mp4"


# ---------------------------------------------------------------- music: F minor, i-VI-III-VII, written to the picture
def song():
    S = M.Song(DUR, BPM, "F", "minor", seed=21)
    prog = [1, 6, 3, 7]
    for name, rev, dly, sc, g in [("kick", 0, 0, 0, 0), ("snare", 0.16, 0, 0, -1), ("hats", 0.04, 0, 0, -2),
                                  ("bass", 0, 0, 0.75, 0), ("chords", 0.22, 0, 0.7, 0), ("pad", 0.4, 0, 0.35, 0),
                                  ("lead", 0.22, 0.22, 0.4, 0), ("pluck", 0.2, 0.25, 0.4, 0), ("fx", 0.3, 0, 0, 0)]:
        S.track(name, rev, dly, sc, g)
    K = M.kick(50, 1.15, 0.36)
    CL = M.clap()

    def four(b0, b1, claps=True, open_hat=True, rolls=False):
        for b in range(b0, b1):
            for i in range(4):
                S.add("kick", K, S.at_bar(b, i))
                if open_hat:
                    S.add("hats", M.hat(True, vel=0.75), S.at_bar(b, i + 0.5), pan=-0.2)
                for j in (0.25, 0.75):
                    S.add("hats", M.hat(False, vel=0.45), S.at_bar(b, i + j), pan=0.3)
            if claps:
                S.add("snare", CL, S.at_bar(b, 1))
                S.add("snare", CL, S.at_bar(b, 3))

    def reese_bar(b, bright=900, octave=2):
        bn = S.deg(prog[b % 4], octave)
        for i in range(8):
            if i % 2 == 0:
                continue                     # off-beat 8ths: the kick owns the downbeats
            S.add("bass", M.reese(bn + (12 if i == 7 else 0), BEAT * 0.45, bright), S.at_bar(b, i / 2))
        S.add("bass", M.sub(bn, BEAT * 0.4), S.at_bar(b, 0), -4)

    def stabs(b, rhythm=(0, 0.75, 1.5, 2.25, 3.0), cutoff=6000, dur=0.5):
        ch = S.chord(prog[b % 4], 4, 4)
        for r in rhythm:
            S.add("chords", M.supersaw(ch, BEAT * dur, cutoff, 7, 0.2, 0.003, 0.05, 0.7, 0.3), S.at_bar(b, r))

    # [01] prompt: a held chord opening up while the prompt types, then everything drops out on Enter
    S.add("pad", M.pad(S.chord(1, 3, 4), T_ENTER + 0.4, 1800, 0.4, 0.3), 0.0)
    for i in range(int(T_ENTER / BEAT)):
        S.add("bass", M.sub(S.deg(1, 2), BEAT * 0.35), i * BEAT, -6)
        S.add("hats", M.hat(False, vel=0.25), i * BEAT + BEAT / 2, pan=0.4)
    S.add("fx", M.reverse_crash(B0 - T_ENTER), T_ENTER, -2)
    S.add("fx", M.riser(B0 - T_ENTER, 12000), T_ENTER, -4)

    # [02] type tunnel + [03] morph: four-on-the-floor, reese, stabs; morph gets a pluck arp on every 8th
    four(2, 6)
    for b in range(2, 6):
        reese_bar(b, 800 if b < 4 else 1200)
        stabs(b, (0, 1.5, 3.0) if b < 4 else (0, 0.75, 1.5, 2.25, 3.0))
    arp = [1, 3, 5, 8, 5, 3, 8, 10]
    for b in range(4, 6):
        for i in range(8):
            S.add("pluck", M.pluck(S.deg(arp[i] + prog[b % 4] - 1, 5), BEAT * 0.45, 6000, 0.16), S.at_bar(b, i / 2))
    S.add("fx", M.impact(2.0), B0, -2)
    S.add("fx", M.crash(2.0), B0, -6)
    S.add("fx", M.crash(1.6), C0, -8)

    # [04] NO: half-time hits; each word = impact + braam, each blade = snare crack; then a roll into the drop
    for s in NO_SLOTS:
        S.add("kick", M.sat(M.kick(44, 1.4, 0.5, 0.9), 2.5), s)
        S.add("fx", M.impact(1.4, 29), s, -1)
        S.add("pad", M.brass_braam(S.deg(1, 2), 2 * BEAT), s, 2)
        sn = M.snare(220, 1.4, 0.2)
        S.add("snare", M.sat(sn + np.pad(CL, (0, max(0, len(sn) - len(CL))))[: len(sn)], 2.0), s + BEAT)
    S.add("pad", M.brass_braam(S.deg(1, 3), 2 * BEAT), NO_JUST, 3)
    S.add("snare", M.snare_roll(E0 - NO_JUST, 4, 32, 220), NO_JUST, -2)
    S.add("fx", M.riser(E0 - NO_JUST + BEAT, 14000), NO_JUST - BEAT, -1)

    # [05] drop: full groove, syncopated supersaw, vocal-chop lead, fill into the montage
    four(8, 12)
    hook = [8, 10, 9, 8, 6, 8, 5, 6]
    for b in range(8, 12):
        reese_bar(b, 1500)
        stabs(b)
        for i in range(8):
            S.add("lead", M.vox(S.deg(hook[i] + (2 if b % 2 else 0), 5), BEAT * 0.42, "aeoui"[i % 3]), S.at_bar(b, i / 2),
                  pan=0.25 * math.sin(i))
        for i in range(16):                               # 16th shaker drive
            S.add("hats", M.shaker(0.5 + 0.3 * (i % 4 == 2)), S.at_bar(b, i / 4), pan=-0.3)
    for b in (8, 10):
        S.add("fx", M.impact(2.4), S.at_bar(b), 0)
        S.add("fx", M.crash(2.4), S.at_bar(b), -3)
    for j, n in enumerate((50, 47, 45, 43)):              # tom fill on the last beat of the barrel roll
        S.add("snare", M.tom(n, 0.25), S.at_bar(11, 3 + j / 4), -2)

    # [06] montage: a kick + chord stab on every cut, the cuts getting faster, pitch climbing into the logo
    for i, c in enumerate(CUTS):
        S.add("kick", K, c)
        ch = S.chord(prog[i % 4], 4, 4)
        up = i // 4
        S.add("chords", M.supersaw([n + up for n in ch], min(BEAT, CUTS[i + 1] - c if i + 1 < len(CUTS) else BEAT / 2) * 0.8,
                                   7000, 7, 0.2, 0.002, 0.04, 0.7, 0.2), c)
        S.add("bass", M.reese(S.deg(prog[i % 4], 2) + up, BEAT * 0.4, 1600), c)
        S.add("hats", M.hat(i % 2 == 1, vel=0.8), c + 0.06)
    S.add("snare", M.snare_roll(BAR, 8, 32, 240), F0 + BAR, -3)
    S.add("fx", M.riser(BAR * 1.0, 15000), F0 + BAR, -2)

    # [07] logo: one slam per letter, EDITING lands with a crash, then a half-time outro under the tagline
    for i in range(4):
        t = G0 + i * BEAT
        S.add("kick", M.sat(M.kick(42 - i, 1.4, 0.55, 0.9), 2.5), t)
        S.add("fx", M.impact(1.2, 30 - i), t, -2)
        S.add("snare", M.taiko(36 + 2 * i, 0.9), t, -3)
    S.add("pad", M.brass_braam(S.deg(1, 2), BAR), G0, 2)
    S.add("fx", M.crash(3.0), G0 + BAR, -2)
    S.add("fx", M.impact(3.0, 29), G0 + BAR, -1)
    for b in range(15, 18):
        last = b == 17
        S.add("kick", K, S.at_bar(b, 0))
        if not last:
            S.add("kick", K, S.at_bar(b, 2.5))
            S.add("snare", CL, S.at_bar(b, 2))
            for i in range(8):
                S.add("hats", M.hat(i % 2 == 1, vel=0.5), S.at_bar(b, i / 2 + 0.25), pan=0.25)
        S.add("pad", M.pad(S.chord(prog[(b - 15) % 4], 4, 4), BAR * (1.6 if last else 1.0), 2600, 0.05, 0.6), S.at_bar(b))
        S.add("bass", M.sub(S.deg(prog[(b - 15) % 4], 2), BAR * (1.5 if last else 0.9)), S.at_bar(b))
        if not last:
            for i in range(8):
                S.add("lead", M.vox(S.deg(hook[i], 5), BEAT * 0.42, "aeoui"[i % 3]), S.at_bar(b, i / 2), -3)
    S.add("fx", M.bell(S.deg(1, 6), 2.5), S.at_bar(17), -4)
    return S


def master():
    return song().master(width=1.2)


# ---------------------------------------------------------------- picture
def layer(extra):
    cmd = ["node", str(REELS / "batch2" / "render3d.mjs"), str(HERE / "scene.html"), "--fps", "60", "--dur", f"{DUR:.4f}",
           "-o", str(HERE / "work" / "layer60.mp4")] + extra
    subprocess.run(cmd, check=True)


def picture():
    # average each pair of 60 fps frames: real motion blur with a 180 degree shutter, then 30 fps
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(HERE / "work" / "layer60.mp4"), "-vf",
                    "tmix=frames=2:weights='1 1',select='not(mod(n+1\\,2))',setpts=N/30/TB",
                    "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "13", "-pix_fmt", "yuv420p",
                    str(HERE / "work" / "picture.mp4")], check=True)
    print("->", HERE / "work" / "picture.mp4")


def stills(ts):
    subprocess.run(["node", str(REELS / "batch2" / "render3d.mjs"), str(HERE / "scene.html"), "--stills", ",".join(ts),
                    "-o", str(HERE / "out" / "web")], check=True)


# ---------------------------------------------------------------- sound
def sound():
    from sound import Mix
    bed = master()
    m = Mix(DUR)
    m.music(bed, gain_db=-1.0, duck_db=0, fade_out=0.5)
    for i, k in enumerate(KEYS):
        m.sfx("click", k, -11, pan=0.1 * math.sin(i))
    m.sfx("pop", T_ENTER, -6)
    m.sfx("whoosh", B0 - 0.45, -6)
    for i in range(8):
        m.sfx("swish", C0 + i * BEAT, -14, pan=0.3 if i % 2 else -0.3)
    for s in NO_SLOTS:
        m.sfx("swish", s + BEAT - 0.08, -4)
        m.sfx("glitch", s + BEAT, -12)
    m.sfx("whoosh", E0 - 0.4, -6)
    for c in CUTS:
        m.sfx("shutter", c, -10)
        m.sfx("glitch", c, -16)
    for i in range(4):
        m.sfx("whoosh", G0 + i * BEAT - 0.3, -12)
    m.sfx("sparkle", G0 + 1.5 * BAR, -10)
    m.sfx("sparkle", G0 + 3 * BAR, -12)
    m.finish(HERE / "work" / "picture.mp4", OUT, HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    args = sys.argv[2:]
    (HERE / "work").mkdir(exist_ok=True)
    (HERE / "out").mkdir(exist_ok=True)
    if cmd == "stills":
        stills(args)
    elif cmd == "layer":
        layer(args)
    elif cmd == "picture":
        picture()
    elif cmd == "sound":
        sound()
    elif cmd == "music":
        import audio_kit as ak
        ak.write_wav(HERE / "work" / "music.wav", master())
        print("->", HERE / "work" / "music.wav")
    elif cmd == "all":
        layer(args)
        picture()
        sound()
