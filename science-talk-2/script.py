"""Video 2 (gut -> psoriasis), the story edit: kept source ranges (best / last complete take of every line)
+ Hinglish caption text.

`^word` = emphasised caption word. Times are source seconds in raw/take.mp4 (from the Whisper passes,
checked by decoding both sides of every cut). Everything between the ranges (retakes, teleprompter pauses,
false starts, "um"s) is dropped; the rest is played at 1.2x.
"""
import json
import re
from pathlib import Path

import timing

HERE = Path(__file__).resolve().parent
SPEED = 1.2
FPS = 30
PRE, POST = 0.06, 0.12        # padding around speech (source seconds)
MAX_GAP = 0.20                # longest pause kept between two ranges (source seconds)

SEGMENTS = [
    # ---- hook
    ("hook1", 0.65, 12.34, "Agar main kahoon ki ^gut health agar aap logon ki theek nahi hai, uski wajah se ^psoriasis "
                           "hai aap logon ko, to kya aap log maanoge? Aap logon ko lag raha hoga ki yaar ye to pagal "
                           "aadmi hai, kaise keh raha hai ki pet theek nahi hai to usse ^chamdi ka kya hi ilaaj ho "
                           "sakta hai."),
    ("hook2", 12.97, 13.36, "Theek hai?"),
    ("hook3", 13.96, 15.86, "But main aap logon ko bata raha hoon, ^gut"),
    ("hook4", 15.98, 16.44, "health"),
    ("hook5", 16.62, 20.50, "sahi ho jaayegi aap logon ki, to psoriasis ^aadha theek ho jaayega aapka wahin."),
    # ---- the gut-skin axis (third take)
    ("axis1", 49.06, 53.88, "Aapke pet mein ^kharbon bacteria rehte hain, achhe bhi hote hain, bure bhi hote hain,"),
    ("axis2", 54.06, 55.99, "jinko ^gut microbiome kehte hain."),
    ("axis3", 56.55, 60.88, "In bacteria aur aapki chamdi ke beech mein ek ^seedhi line hai."),
    ("axis4", 62.02, 64.21, "Aur science isko kehti hai ^gut-"),
    ("axis5", 64.33, 65.59, "^skin axis."),
    # ---- what the research found
    ("res1", 140.78, 150.23, "Psoriasis patient ke gut mein kya kya cheezein hoti hain? Jaise ^2025 ki research mein, "
                             "achhe bacteria ^ghat jaate hain,"),
    ("res2", 108.84, 112.30, "jisko specifically ^Faecalibacterium kehte hain."),
    ("res3", 162.82, 174.24, "Ye ^anti-inflammatory bacteria hai. Ye khatam hua, to poori body mein ^inflammation "
                             "badh jaati hai. Aur ^70% immune cells aapke gut mein hi hain. 70% ki baat kar raha "
                             "hoon main."),
    ("res4", 181.54, 185.30, "Matlab ki gut kharab, to ^immunity to automatically kharab."),
    ("res5", 185.61, 188.66, "To chamdi par ^attack jaayaz hai."),
    # ---- four fixes (second take)
    ("fix1", 224.71, 231.93, "Agar gut theek karna hai, to simple si ^chaar cheezein bata raha hoon, usko achhe tareeke "
                             "se follow kar lena. Number one:"),
    ("fix2", 232.01, 239.32, "^fiber khaana bahut zaroori hai. Sabzi, phal, daalein, chhilke wala aata, ye saari "
                             "cheezein khaana zaroori hai."),
    ("fix3", 239.40, 246.46, "Fiber ^achhe bacteria ka khaana hai, samajh rahe ho aap? Unko agar nahi khilaoge aap, to "
                             "wo aapko bachayenge nahi."),
    ("pro1", 251.05, 260.38, "Number two: ^probiotics, yaani ki dahi. Fresh ^dahi roz khaiye, ^kanji, achaar, ghar ka "
                             "ek achaar hota hai,"),
    ("pro2", 260.46, 267.84, "market wala nahi. ^Fermented food ki baat kar raha hoon main. Jo fermented food hote hain, "
                             "wo gut bacteria ko aur zyada badha dete hain."),
    ("pre1", 299.88, 300.95, "Number three:"),
    ("pre2", 301.13, 303.51, "^prebiotics, jaise ki lahsun,"),
    ("pre3", 303.75, 308.08, "pyaaz, kela. Ye achhe bacteria ke liye ^fertilizer type kaam karte hain."),
    ("anti1", 313.42, 322.65, "Number four: ye cheez band kar dijiye. ^Antibiotics bina zaroorat ke mat lijiye. Ye "
                              "achhe bacteria ko ^maar dete hain."),
    ("anti2", 322.82, 329.88, "Aur jab tak ^doctor ne nahi bola, tab tak to ekdam nahi lena hai. ^Ayurveda mein kehte "
                              "hain ki agni theek hai,"),
    ("agni1", 330.12, 337.92, "to sab theek. Yaani ki jo paachak aapki theek hai, paachak ^agni theek hai, yaani ki "
                              "^digestive fire jisko kehte hain,"),
    ("agni2", 337.99, 343.48, "wo theek, to saari cheezein theek. Yaani ki ^gut health theek, to saari cheezein theek. "
                              "Same baat, bas"),
    ("agni3", 343.88, 345.01, "alag-alag bhaasha mein hai."),
    # ---- mom
    ("mom1", 351.85, 359.71, "Meri ^mummy ne dahi khaana jab roz shuru kiya, to pehle ^gut sudhra, phir pairon ki "
                             "^skin dheere dheere sahi hona shuru hui."),
    ("mom2", 359.78, 370.27, "Aur ^coincidence nahi tha. Ye gut-skin axis kaam kar raha tha, tabhi ye saari cheezein "
                             "theek ho rahi thi. Psoriasis ka ilaaj sirf ^cream mein nahi, ki cream lagaya aur sahi ho "
                             "gaya."),
    ("mom3", 370.34, 375.12, "^Pet ke andar jaakar ke saari cheezein sahi karni padti hain."),
    # ---- CTA (last takes)
    ("cta1", 394.12, 403.04, "^Part 4 mein bataunga ki chamdi ka dhyaan kaise rakhein. ^Vitamin D kitna hai, "
                             "^sunlight, moisturizer, ye saari cheezein kitni hain,"),
    ("cta2", 403.11, 410.04, "ye saari cheezein main bataunga aap logon ko Part 4 mein. Comment kariye ^\"PART 4\". "
                             "Mera kaam tha ^science pahunchana, ^decision aapka hai."),
    ("cta3", 424.95, 428.03, "You're watching Fit Influencer, milte hain next video mein."),
]


def build():
    """-> cuts [(src_a, src_b, out_a, n_frames)], segs {key: (src_a, src_b)}, words [{w,s,e,big,key}] (output time)"""
    tight = []
    for key, a, b, txt in SEGMENTS:
        s, e = timing.speech_bounds(a, b)
        tight.append([key, max(a - 0.05, s - PRE), min(b + 0.05, e + POST), txt])
    # merge ranges that sit close together in the source (natural micro pauses survive, capped)
    cuts = []
    for key, a, b, txt in tight:
        if cuts and -0.3 <= a - cuts[-1][1] <= MAX_GAP:
            cuts[-1][1] = b
        else:
            if cuts and cuts[-1][0] <= a < cuts[-1][1]:      # overlapping forward range: start after it
                a = cuts[-1][1]
            cuts.append([a, b])
    out, t = [], 0.0
    for a, b in cuts:
        n = max(1, int(round((b - a) / SPEED * FPS)))
        b = a + n * SPEED / FPS
        out.append((round(a, 4), round(b, 4), round(t, 4), n))
        t += n / FPS
    words = []
    for key, a, b, txt in tight:
        for w, s, e in timing.words(a + PRE * 0.5, b - POST * 0.6, txt):
            big = w.startswith("^")
            disp = w.lstrip("^").replace('"', "")
            disp = re.sub(r"[.,:;]+$", "", disp)
            if disp == "...":
                continue
            words.append(dict(w=disp, s=src2out(out, s), e=src2out(out, e), big=big, key=key, raw=w))
    return out, {k: (a, b) for k, a, b, _ in tight}, words, t


def src2out(cuts, ts):
    for a, b, o, n in cuts:
        if a - 1e-6 <= ts <= b + 1e-6:
            return round(o + (ts - a) / SPEED, 4)
    best = min(cuts, key=lambda c: min(abs(ts - c[0]), abs(ts - c[1])))
    a, b, o, n = best
    return round(o + (min(max(ts, a), b) - a) / SPEED, 4)


if __name__ == "__main__":
    cuts, segs, words, total = build()
    (HERE / "work").mkdir(exist_ok=True)
    json.dump(dict(cuts=cuts, words=words, total=total, speed=SPEED, fps=FPS), open(HERE / "work" / "edl.json", "w"), indent=1)
    src = sum(b - a for a, b, _, _ in cuts)
    print(f"{len(cuts)} cuts, {src:.1f}s source -> {total:.1f}s output ({int(total // 60)}:{total % 60:04.1f}), "
          f"{len(words)} words")
