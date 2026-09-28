"""Shared timeline for the Vibe Editing promo: scene cuts, SFX cues, camera hits.

Everything is locked to a 150 BPM grid (1 beat = 0.4 s), so every cut lands on a beat.
"""

W, H = 1080, 1920
FPS = 30
DUR = 30.0
STEP_FPS = 12          # paper elements animate "on twos-and-a-half" like stop-motion
BPM = 150
BEAT = 60.0 / BPM      # 0.4 s

# (start, end, scene name, enter transition)
SCENES = [
    (0.0, 3.2, "hook", None),
    (3.2, 7.2, "problem", "tear_up"),
    (7.2, 11.2, "reveal", "tear_left"),
    (11.2, 12.8, "captions", "tear_diag"),
    (12.8, 14.4, "motion", "tear_up"),
    (14.4, 16.0, "anim", "tear_left"),
    (16.0, 17.6, "ads", "tear_diag"),
    (17.6, 19.2, "trans", "tear_up"),
    (19.2, 20.8, "recap", None),
    (20.8, 21.6, "all", None),
    (21.6, 22.0, "with", None),
    (22.0, 23.2, "ai", None),
    (23.2, 26.8, "payoff", "tear_left"),
    (26.8, 30.0, "cta", "tear_up"),
]


def scene_start(name):
    for s, e, n, _ in SCENES:
        if n == name:
            return s
    raise KeyError(name)


def _sfx():
    S = scene_start
    ev = []
    add = lambda t, kind, gain=1.0: ev.append((round(t, 4), kind, gain))

    # HOOK
    t0 = S("hook")
    add(t0, "impact", 0.9)
    add(t0 + 0.05, "pop")
    add(t0 + 0.15, "rustle", 0.8)
    add(t0 + 0.30, "pop")
    for i in range(6):
        add(t0 + 0.45 + i * 0.14, "tick", 0.5)   # frantic scrubbing
    add(t0 + 1.2, "pop")
    add(t0 + 1.3, "crumple", 1.0)
    add(t0 + 1.6, "stamp", 0.7)
    add(t0 + 2.05, "slap", 0.6)
    add(t0 + 2.35, "slap", 0.45)
    add(t0 + 2.75, "whoosh", 1.0)

    # PROBLEM
    t0 = S("problem")
    add(t0, "tear", 1.0)
    add(t0 + 0.02, "pop")
    add(t0 + 0.4, "pop", 0.7)
    for i in range(20):
        add(t0 + i * 0.2, "tick", 0.55)
    for i in range(18):
        add(t0 + 0.2 + i * 0.2 + 0.25, "slap", 0.45)
    add(t0 + 0.8, "stamp", 0.7)
    add(t0 + 1.6, "pop")
    add(t0 + 3.2, "rustle", 0.7)

    # REVEAL
    t0 = S("reveal")
    add(t0, "tear", 1.0)
    add(t0 + 0.05, "whoosh", 0.6)
    for i in range(11):
        add(t0 + 0.3 + i / 12, "type", 0.8)
    add(t0 + 1.4, "pop", 1.0)
    add(t0 + 1.42, "whoosh", 0.7)
    add(t0 + 1.55, "rustle", 0.9)
    add(t0 + 1.62, "pop", 0.8)
    add(t0 + 1.8, "pop", 0.7)
    add(t0 + 1.95, "pop", 0.7)
    add(t0 + 1.65, "sparkle", 0.6)
    add(t0 + 2.4, "stamp", 0.9)
    add(t0 + 2.6, "stamp", 0.8)

    # MONTAGE
    t0 = S("captions")
    add(t0, "impact", 1.0)
    add(t0, "whoosh", 0.8)
    add(t0 + 0.05, "stamp", 0.6)
    for i in range(4):
        add(t0 + 0.15 + i * 0.2, "pop", 0.8)
    t0 = S("motion")
    add(t0, "whoosh", 0.9)
    add(t0 + 0.02, "snip", 0.7)
    for i in range(6):
        add(t0 + 0.12 + i * 0.06 + 0.2, "pop", 0.55)
    for b in (0.4, 0.8, 1.2):
        add(t0 + b, "whoosh", 0.35)
    t0 = S("anim")
    add(t0, "tear", 0.9)
    for i in range(8):
        add(t0 + 0.05 + i * 0.04, "pop", 0.45)
    add(t0 + 0.1, "stamp", 0.6)
    add(t0 + 0.5, "sparkle", 0.6)
    t0 = S("ads")
    add(t0, "whoosh", 0.9)
    add(t0 + 0.05, "stamp", 0.6)
    add(t0 + 0.25, "slap", 0.7)
    add(t0 + 0.4, "pop", 1.0)
    add(t0 + 0.6, "pop", 0.6)
    t0 = S("trans")
    add(t0, "tear", 0.9)
    for b in range(4):
        add(t0 + b * 0.4 + 0.12, "whoosh", 0.8)
    t0 = S("recap")
    for k in range(8):
        add(t0 + k * 0.2, "snip" if k % 2 == 0 else "whoosh", 0.7)
    add(S("all"), "stamp", 1.0)
    add(S("with"), "stamp", 0.9)
    add(S("ai"), "impact", 1.0)
    add(S("ai") + 0.02, "sparkle", 0.9)

    # PAYOFF
    t0 = S("payoff")
    add(t0, "whoosh", 0.9)
    add(t0 + 0.2, "pop", 0.8)
    add(t0 + 0.4, "whoosh", 0.8)
    add(t0 + 0.6, "pop", 0.8)
    for b in (0.4, 1.2, 2.0, 2.8):
        add(t0 + b, "clack", 0.9)
    for b in (0.8, 1.6, 2.4, 3.2):
        add(t0 + b, "snip", 0.9)

    # CTA
    t0 = S("cta")
    add(t0, "whoosh", 0.8)
    add(t0 + 0.05, "rustle", 0.8)
    add(t0 + 0.4, "stamp", 1.3)
    add(t0 + 0.4, "impact", 0.7)
    add(t0 + 1.2, "pop", 1.0)
    add(t0 + 1.6, "pop", 0.7)
    add(t0 + 2.0, "type", 1.0)
    add(t0 + 2.02, "pop", 0.5)
    return sorted(ev)


SFX = _sfx()

# camera shakes: (time, amplitude px, decay s)
SHAKES = [
    (0.0, 14, 0.18),
    (1.6, 18, 0.2),
    (3.2 + 0.8, 16, 0.2),
    (3.2 + 3.2, 6, 0.8),
    (7.2 + 2.4, 22, 0.22),
    (7.2 + 2.6, 16, 0.2),
    (11.2, 26, 0.25),
    (20.8, 24, 0.2),
    (21.6, 20, 0.2),
    (22.0, 30, 0.3),
    (26.8 + 0.4, 38, 0.35),
]

# white paper flashes: (time, alpha, duration)
FLASHES = [
    (11.2, 0.55, 0.12),
    (20.8, 0.35, 0.08),
    (22.0, 0.6, 0.14),
    (27.2, 0.5, 0.12),
]

# sections where the camera punches in on every beat
PUNCH = [(0.0, 7.2), (9.6, 11.0), (11.2, 26.8), (27.2, 30.0)]
