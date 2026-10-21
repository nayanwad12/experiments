# science-talk-2: "Gut health se psoriasis" (video 2)

A 7 min 9 s teleprompter take (Hindi, vertical 4K phone footage) cut into a natural **2 min 34 s** Reel/Short
(1080x1920, 30 fps). Same edit brief as `../science-talk` (last complete take of every line, no dead air, 1.2x,
white kinetic Hinglish captions, some behind the speaker, motion graphics, science images, music + SFX), but in
a **mature, editorial look**: no emoji, no stickers or stamps.

## Look

- **Thin-line icons** (Tabler, MIT, `assets/lineicons`) that draw on stroke by stroke, never cartoon emoji.
- **Mono lower-third tags** (JetBrains Mono, wipe reveal), **serif italic quotes** (Instrument Serif) with a
  hairline rule, **editorial headlines** rising out of a mask line, Anton for the giant words behind the speaker.
- **Museum-plate photos:** hairline frame, mask reveal, slow push, mono caption. Uses skin histology (H&E) and a
  procedural SEM-style micrograph of gut bacteria (`make_bacteria.py`, captioned as an illustration).
- **Restrained palette:** white on charcoal, teal for "good", soft red for "bad", gold for Ayurveda. A light
  filmic grade on the footage, warm for the mummy story.
- Captions are white Inter Tight 800: word by word, key words slightly larger with a hairline underline.

## Beats (all cued off the spoken words)

Hook: GUT HEALTH / PSORIASIS behind the head, then the quote "Pet theek nahi, to chamdi ka kya ilaaj?", then
AADHA THEEK. Studio: the gut microbiome plate (achhe / bure), the gut-skin axis (gut and skin plates joined by
a straight line), the 2025 research (the micrograph dims as good bacteria drop, *Faecalibacterium* marked
anti-inflammatory), INFLAMMATION, 70% with a 10x10 dot matrix of immune cells, then the chain gut kharab →
immunity kharab → skin par attack. The four fixes: 01 Fiber (sabzi / phal / daal / chhilke ka aata),
02 Probiotics (dahi / kanji / ghar ka achaar, fermented food), 03 Prebiotics (*Lahsun · Pyaaz · Kela*,
fertilizer), 04 Antibiotics (only when the doctor says). Studio: *Ayurveda* → AGNI · digestive fire →
"Agni theek = Gut health theek". Mummy: dahi roz → gut → skin, COINCIDENCE NAHI, "Ilaaj sirf cream mein nahi".
CTA: PART 4 (Vitamin D / Sunlight / Moisturizer), a minimal comment box, SCIENCE / DECISION AAPKA.

## Run

Same pipeline as video 1 (`../science-talk/README.md`). The scripts here: `asr.py --fine`, `script.py`
(the story edit), `cut.py`, `matte.py`, `make_bacteria.py`, `edit2.py stills|render|srt`, `sound.py`, then
mux `work/picture.mp4` + `work/mix.wav`.
