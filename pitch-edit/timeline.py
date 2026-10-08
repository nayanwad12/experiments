"""timeline: the single source of truth for pitch-edit (times on the CUT timeline, work/cut.mp4)."""

W, H = 1080, 1920
FPS = 30
SPEECH_END = 43.40
DURATION = 44.6
MOOD = "upbeat"
SEED = 21

# (start, end, scene, kind)  kind: full = footage full frame, gfx = graphics only, cover = magazine cover
SCENES = [
    (0.00, 2.56, "hook", "full"),        # This video is fully edited and I didn't touch it.
    (2.56, 4.02, "forever", "full"),     # Editing takes forever.
    (4.02, 9.24, "pain", "gfx"),         # Cutting, captions, music, zooms, it eats your whole day.
    (9.24, 11.16, "built", "full"),      # So I've built my own system.
    (11.16, 15.24, "step1", "full"),     # Step 1. I record on my phone. One take and mistakes are fine.
    (15.24, 22.20, "step2", "gfx"),      # Step 2. I tell my system what I want in normal words. Like make it fun...
    (22.20, 27.34, "step3", "full"),     # Step 3. It edits everything. The cuts, the captions, the zooms, the music.
    (27.34, 29.82, "nos", "gfx"),        # No editing app, no editor, no skills.
    (29.82, 32.38, "talk", "full"),      # If you can talk, you can make videos like this.
    (32.38, 36.14, "cover", "cover"),    # This video was made exactly like that. So is every video on my page.
    (36.14, 38.54, "open", "full"),      # And I'm opening it up to a few creators.
    (38.54, DURATION, "cta", "full"),    # If you want to see how it works, comment system ... tap the link below.
]
WIPE = 0.40

CUE = dict(
    fully=0.64, edited=1.04, touch=1.60,
    editing=2.64, forever=3.44,
    cutting=4.16, captions=4.80, music=6.00, zooms=7.18, day=7.74,
    my_own=10.14, system=10.62,
    record=12.46, one_take=13.58, mistakes=14.38,
    normal=17.90, type_start=19.10, type_end=21.80, send=21.95,
    it_edits=23.34, s3_cuts=24.30, s3_captions=25.02, s3_zooms=25.82, s3_zoom_back=26.40, s3_music=26.70,
    no1=27.42, no2=28.30, no3=29.02,
    talk=30.30, make_this=31.10,
    exactly=33.34, every=34.86, page=35.58,
    few=37.50, creators=37.74,
    how=39.50, comment=40.46, cta_system=40.94, tap=42.20,
)
