"""The script: 6 scenes. Each line is split into phrases so the voice can be synthesised phrase by
phrase, which gives exact cue times for the visuals. voice.py writes out/cues.json: per scene its start,
its length (the take plus a tail, snapped up to the beat grid so every cut lands on the music) and the
phrase start times."""

N = 6
BPM = 128
BEAT = 60 / BPM
GRID = BEAT * 2       # scene lengths snap up to half bars
VOICE_IN = 0.12       # narration starts this far into each scene
VOICE = "am_michael"  # Kokoro voice: deep US male
SPEED = 1.16          # brisk read
PAUSE = 0.5           # scale on the written pauses below
TAIL = [0.55, 0.75, 0.75, 1.25, 0.9, 3.4]   # breathing room after each take (scene 6 holds the ending)

# (phrase, pause after in seconds). Names are respelled for the TTS (Movie-ola, Kar-PATHY).
LINES = [
    [("For a hundred years, editing a video meant one gesture.", 0.30),
     ("The cut.", 0.55),
     ("Now the cut is becoming a sentence.", 0.0)],
    [("In nineteen twenty-four, editors cut film by hand on a Movie-ola.", 0.40),
     ("In nineteen eighty-nine, Avid moved the cut onto screens.", 0.0)],
    [("Then, in February twenty twenty-five,", 0.15),
     ("Andrej Kar-PATHY coined vibe coding.", 0.35),
     ("Describe what you want, and let A.I. write the code.", 0.0)],
    [("Vibe editing is the same idea, for video.", 0.35),
     ("You type: cut the pauses, add captions, make it punchy.", 0.25),
     ("It happens.", 0.0)],
    [("But here's the catch.", 0.30),
     ("The software can make a thousand cuts.", 0.30),
     ("It still can't tell which one actually matters.", 0.0)],
    [("So the cut didn't disappear.", 0.30),
     ("It moved, from your hands, to your words.", 0.45),
     ("The editor is still you.", 0.0)],
]

SOURCES = [
    ("Moviola, the first film-editing machine (1924)", "https://en.wikipedia.org/wiki/Moviola"),
    ("Iwan Serrurier, inventor of the Moviola", "https://en.wikipedia.org/wiki/Iwan_Serrurier"),
    ("Avid Media Composer, sold from NAB 1989", "https://en.wikipedia.org/wiki/Media_Composer"),
    ("Non-linear editing and the arrival of Avid", "https://broadcastbeat.com/news/non-linear-editing-and-the-arrival-of-avid"),
    ("Karpathy's 'vibe coding' post, 2 Feb 2025", "https://knowyourmeme.com/memes/vibe-coding"),
    ("'Vibe coding' named Collins Word of the Year 2025", "https://www.lbc.co.uk/tech/vibe-coding-clanker-word-of-the-year-collins"),
    ("What vibe editing is", "https://pexo.ai/vibe-hub/vibe-editing"),
    ("Prompt-based video editing in practice", "https://www.kapwing.com/resources/how-to-edit-videos-with-ai-prompts-prompts-included/"),
]
