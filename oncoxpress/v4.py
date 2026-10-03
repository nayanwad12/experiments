"""v4 re-edit of the finished v3 film (no source re-render needed).

New timeline (seconds), built from the v3 film plus new material:
  [ 0.000, 28.750)  v3 film as-is
  [28.750, 29.850)  v3 doctors shot, cropped above the old lower-third (preview, ~1.1 s)
  [29.850, 34.600)  doctor cards: Dr Shyam Aggarwal, then Dr Aditya Sarin (mg)
  [34.600, 74.300)  v3 film [32.70, 72.40)
  [74.300, 89.000)  "And this is just the beginning… coming soon" (clip 11 + mg)
  [89.000, 96.600)  v3 film [72.40, 80.00) — end card
Narration: v3 voice stem re-ordered to "…of Dr Shyam Agrawal and Dr Aditya Sarin" (the corrected take),
so it follows the cards, then a pause for the cards, and the new paragraph at 74.75.
"""
FPS = 24
DUR = 96.6
NF = int(round(DUR * FPS))

# voice edit (v3 film seconds)
CUT_A0, CUT_A1 = 30.035, 31.235     # old "Dr Aditya Sarin" -> replaced
SNIP_LEN = 1.80                      # corrected take
PAUSE_AT, PAUSE = 32.70, 1.30        # after the names
# the names are swapped to match the cards: old "and" and "Dr Shyam Agrawal," (v3 seconds)
AND_0, AND_1 = 31.235, 31.42
SHYAM_0, SHYAM_1 = 31.42, 32.46
SWAP_GAP = 0.06
# v4 seconds of the re-ordered names (for subtitles and cards)
SHYAM_AT = CUT_A0
AND_AT = SHYAM_AT + (SHYAM_1 - SHYAM_0) + SWAP_GAP
ADITYA_AT = AND_AT + (AND_1 - AND_0)
SPLIT_V = 72.40                      # end of "…under 60 seconds."
SOON_AT = 74.75                      # new paragraph start (new seconds)
SOON_LEN = 13.714
END_AT = 89.0                        # v3 end card resumes here

D1 = (CUT_A0 + SNIP_LEN) - CUT_A1    # +0.60
D2 = D1 + PAUSE                      # +1.90
D3 = END_AT - SPLIT_V                # +16.60

# picture
PREVIEW = (28.75, 29.85)
DOCS = (29.85, 34.60)
SOON = (74.30, 89.00)
CROP_H = 770                         # doctors preview: keep y < 770 (old lower-third sits below)


def warp(t, split_end=SPLIT_V):
    """v3 film time -> v4 time (for music/SFX events and words). Events from the end card (>= split_end) jump
    past the new section."""
    if t < CUT_A0:
        return t
    if t < CUT_A1:
        return CUT_A0 + (t - CUT_A0) * SNIP_LEN / (CUT_A1 - CUT_A0)
    if t < PAUSE_AT:
        return t + D1
    if t < split_end:
        return t + D2
    return t + D3


def old_frame_of(fi):
    """v4 frame index -> (v3 frame index, crop?) or None when the frame is new material."""
    t = fi / FPS
    if t < PREVIEW[0]:
        return fi, False
    if t < PREVIEW[1]:
        return fi, True
    if t < DOCS[1]:
        return None
    if t < SOON[0]:
        return int(round((t - D2) * FPS)), False
    if t < SOON[1]:
        return None
    return min(int(round((t - D3) * FPS)), 1919), False
