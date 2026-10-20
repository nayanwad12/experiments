"""The story edit: kept source ranges (best / last complete take of every line) + Hinglish caption text.

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
    ("hook1", 0.84, 3.80, "Sirf ^EK cheez par agar aap logon ne bhi kaabu paa liya na,"),
    ("hook2", 4.36, 6.45, "to aap logon ka bhi ^psoriasis khatam ho sakta hai."),
    ("hook3", 6.70, 8.15, "Aur wo hai... ^STRESS."),
    ("hook4", 9.06, 11.48, "Aur ye sirf main mann ki baat nahi bol raha hoon,"),
    ("hook5", 11.72, 13.30, "ye ^body ki baat hai,"),
    ("hook6", 13.58, 14.32, "jo ki"),
    ("hook7", 14.60, 16.18, "^science prove karti hai."),
    ("hook8", 17.67, 19.16, "Stress aapki ^chamdi"),
    ("hook9", 19.30, 20.85, "ko tod deti hai. ^Literally."),
    # ---- mechanism (third take, the complete one)
    ("mech1", 57.32, 59.44, "Jab aap stress mein hote ho, to ^brain"),
    ("mech2", 59.85, 66.94, "^cortisol release karta hai, aur ye emergency hormone hai. Cortisol ^immune system ko "
                            "bigaadta hai, ^T-cells overactive ho jaate hain."),
    ("mech3", 67.24, 71.67, "Aur wahi T-cells jo psoriasis mein ^chamdi par attack kar rahe the, wahi..."),
    ("mech4", 72.33, 73.43, "unhi ki baat kar raha hoon main."),
    # ---- the loop
    ("loop1", 73.80, 74.93, "To ^stress aaya,"),
    ("loop2", 75.46, 76.44, "to ^cortisol aaya,"),
    ("loop3", 76.58, 77.62, "cortisol aaya"),
    ("loop4", 77.90, 83.48, "to ^immune system bigda, immune system bigda to ^flare aaya, flare aaya to aapko aur "
                            "^stress hua..."),
    ("loop5", 84.10, 85.14, "\"Phir se ho gaya!\""),
    ("loop6", 85.48, 90.10, "\"Log kya sochenge? Ab theek kaise hoga?\" Aur ye saari cheezein ise aur zyada"),
    ("loop7", 90.57, 91.32, "badha deti hain."),
    ("loop8", 91.66, 93.20, "To ye ^loop hai, poora ka poora."),
    ("loop9", 93.45, 99.35, "Aur loop jaise jaise banega, ^stress, ^flare, stress, flare, stress, flare ka loop "
                            "banta chala jaayega."),
    ("loop10", 99.56, 103.06, "Jab tak aap isko ^todoge nahi, tab tak ye chalta rahega."),
    # ---- fix 1: breathing (second take)
    ("fix1", 132.30, 140.09, "Aur loop ko todna hai to ^teen cheezein rozana karni padengi. Number one: ^saans leni "
                             "padegi achhe tareeke se, ^6 saans"),
    ("fix2", 140.17, 141.24, "per minute."),
    ("fix3", 141.45, 148.83, "Yaani ki ^4 second saans andar, ^6 second tak saans bahar. ^Vagus nerve ko activate "
                             "kar deti hai."),
    ("fix4", 149.03, 159.48, "Theek? To cortisol isse ^gir jaata hai. Log kehte hain na ^box breathing karna. To box "
                             "breathing mein kya hota hai ki 4 second saans lete hain, phir 4 second hold karte hain, "
                             "phir 4 second saans chhodte hain, phir 4 second hold karte hain."),
    ("fix5", 159.56, 168.60, "To is tareeke se agar aap log, jo main bata raha hoon, saans agar achhe tareeke se "
                             "lenge, to aap logon ka ^cortisol level theek rehna shuru ho jaayega."),
    ("fix6", 172.55, 177.62, "Aur ye din bhar nahi karna hai aapko. Din mein ^do-teen baar, ^paanch-paanch minute "
                             "ke liye kar lijiye."),
    ("fix7", 183.37, 189.88, "Ho jaayega aap logon ka kaam. Number two: ^exercise. Exercise is the most important "
                             "thing."),
    # ---- fix 2: exercise
    ("ex1", 190.28, 196.63, "^2025 ki meta-analysis mein ^yoga sabse effective bataya gaya tha cortisol reducer"),
    ("ex2", 197.45, 199.28, "ke taur par."),
    ("ex3", 212.58, 223.48, "^Qigong tha isme number two par, aur ^walking thi number three par. Aur walking, normal "
                            "walking nahi, ^brisk walking ki baat kar raha hoon main. Thoda tez chalna, jisme aapki "
                            "dil ki dhadkan thodi si tez ho normal se."),
    ("ex4", 224.62, 233.88, "Aur isme zaroori nahi ki aapko gym jaana zaroori hai, but ^weight uthana important hai. "
                            "Chahe aap ghar par do dumbbell leke weight uthao,"),
    ("ex5", 233.96, 241.02, "chahe aap bodyweight exercise kar lo, yoga kar lo, ^20-30 minute. Psoriasis ke liye ye "
                            "saari cheezein ^dawai hain."),
    # ---- fix 3: sleep (second take)
    ("sleep1", 261.16, 265.88, "Number three: ^neend. Saat se aath ghante ki neend ^non-negotiable hai."),
    ("sleep2", 266.15, 274.33, "Theek? ^Sleep deprivation ki wajah se cortisol aur zyada badh jaata hai. Cortisol "
                               "badha to ^flare aur zyada badh jaata hai. Simple si cheez hai."),
    # ---- payoff
    ("recap", 306.42, 316.48, "In ^teeno cheezon se cortisol level girta hai, aur cortisol gira to immune system "
                              "dheere dheere dheere ^shaant ho jaata hai. Immune system shaant hua, to ^skin shaant "
                              "ho gayi."),
    # ---- mom's story (complete take)
    ("mom1", 335.56, 347.00, "To meri ^mummy ko jo sabse zyada stress hota tha, wo hota tha sabse zyada ^pair "
                             "dikhane mein. Theek? Ghar mein mehmaan aaye to pair chhupane lagti thi, ^mandir jaati "
                             "thi to pair chhupane lagti thi, chappal utaare"),
    ("mom2", 347.08, 354.56, "to uska darr ki yahan bhai sahab kuch aur na lag jaaye. Jab ^stress manage kiya gaya, "
                             "to ^flare dheere dheere kam hua."),
    ("mom3", 354.95, 361.00, "Aur jab flare kam hua, to stress already kam ho gaya. Theek? To loop ^ulta chal gaya, "
                             "samajh rahe ho aap?"),
    # ---- close + CTA (last takes)
    ("close1", 399.08, 410.45, "Aur agar loop todna hai, to kisi ^ek jagah se shuru karna padega. Pehle ^saans se "
                               "shuru karo, phir dheere dheere ^yoga karna shuru karo, aur ^neend to abhi se hi sahi "
                               "karna shuru kar dijiye."),
    ("cta1", 412.74, 420.48, "Agar aap logon ko jaanna hai ki ^dawaiyan kahan se li maine, kya kya cheezein aur bhi ki"),
    ("cta2", 420.55, 435.29, "jisse hamara psoriasis theek hua, to uske liye likhiye aap log ^\"PART 3\". Part 3 mein "
                             "main bata doonga ki kahan se maine dawai li, aur us company ke saath ^collab bhi karke "
                             "main dikhaunga aap logon ko ki wo log kaise psoriasis theek kar rahe hain,"),
    ("cta3", 435.37, 442.56, "aur aap kis tareeke se unse ilaaj karwa sakte ho. Mera kaam tha ^science pahunchana, "
                             "^decision aapka hai. You're watching Fit Influencer, milte hain"),
    ("cta4", 442.66, 443.44, "next video mein."),
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
        if cuts and 0 <= a - cuts[-1][1] <= MAX_GAP:
            cuts[-1][1] = b
        else:
            if cuts and a < cuts[-1][1]:
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
