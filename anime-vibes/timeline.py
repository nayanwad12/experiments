"""Every timing shared by picture and sound. The score is 150 BPM (beat 0.4 s) from t=0, and the
scene cuts and the big hits sit on that grid."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 40.0
BPM = 150
BEAT = 60 / BPM

# scene name -> (start, end)
SCENES = [
    ("city",   0.0, 5.6),    # cinematic neon rain
    ("manga",  5.6, 10.4),   # black & white manga panels
    ("chibi",  10.4, 14.8),  # super-deformed comedy
    ("spirit", 14.8, 19.6),  # pastel fantasy, the vibe spirit
    ("power",  19.6, 25.6),  # shonen power-up + impact frame
    ("mecha",  25.6, 30.4),  # mecha / cyber HUD
    ("shojo",  30.4, 35.2),  # shojo sparkle
    ("title",  35.2, 40.0),  # opening-credits end card
]
STYLE_TAG = {
    "city": "CINEMATIC", "manga": "MANGA", "chibi": "CHIBI", "spirit": "FANTASY",
    "power": "SHONEN", "mecha": "MECHA", "shojo": "SHOJO", "title": "OPENING",
}

# VO phrase -> start time (s)
VO_AT = {
    "world1": 0.7, "world2": 3.25,
    "dead": 5.85, "clips": 7.4, "sleep": 9.0,
    "chibi1": 10.55, "chibi2": 12.75,
    "spirit1": 15.35, "spirit2": 17.65,
    "epic": 20.0, "emo": 20.85, "beat": 21.65, "vibe": 22.65, "edit": 23.56,
    "cuts": 25.8, "color": 26.6, "caps": 27.4, "music": 28.3, "synced": 29.1,
    "sugoi": 31.0, "client": 33.0,
    "title": 35.6, "say": 37.05, "alive": 38.15,
}
IMPACT = 23.6   # the "EDIT!" impact frame / drop

_vo = None


def vo():
    global _vo
    if _vo is None:
        p = os.path.join(HERE, "work", "vo.json")
        _vo = json.load(open(p)) if os.path.exists(p) else {}
    return _vo


def vo_end(k):
    return VO_AT[k] + vo().get(k, {}).get("dur", 1.0)


def scene_at(t):
    for name, a, b in SCENES:
        if a <= t < b:
            return name, a, b
    return SCENES[-1]


if __name__ == "__main__":
    for k, t in VO_AT.items():
        print(f"{k:8s} {t:6.2f} -> {vo_end(k):6.2f}")
