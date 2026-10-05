"""Every timing in the film. Video (scenes.py) and sound (audio.py) both read this file,
so picture and audio can never drift apart."""

W, H, FPS = 1920, 1080, 60
DURATION = 40.0
BPM = 120                     # beat 0.5 s, bar 2 s
BAR0 = 1.0                    # bars start on odd seconds: 1, 3, 5 ... (drop lands on 9.0)

# narration: line id -> start (s) inside the film. Offsets inside each line came from
# pause detection on the Kokoro takes (work/vo_<id>.wav).
VO = {
    "apps": 0.47,      # After Effects 0.50 · Premiere Pro 1.14 · Higgsfield 2.24
    "subs": 3.16,      # Another month 3.20 · Another subscription 4.06
    "whatif": 5.56,    # What if you didn't need 5.60 · any of them 6.38
    "era": 7.94,       # This is the era of 7.99 · vibe editing 9.00
    "describe": 11.0,  # You don't drag keyframes 11.04 · You describe the vibe 12.50
    "features": 14.95, # Smooth transitions 15.0 · Kinetic type 16.40 · Sound design 17.22
    "meta": 20.46,     # Even this video 20.5 · Every frame 21.72 · every sound 22.09 · came from a prompt 22.56
    "nos": 24.96,      # No timeline 25.0 · No plugins 26.04 · No subscriptions 26.81
    "idea": 28.44,     # Just your idea 28.5 · and the words to describe it 29.53
    "end": 32.45,      # Welcome to 32.5 · vibe editing 33.0
}

# scenes: (name, start, end)
SCENES = [
    ("apps", 0.0, 3.05),
    ("subs", 3.05, 5.5),
    ("whatif", 5.5, 7.75),
    ("era", 7.75, 10.9),
    ("describe", 10.9, 14.95),
    ("features", 14.95, 20.3),
    ("meta", 20.3, 24.75),
    ("nos", 24.75, 28.3),
    ("idea", 28.3, 32.35),
    ("end", 32.35, 40.0),
]

# transition INTO scene i (at its start): kind, half-length (s)
TRANS = {
    "subs": ("push_up", 0.28),
    "whatif": ("self", 0.35),
    "era": ("zoom", 0.3),
    "describe": ("slide_left", 0.28),
    "features": ("cut", 0),
    "meta": ("cut", 0),
    "nos": ("zoom", 0.3),
    "idea": ("blur", 0.3),
    "end": ("zoom", 0.3),
}

# key moments
APP_HITS = [0.50, 1.14, 2.24]
NOTIF_T = [3.15, 3.45, 3.75, 4.05, 4.30, 4.52, 4.72]
ANY_T = 6.38
ERA_WORDS = [7.99, 8.31, 8.45, 8.84]
VIBE_T = 9.0
SHIMMER_T = 9.55
CAPTION_T = 10.0
DRAG_T, DESCRIBE_T = 11.04, 12.5
DIAMOND_T = 11.75
MORPH_T = 12.3
PROMPT = "Make it smooth, fast & aesthetic."
TYPE_T0, TYPE_T1 = 12.75, 14.2
ENTER_T = 14.42
IRIS_T0, IRIS_T1 = 14.5, 14.95
SMOOTH_T, TRANSITIONS_T = 15.0, 15.38
IRIS2_T0, IRIS2_T1 = 16.0, 16.4
KINETIC_T, TYPE_WORD_T = 16.4, 16.62
SOUND_PUSH_T = 17.12
SOUND_T, DESIGN_T = 17.22, 17.55
MONTAGE = [(18.5, "Captions."), (19.0, "Color."), (19.5, "Motion."), (20.0, "Music.")]
EVEN_T, FRAME_T, SOUND2_T, PROMPT2_T = 20.5, 21.72, 22.09, 22.56
PROMPT2 = "make a 40s apple-style video about vibe editing"
PROMPT2_T0, PROMPT2_T1 = 22.75, 23.85
NO_T = [25.0, 26.04, 26.81]
IDEA_WORDS = [28.5, 28.74, 28.95]
WORDS_LINE = "and the words to describe it."
WORDS_T0, WORDS_T1 = 29.53, 30.75
WELCOME_T, LOGO_T, LOGO_SHIMMER_T = 32.5, 33.0, 33.5
TAGLINE_T = 34.2
STRIKES = [35.4, 35.65, 35.9, 36.15]
FINAL_HIT = 37.0
FADE_T0, FADE_T1 = 38.8, 39.8


def type_times(text, t0, t1):
    """per-character reveal times between t0 and t1 (spaces/punctuation slightly longer)."""
    weights = [1.6 if ch in " ,.&" else 1.0 for ch in text]
    tot = sum(weights)
    out, acc = [], 0.0
    for w in weights:
        out.append(t0 + (t1 - t0) * acc / tot)
        acc += w
    return out
