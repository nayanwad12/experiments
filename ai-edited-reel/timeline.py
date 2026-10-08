"""timeline: the single source of truth for ai-edited-reel.

Times are seconds on the CUT timeline (work/cut.mp4, words in work/words_cut.json).
Picture (scene.py) and sound (scene.py audio) both read from here.
"""

W, H = 1080, 1920          # 9:16 Reel
FPS = 30
SPEECH_END = 46.10         # last spoken word ends here (cut video length 46.14 s)
DURATION = 47.0            # + a short hold on the end card
MOOD = "upbeat"
SEED = 11

# (start, end, scene, layout)   layout: full = face full screen, gfx = graphics only,
#                                       card = face in a paper card, bubble = graphics + face circle top-right
SCENES = [
    (0.00, 3.36, "hook", "full"),      # "The video is fully edited and I didn't touch it."
    (3.36, 8.62, "pain", "gfx"),       # "Editing takes forever. Cutting, captions, music, zooms, it eats your whole day."
    (8.62, 10.72, "built", "card"),    # "So I built my own editing system."
    (10.72, 15.62, "step1", "bubble"), # "Step 1: I record on my phone. One take and mistakes are fine."
    (15.62, 22.52, "step2", "bubble"), # "Step 2: I tell my system what I want in normal words. Like make it fun, ..."
    (22.52, 28.84, "step3", "full"),   # "Step 3, it edits everything. The cuts, the captions, the zooms. The music."
    (28.84, 31.32, "nos", "gfx"),      # "No editing app, no editor, no skills."
    (31.32, 33.88, "talk", "card"),    # "If you can talk, you can make videos like this."
    (33.88, 38.42, "proof", "gfx"),    # "This video was made exactly like that. So is every video on this page."
    (38.42, 42.56, "open", "card"),    # "So I'm opening up to a few creators who want to see how it works."
    (42.56, DURATION, "cta", "cta"),   # "So comment down system or just tap the link below."
]
TRANSITION = 0.32

# word-synced cues (cut timeline)
CUE = dict(
    stamp=1.52, stamp_fly=2.40,
    editing=3.44, takes=3.92, forever=4.24,
    cutting=4.96, captions=5.36, music=5.92, zooms=6.48, day=7.04,
    one_take=13.28, mistakes=14.24,
    normal_words=18.24, type_start=19.28, type_end=22.10, send=22.25,
    s3_cuts=24.72, s3_captions=25.52, s3_zooms=26.78, s3_zoom_back=27.95, s3_music=28.20,
    no1=28.92, no2=29.80, no3=30.68,
    talk=31.80, make_this=32.44, this=33.32,
    receipt=33.95, every=36.45, page=37.70,
    few=40.18, how=41.46,
    comment=42.90, system=43.78, link=44.72,
)

# "the receipt": real numbers from this edit (see work/edl.json and work/words_cut.json)
RECEIPT = [
    ("RAW TAKE", "49.2s"),
    ("CUTS MADE", "5"),
    ("DEAD AIR REMOVED", "3.1s"),
    ("FRAMES STABILISED", "1,477"),
    ("CAPTION WORDS", "131"),
    ("SCENES DESIGNED", "11"),
    ("TIMELINE OPENED", "0"),
]
