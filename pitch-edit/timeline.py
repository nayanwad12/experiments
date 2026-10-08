"""timeline: the single source of truth for pitch-edit v2 (times on the CUT timeline, see work/edl60.json)."""

W, H = 1080, 1920
FPS = 60
SRC_FPS = 60
SPEECH_END = 33.10
DURATION = 34.3
MOOD = "tech"
SEED = 21

# (start, end, scene, layout)  layout: full = footage full frame, explainer = graphics + face circle top-right
SCENES = [
    (0.00, 2.20, "hook", "full"),          # This video is fully edited and I didn't touch it.
    (2.20, 3.30, "forever", "explainer"),  # Editing takes forever.
    (3.30, 6.75, "pain", "explainer"),     # Cutting, captions, music, zooms. It eats your whole day.
    (6.75, 8.02, "built", "explainer"),    # So I've built my own system.
    (8.02, 11.46, "step1", "explainer"),   # Step 1: I record on my phone. One take and mistakes are fine.
    (11.46, 16.82, "step2", "explainer"),  # Step 2: I tell my system what I want in normal words. Like make it fun...
    (16.82, 20.48, "step3", "full"),       # Step 3: it edits everything. The cuts, the captions, the zooms, the music.
    (20.48, 22.48, "nos", "explainer"),    # No editing app, no editor, no skills.
    (22.48, 24.26, "talk", "full"),        # If you can talk, you can make videos like this.
    (24.26, 27.20, "cover", "full"),       # This video was made exactly like that. So is every video on my page.
    (27.20, 29.12, "open", "explainer"),   # And I'm opening it up to a few creators.
    (29.12, DURATION, "cta", "full"),      # If you want to see how it works, comment system ... tap the link below.
]
ZOOM_T = 0.40          # zoom transition length

CUE = dict(
    fully=0.64, edited=0.96,
    editing=2.24, takes=2.64, forever=2.96,
    cutting=3.36, captions=3.84, music=4.40, zooms=5.04, day=5.60,
    so=6.80, my_own=7.36, system=7.68,
    record=8.88, phone=9.44, one_take=9.84, mistakes=10.64,
    tell=12.24, normal=13.76, type_start=14.64, type_end=16.70, send=16.62,
    it_edits=17.68, s3_cuts=18.48, s3_captions=19.04, s3_zooms=19.68, s3_zoom_back=20.02, s3_music=20.16,
    no1=20.56, no2=21.36, no3=21.92,
    talk=22.88, make_this=23.44,
    exactly=25.12, every=26.24, page=26.88,
    few=28.24, creators=28.48,
    how=29.20, comment=30.64, cta_system=31.04, tap=32.24,
)
