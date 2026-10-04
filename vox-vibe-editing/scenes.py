"""The six 10-second scenes. Each scene is f(canvas, t_local, cues) where cues are the narration
phrase start times for that scene (out/cues.json), so every visual hit lands on its words.
Each scene also lists its sound effects (same cue maths) in SFX."""

import math

import skia

import cutouts as K
from design import (CORAL, CREAM, H, INK, NAVY, NAVY_L, TEAL, W, WHITE, YELLOW, YELLOW_D, Cam, R, clamp,
                    dashed_cut, draw_bg, eic, eob, eoc, font, gpaint, highlight, lerp, marker, marker_arrow,
                    marker_check, marker_circle, marker_underline, paper_paint, paper_rect, paper_rrect, pop,
                    prog, rgb, rough_poly, path_of, scribble_question, shadow, smooth, tag, tape, text)

BG = [YELLOW, NAVY, CREAM, YELLOW, NAVY, CREAM]


def camera(c, sc=1.0, dx=0.0, dy=0.0, rot=0.0, cx=W / 2, cy=H / 2):
    c.translate(cx + dx, cy + dy)
    if rot:
        c.rotate(rot)
    c.scale(sc, sc)
    c.translate(-cx, -cy)


def punch(t, t0, amt=0.05, tau=0.12):
    return 0.0 if t < t0 else amt * math.exp(-(t - t0) / tau)


def typed(s, t, t0, cps):
    n = int(clamp((t - t0) * cps / max(len(s), 1)) * len(s)) if t >= t0 else 0
    return s[:n]


def cursor(c, x, y, h, t, color=INK):
    if int(t * 2.4) % 2 == 0:
        c.drawRect(skia.Rect.MakeXYWH(x + 4, y - h * 0.8, 4, h), gpaint(color=rgb(color)))


def bubble(c, cx, cy, w, h, color=WHITE, tail="left", depth=1.0, rot=0.0):
    paper_rrect(c, cx, cy, w, h, 26, color, depth, rot)
    p = paper_paint(color)
    tx = cx - w / 2 + 50 if tail == "left" else cx + w / 2 - 50
    s = 1 if tail == "left" else -1
    c.drawPath(path_of([(tx, cy + h / 2 - 4), (tx + s * 36, cy + h / 2 - 4), (tx - s * 10, cy + h / 2 + 30)]), p)


def split_text(s, f, maxw):
    words, lines, cur = s.split(" "), [], ""
    for w_ in words:
        tryl = (cur + " " + w_).strip()
        if f.measureText(tryl) > maxw and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = tryl
    lines.append(cur)
    return lines


def typed_lines(c, lines_full, shown, x, y, f, lh, color=INK, t=0.0, show_cursor=True):
    """Draw a prefix `shown` of the text that wraps as lines_full."""
    left = len(shown)
    lx, ly = x, y
    for i, ln in enumerate(lines_full):
        seg = ln[:max(0, left)]
        text(c, seg, x, y + i * lh, f, color, "left")
        if 0 <= left <= len(ln):
            lx, ly = x + f.measureText(seg), y + i * lh
            left = -1
            break
        left -= len(ln) + 1
    if show_cursor:
        cursor(c, lx, ly, f.getSize(), t, color)


# ===================================================================== scene 1
# "For a hundred years, editing a video meant one gesture. | The cut. | Now the cut is becoming a sentence."
def s1(c, t, q, L=10.0):
    a, cut, sent = q
    draw_bg(c, YELLOW, 1)
    camera(c, 1.0 + 0.05 * smooth(t / L) + punch(t, cut, 0.06) + 0.10 * eic(prog(t, L - 1.2, 1.2)))
    strip = K.film_strip()
    cy = 900
    k_in = eoc(prog(t, 0.0, 1.1))
    x = lerp(1500, 560, k_in) - 14 * min(t, cut)
    sp = (eoc(prog(t, cut, 0.35)) * 70 + eoc(prog(t, sent, 0.6)) * 420)
    # 100-years bracket + tag
    s = pop(t, 0.9)
    tag(c, "100 YEARS", 540, 560, 54, WHITE, INK, sc=s, rot=-2, seed=2)
    if t > 1.15:
        k = eoc(prog(t, 1.15, 0.8))
        marker(c, [(110, 690), (112, 655), (540, 650), (968, 655), (970, 690)], k, 10)
    # strip: whole before the cut, two halves after
    gx = x - 14 * 0  # anchor centre
    cutx = 540
    if t < cut:
        strip.draw(c, gx, cy, -3, 0.95)
    else:
        for side in (-1, 1):
            c.save()
            if side < 0:
                c.clipRect(skia.Rect.MakeLTRB(-2000, -2000, cutx, 4000))
            else:
                c.clipRect(skia.Rect.MakeLTRB(cutx, -2000, 4000, 4000))
            with Cam(c)(side * sp, 0, side * 4 * eoc(prog(t, cut, 0.4))):
                strip.draw(c, gx, cy, -3, 0.95)
            c.restore()
        # coral cut line flash
        dashed_cut(c, cutx, 640, cutx, 1160, prog(t, cut, 0.25), CORAL, 8)
    # scissors: fly in open, snip on "The cut.", fly out
    k_s = eoc(prog(t, 2.3, 0.7))
    if k_s > 0 and t < cut + 1.2:
        out = eic(prog(t, cut + 0.55, 0.6))
        px = lerp(1250, cutx, k_s) + out * 700
        py = lerp(1700, 1230, k_s) + out * 500
        op = 16 * (1 - eoc(prog(t, cut - 0.1, 0.12))) + 2
        if t > cut + 0.25:
            op = 2 + 14 * eoc(prog(t, cut + 0.25, 0.3))
        base = -90 + 8 * (1 - k_s)
        K.scissor_half(False).draw(c, px, py, base - op, 0.92)
        K.scissor_half(True).draw(c, px, py, base + op, 0.92)
    # the sentence that replaces the cut
    if t > sent:
        k = eob(prog(t, sent + 0.15, 0.45))
        f = font("mono", 50)
        s_ = "cut right after the laugh"
        with Cam(c)(540, cy, -1.5 * k, (k, k)):
            paper_rect(c, 0, 0, 800, 150, WHITE, 7, 1.4)
            tape(c, -380, -66, 120, 40, -20, 3)
            sh = typed(s_, t, sent + 0.4, 20)
            text(c, sh, -355, 17, f, INK, "left")
            cursor(c, -355 + f.measureText(sh), 17, 50, t)
            marker_underline(c, -345, 345, 58, prog(t, sent + 2.3, 0.6), 4, 9, CORAL)


def sfx1(q):
    a, cut, sent = q
    ev = [(0.05, "whoosh", 0.8), (0.95, "pop", 0.8), (1.2, "marker", 0.7), (2.3, "whoosh", 0.6),
          (cut, "snip", 1.2), (cut, "impact", 0.5), (cut + 0.6, "whoosh", 0.5), (sent + 0.15, "pop", 0.9)]
    s_ = "cut right after the laugh"
    ev += [(sent + 0.4 + i / 20, "type", 0.55) for i in range(len(s_)) if s_[i] != " "]
    ev += [(sent + 2.3, "marker", 0.6)]
    return ev


# ===================================================================== scene 2
# "In nineteen twenty-four, editors cut film by hand on a Moviola. | In nineteen eighty-nine, Avid moved the cut onto screens."
def s2(c, t, q, L=10.0):
    a, b = q
    draw_bg(c, NAVY, 2)
    pan = 260 * smooth(prog(t, b - 0.4, 1.4))
    camera(c, 1.03 + 0.03 * smooth(t / L), 0, -pan + 60)
    # 1924 machine
    k = eoc(prog(t, 0.05, 0.6))
    mx = lerp(-300, 330, k)
    K.moviola().draw(c, mx, 780, 2, 0.86)
    tag(c, "1924", 250, 330, 64, CORAL, WHITE, rot=-5, sc=pop(t, 0.55), seed=4)
    # film feeding through
    fs = K.film_strip(5, 150, 112, "runner", 2)
    fy = 1180 + (t * 40) % 60
    fs.draw(c, mx + 230, fy - 120, 76, 0.7)
    # hand cuts: scissors snipping, chips falling
    snips = [a + 2.1, a + 2.7, a + 3.3]
    ks = eoc(prog(t, a + 1.6, 0.5))
    if ks > 0:
        op = 14
        for s_ in snips:
            if s_ - 0.08 < t < s_ + 0.18:
                op = 2
        sx, sy = lerp(1300, 770, ks), 640
        K.scissor_half(False).draw(c, sx, sy, 180 - 20 - op, 0.62)
        K.scissor_half(True).draw(c, sx, sy, 180 - 20 + op, 0.62)
        marker_circle(c, sx - 150, sy - 50, 210, 120, prog(t, a + 3.6, 0.6), 7, 10, WHITE)
        for i, s_ in enumerate(snips):
            if t > s_:
                d = t - s_
                r = R("chip", i)
                px = sx - 260 + r.uniform(-30, 30) + d * r.uniform(-60, 60)
                py = sy - 40 + 0.5 * 1500 * d * d
                with Cam(c)(px, py, d * r.uniform(-200, 200)):
                    paper_rect(c, 0, 0, 70, 54, 0x2A2A2A, i, 0.8)
                    c.drawRect(skia.Rect.MakeXYWH(-24, -16, 48, 32), gpaint(color=rgb(0xBDB6A8)))
    # 1989 workstation
    if t > b - 0.3:
        kc = pop(t, b, 0.45)
        cx_, cy_ = 650, 1420
        crt = K.crt()
        crt.draw(c, cx_, cy_, -2, 0.95 * kc)
        tag(c, "1989", 300, 1260, 64, WHITE, INK, rot=4, sc=pop(t, b + 0.35), seed=5)
        marker_arrow(c, 300, 1000, 330, 1190, prog(t, b + 0.2, 0.6), 0.3, 10, WHITE)
        if kc > 0.6:
            with crt.space(c, cx_, cy_, -2, 0.95 * kc):
                x0, y0, sw, sh = K.SCREEN_1989
                c.save()
                c.clipRect(skia.Rect.MakeXYWH(x0, y0, sw, sh))
                c.drawRect(skia.Rect.MakeXYWH(x0, y0, sw, sh), gpaint(color=rgb(0x15233F)))
                cols = [YELLOW, CORAL, TEAL]
                for tr in range(3):
                    ty = y0 + 60 + tr * 62
                    c.drawRect(skia.Rect.MakeXYWH(x0 + 16, ty - 4, sw - 32, 48), gpaint(color=rgb(0x22335A)))
                    xx = x0 + 22
                    r = R("trk", tr)
                    for j in range(5):
                        wj = r.uniform(50, 110)
                        kj = eoc(prog(t, b + 0.9 + tr * 0.25 + j * 0.12, 0.3))
                        if kj > 0:
                            xj = lerp(x0 + sw + 40, xx, kj)
                            c.drawRect(skia.Rect.MakeXYWH(xj, ty, wj - 6, 40), gpaint(color=rgb(cols[tr])))
                        xx += wj
                # playhead and an on-screen cut
                ph = x0 + 30 + (sw - 60) * smooth(prog(t, b + 2.0, 2.4))
                c.drawRect(skia.Rect.MakeXYWH(ph, y0 + 30, 4, sh - 50), gpaint(color=rgb(WHITE)))
                if t > b + 3.0:
                    dashed_cut(c, x0 + sw * 0.62, y0 + 34, x0 + sw * 0.62, y0 + sh - 20, prog(t, b + 3.0, 0.25),
                               CORAL, 5, 14, 8)
                c.restore()


def sfx2(q):
    a, b = q
    ev = [(0.05, "whoosh", 0.7), (0.55, "stamp", 0.7), (a + 1.6, "whoosh", 0.5)]
    ev += [(a + 2.1, "snip", 0.9), (a + 2.7, "snip", 0.9), (a + 3.3, "snip", 0.9), (a + 3.6, "marker", 0.5)]
    ev += [(b, "pop", 0.9), (b + 0.35, "stamp", 0.6), (b + 0.2, "marker", 0.5)]
    ev += [(b + 0.9 + tr * 0.25 + j * 0.12, "tick", 0.6) for tr in range(3) for j in range(5)]
    ev += [(b + 3.0, "snip", 0.5)]
    return ev


# ===================================================================== scene 3
# "Then, in February twenty twenty-five, | Andrej Karpathy coined vibe coding. | Describe what you want, and let AI write the code."
def _calendar(c, cx, cy, top, big, rot, sc, seed, color=CORAL):
    with Cam(c)(cx, cy, rot, sc):
        paper_rect(c, 0, 0, 440, 500, WHITE, seed, 1.2)
        c.drawPath(path_of(rough_poly([(-220, -250), (220, -250), (220, -110), (-220, -110)], seed + 1, 1.5)),
                   paper_paint(color))
        text(c, top, 0, -150, font("black", 86), WHITE)
        text(c, big, 0, 100, font("black", 150), INK)
        for i in range(7):
            c.drawCircle(-180 + i * 60, -232, 9, gpaint(color=rgb(0x2B2B2B)))


def s3(c, t, q, L=10.0):
    a, b, d = q
    draw_bg(c, CREAM, 3)
    camera(c, 1.02 + 0.04 * smooth(t / L) + punch(t, 0.45, 0.04))
    up = smooth(prog(t, d - 0.3, 0.8))
    # calendar: 1989 page rips away, FEB 2025 underneath
    cal_y = lerp(780, -400, up) + lerp(0, -330, smooth(prog(t, b - 0.1, 0.6))) * (1 - up)
    cal_s = lerp(1.0, 0.62, smooth(prog(t, b - 0.1, 0.6)))
    cal_x = lerp(540, 300, smooth(prog(t, b - 0.1, 0.6)))
    _calendar(c, cal_x, cal_y, "FEB", "2025", -4, cal_s * eob(prog(t, 0.0, 0.4)), 11)
    if t < 0.9:
        k = eic(prog(t, 0.3, 0.5))
        _calendar(c, cal_x + k * 200, cal_y - k * 1400, "1989", "", -4 + k * 25, cal_s, 12, NAVY)
    if t > 1.0:
        fs = K.film_strip(3, 120, 90, "runner", 4)
        fs.draw(c, cal_x + 230 * cal_s, cal_y + 260 * cal_s, 18, 0.7 * cal_s * eob(prog(t, 1.0, 0.4)))
    # "vibe coding" card
    if t > b - 0.1:
        k = eob(prog(t, b, 0.45))
        cy_ = lerp(1180, 560, up)
        sc_ = lerp(1.0, 0.72, up) * k
        with Cam(c)(lerp(560, 600, up), cy_, 2, sc_):
            paper_rect(c, 0, 0, 860, 350, WHITE, 13, 1.4)
            highlight(c, -360, -80, 360, 40, prog(t, b + 0.4, 0.5), YELLOW, 255, 2)
            text(c, "vibe coding", 0, 18, font("black", 112), INK)
            text(c, "noun  ·  coined Feb 2025", 0, 132, font("mono", 34), 0x4A453E)
            marker_circle(c, 0, -8, 415, 92, prog(t, b + 1.2, 0.7), 5, 11, CORAL)
        tape(c, lerp(560, 600, up) - 380 * sc_, cy_ - 150 * sc_, 140, 44, -28, 8)
    # laptop: describe -> code
    if t > d - 0.4:
        k = eoc(prog(t, d - 0.4, 0.8))
        lx, ly = 540, lerp(2300, 1290, k)
        lap = K.laptop()
        lap.draw(c, lx, ly, 0, 1.4)
        with lap.space(c, lx, ly, 0, 1.4):
            x0, y0, sw, sh = K.SCREEN_LAPTOP
            c.save()
            c.clipRect(skia.Rect.MakeXYWH(x0, y0, sw, sh))
            c.drawRect(skia.Rect.MakeXYWH(x0, y0, sw, sh), gpaint(color=rgb(0x141C30)))
            # chat bubble on the left
            f = font("mono", 19)
            s_ = "make me a website"
            kb = eob(prog(t, d + 0.2, 0.35))
            with Cam(c)(x0 + 130, y0 + 70, 0, kb):
                paper_rrect(c, 0, 0, 220, 64, 14, WHITE, 0.4)
                sh_ = typed(s_, t, d + 0.4, 16)
                text(c, sh_, -96, 7, f, INK, "left")
            # dashed cut between "describe" and "code"
            dashed_cut(c, x0 + 262, y0 + 20, x0 + 262, y0 + sh - 20, prog(t, d + 1.4, 0.3), CORAL, 4, 12, 8)
            # code lines cascade on the right
            r = R("code")
            cols = [YELLOW, CORAL, TEAL, CREAM, 0x8FA2D6]
            for i in range(13):
                t0 = d + 1.3 + i * 0.11
                kl = eoc(prog(t, t0, 0.25))
                if kl <= 0:
                    break
                ind = r.choice([0, 0, 1, 2, 1])
                yy = y0 + 30 + i * 24
                xx = x0 + 285 + ind * 22
                for seg in range(r.randint(1, 3)):
                    wseg = r.uniform(30, 110)
                    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(xx, yy, wseg * kl, 12), 6, 6),
                                gpaint(color=rgb(r.choice(cols))))
                    xx += wseg + 10
            c.restore()


def sfx3(q):
    a, b, d = q
    ev = [(0.0, "pop", 0.6), (0.3, "tear", 1.0), (0.45, "stamp", 0.7), (1.0, "pop", 0.5),
          (b, "pop", 0.9), (b + 0.4, "marker", 0.5), (b + 1.2, "marker", 0.7),
          (d - 0.4, "whoosh", 0.7), (d + 0.2, "pop", 0.6)]
    ev += [(d + 0.4 + i / 16, "type", 0.45) for i in range(17)]
    ev += [(d + 1.3 + i * 0.11, "tick", 0.5) for i in range(13)]
    return ev


# ===================================================================== scene 4
# "Vibe editing is the same idea, for video. | You type: cut the pauses, add captions, make it punchy. | It happens."
PROMPT = "cut the pauses, add captions, make it punchy"


def s4(c, t, q, L=10.0):
    a, b, d = q
    draw_bg(c, YELLOW, 4)
    camera(c, 1.0 + 0.03 * smooth(t / L) + punch(t, d, 0.07, 0.16))
    # headline: vibe c̶o̶d̶i̶n̶g̶ editing
    fb = font("black", 150)
    text(c, "vibe", 330, 330, fb, INK, alpha=int(255 * clamp(pop(t, 0.1))))
    if t > 0.1:
        k = pop(t, 0.35)
        with Cam(c)(330, 500, 0, k):
            text(c, "coding", 0, 0, fb, INK, alpha=int(255 * clamp(1 - 0.55 * prog(t, 1.1, 0.3))))
        marker(c, [(80, 455), (330, 445), (590, 450)], eoc(prog(t, 0.9, 0.35)), 16, CORAL)
    ke = pop(t, 1.35, 0.4)
    if ke > 0:
        with Cam(c)(700, 650, -5, ke):
            paper_rect(c, 0, 0, 470, 150, CORAL, 21, 1.4)
            text(c, "editing", 0, 42, font("black", 104), WHITE)
    # phone
    kp = eoc(prog(t, 1.7, 0.7))
    px, py = 540, lerp(2500, 1330, kp) - 30 * eob(prog(t, d, 0.3)) * (1 - prog(t, d + 0.3, 0.6))
    ph = K.phone()
    if kp > 0:
        ph.draw(c, px, py, 0, 1.0)
        with ph.space(c, px, py, 0, 1.0):
            x0, y0, sw, sh = K.SCREEN_PHONE
            c.save()
            c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0, sw, sh), 52, 52), True)
            c.drawRect(skia.Rect.MakeXYWH(x0, y0, sw, sh), gpaint(color=rgb(0xF4EFE4)))
            done = eoc(prog(t, d, 0.45))
            # preview
            c.drawRect(skia.Rect.MakeXYWH(x0, y0 + 60, sw, 300), gpaint(color=rgb(NAVY)))
            c.drawCircle(x0 + sw / 2, y0 + 190, 70, gpaint(color=rgb(0x6F7FA8)))
            c.drawRect(skia.Rect.MakeXYWH(x0 + sw / 2 - 100, y0 + 260, 200, 100), gpaint(color=rgb(0x6F7FA8)))
            if done > 0:   # captions appear
                kc = eob(prog(t, d + 0.15, 0.35))
                with Cam(c)(x0 + sw / 2, y0 + 315, -2, kc):
                    paper_rrect(c, 0, 0, 300, 58, 10, YELLOW, 0.5)
                    text(c, "IT HAPPENS.", 0, 12, font("black", 34), INK)
            # timeline: clips with gaps close up
            ty = y0 + 400
            r = R("clips")
            xx = x0 + 22
            cols = [CORAL, TEAL, 0x8FA2D6, CORAL, TEAL, 0x8FA2D6]
            for i in range(6):
                wj = r.uniform(48, 70)
                gap = r.uniform(14, 34) * (1 - done)
                c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(xx, ty, wj, 64), 8, 8), gpaint(color=rgb(cols[i])))
                xx += wj + gap + 4
            # waveform with silences that vanish
            for i in range(54):
                xw = x0 + 24 + i * 7.8
                silent = (i // 9) % 2 == 1
                amp = 4 if silent else 10 + 22 * abs(math.sin(i * 1.7) * math.cos(i * 0.6))
                if silent:
                    amp = lerp(4, 10 + 20 * abs(math.sin(i * 2.3)), done)
                c.drawRect(skia.Rect.MakeXYWH(xw, ty + 120 - amp, 4, 2 * amp), gpaint(color=rgb(0x3B3A44)))
            # chat
            f = font("mono", 29)
            lines = split_text(PROMPT, f, sw - 100)
            if t > b - 0.2:
                kb = eob(prog(t, b - 0.2, 0.35))
                bh = 44 + 40 * len(lines)
                with Cam(c)(x0 + sw / 2 + 10, y0 + 590 + bh / 2, 0, kb):
                    paper_rrect(c, 0, 0, sw - 60, bh, 22, WHITE, 0.6)
                    typed_lines(c, lines, typed(PROMPT, t, b, 16), -(sw - 60) / 2 + 24, -bh / 2 + 48, f, 40,
                                INK, t, t < d)
            # input bar
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0 + 24, y0 + sh - 110, sw - 48, 64), 32, 32),
                        gpaint(color=rgb(0xE2DACB)))
            c.drawCircle(x0 + sw - 62, y0 + sh - 78, 24, gpaint(color=rgb(CORAL if t > d - 0.3 else 0xB9B0A0)))
            c.restore()
    # payoff: check + burst marks
    if t > d:
        marker_check(c, 935, 1000, 60, prog(t, d + 0.35, 0.4), 16, INK)
        for i in range(7):
            a_ = -math.pi / 2 + (i - 3) * 0.32
            k = eoc(prog(t, d + 0.05, 0.3))
            r0, r1 = 560 + 30 * k, 580 + 120 * k
            if k > 0 and t < d + 1.6:
                marker(c, [(540 + r0 * math.cos(a_) * 0.8, 1330 + r0 * math.sin(a_)),
                           (540 + r1 * math.cos(a_) * 0.8, 1330 + r1 * math.sin(a_))], 1.0, 10, INK,
                       alpha=int(255 * (1 - prog(t, d + 1.0, 0.6))), smooth_=False)


def sfx4(q):
    a, b, d = q
    ev = [(0.1, "pop", 0.7), (0.35, "pop", 0.6), (0.9, "marker", 0.9), (1.35, "stamp", 0.7),
          (1.7, "whoosh", 0.7), (b - 0.2, "pop", 0.6)]
    ev += [(b + i / 16, "type", 0.5) for i in range(len(PROMPT)) if PROMPT[i] != " "]
    ev += [(d - 0.3, "tick", 0.8), (d, "impact", 0.8), (d, "sparkle", 0.9), (d + 0.15, "pop", 0.8),
           (d + 0.35, "marker", 0.8)]
    return ev


# ===================================================================== scene 5
# "But here's the catch. | The software can make a thousand cuts. | It still can't tell which one actually matters."
COLS, ROWS, CELL = 25, 40, 34
GX0, GY0 = (W - COLS * CELL) / 2, 330
PICK = (16, 21)


def _count(t, t0, t1):
    p = prog(t, t0, t1 - t0)
    return 0 if t < t0 else int(round(10 ** (3 * eic(p) ** 0.7)))


def s5(c, t, q, L=10.0):
    a, b, d = q
    draw_bg(c, NAVY, 5)
    pick_x = GX0 + PICK[0] * CELL + CELL / 2
    pick_y = GY0 + PICK[1] * CELL + CELL / 2
    z = smooth(prog(t, d + 0.4, 3.6))
    camera(c, 1.0 + 0.55 * z, (W / 2 - pick_x) * z * 1.2, (H / 2 - pick_y) * z * 1.2)
    # the catch
    kt = pop(t, 0.3)
    fade = 1 - prog(t, b + 0.6, 0.4)
    if fade > 0:
        ks = eoc(prog(t, 0.0, 0.6))
        K.film_strip().draw(c, lerp(1700, 640, ks) - 12 * t, 1170, 3, 0.85 * (1 - eic(prog(t, b, 0.5))) + 0.001)
        with Cam(c)(540, 900, -2, kt):
            paper_rect(c, 0, 0, 640, 170, WHITE, 31, 1.4)
            text(c, "THE CATCH", 0, 34, font("black", 92), INK, alpha=int(255 * fade))
        marker_underline(c, 260, 820, 1010, prog(t, 0.8, 0.5), 3, 11, CORAL)
    # a thousand cuts
    n = _count(t, b + 0.2, b + 1.9)
    r = R("grid")
    dim = smooth(prog(t, d, 0.5))
    for i in range(min(n, COLS * ROWS)):
        col, row = i % COLS, i // COLS
        # fill from the centre outward-ish: shuffle order deterministically
        x = GX0 + col * CELL
        y = GY0 + row * CELL
        g = 0.55 + 0.35 * ((i * 7919) % 97) / 97
        a_ = 255
        if (col, row) != PICK:
            a_ = int(255 * (1 - 0.72 * dim))
        c.drawRect(skia.Rect.MakeXYWH(x + 3, y + 3, CELL - 6, CELL - 6), gpaint(color=skia.Color(18, 18, 22, a_)))
        v = int(255 * g)
        c.drawRect(skia.Rect.MakeXYWH(x + 7, y + 8, CELL - 14, CELL - 16), gpaint(color=skia.Color(v, v - 8, v - 20, a_)))
    if n > 0:
        label = f"{min(n, 1000):,} CUTS"
        with Cam(c)(540, 230, 2, pop(t, b + 0.2)):
            paper_rect(c, 0, 0, 470, 110, CORAL, 33, 1.4)
            text(c, label, 0, 22, font("black", 64), WHITE)
    # which one matters?
    if t > d:
        k = eob(prog(t, d + 0.2, 0.4))
        with Cam(c)(pick_x, pick_y, 0, 1 + 0.9 * k):
            paper_rect(c, 0, 0, CELL + 8, CELL + 8, WHITE, 41, 1.0 * k, 1.0)
            c.drawRect(skia.Rect.MakeXYWH(-CELL / 2 + 5, -CELL / 2 + 5, CELL - 10, CELL - 10), gpaint(color=rgb(0x1C1C20)))
            c.drawRect(skia.Rect.MakeXYWH(-CELL / 2 + 8, -CELL / 2 + 9, CELL - 16, CELL - 18), gpaint(color=rgb(YELLOW)))
        marker_circle(c, pick_x, pick_y, 70, 64, prog(t, d + 0.9, 0.5), 9, 7, CORAL)
        scribble_question(c, pick_x + 120, pick_y - 70, 70, prog(t, d + 1.7, 0.6), 7, WHITE)


def sfx5(q):
    a, b, d = q
    ev = [(0.3, "stamp", 0.7), (0.8, "marker", 0.6), (b + 0.2, "pop", 0.6)]
    last = 0
    tt = b + 0.2
    while tt < b + 1.9:   # ticks accelerate with the count
        n = _count(tt, b + 0.2, b + 1.9)
        if n != last:
            ev.append((tt, "tick", 0.45))
            last = n
        tt += 1 / 30
    ev += [(d, "whoosh", 0.4), (d + 0.2, "pop", 0.8), (d + 0.9, "marker", 0.7), (d + 1.7, "marker", 0.6)]
    return ev


# ===================================================================== scene 6
# "So the cut didn't disappear. | It moved, from your hands, to your words. | The editor is still you."
def s6(c, t, q, L=10.0):
    a, b, d = q
    draw_bg(c, CREAM, 6)
    out = smooth(prog(t, d - 0.2, 0.7))
    camera(c, 1.0 + 0.04 * smooth(t / L) + punch(t, d + 1.0, 0.05, 0.14))
    with Cam(c)(0, -1500 * out):
        # cut line + scissors
        dashed_cut(c, -40, 760, 1120, 760, prog(t, 0.4, 0.8), CORAL, 8, 30, 18, -t * 40)
        ks = eoc(prog(t, 0.1, 0.6))
        travel = smooth(prog(t, b + 1.0, 1.0))
        sx = lerp(lerp(-300, 470, ks), 820, travel)
        sy = lerp(760, 1290, travel) - 160 * math.sin(math.pi * travel)
        ss = lerp(0.9, 0.35, travel)
        sa = 1 - prog(t, b + 1.7, 0.3)
        op = 16 if not (1.25 < t < 1.45) else 2
        if sa > 0:
            K.scissor_half(False).draw(c, sx, sy, -op, ss, int(255 * sa))
            K.scissor_half(True).draw(c, sx, sy, op, ss, int(255 * sa))
        tag(c, "HANDS", 250, 1110, 76, WHITE, INK, rot=-3, sc=pop(t, b + 0.1), seed=51)
        marker_arrow(c, 330, 1010, 760, 1010, prog(t, b + 0.6, 0.8), -0.18, 11, INK)
        tag(c, "WORDS", 830, 1110, 76, CORAL, WHITE, rot=3, sc=pop(t, b + 1.3), seed=52)
        if t > b + 1.6:
            kb = eob(prog(t, b + 1.6, 0.35))
            with Cam(c)(800, 1340, 2, kb * 1.3):
                bubble(c, 0, 0, 330, 110, WHITE)
                f = font("mono", 40)
                sh_ = typed("cut here.", t, b + 1.8, 14)
                text(c, sh_, -120, 14, f, INK, "left")
                cursor(c, -120 + f.measureText(sh_), 14, 40, t)
    # the editor is still you
    if t > d - 0.4:
        k = eoc(prog(t, d - 0.4, 0.7))
        fy = lerp(2500, 1000, k)
        fr = K.portrait_frame()
        fr.draw(c, 540, fy, -1.5, 1.0)
        with fr.space(c, 540, fy, -1.5, 1.0):
            x0, y0, fw, fh = K.FRAME_IN
            c.drawRect(skia.Rect.MakeXYWH(x0, y0, fw, fh), gpaint(color=rgb(0xE9E3D6)))
            ky = pop(t, d + 1.0, 0.3)
            if ky > 0:
                with Cam(c)(x0 + fw / 2, y0 + fh / 2 + 10, -4, ky * 1.0):
                    paper_rect(c, 0, 0, 360, 190, CORAL, 61, 1.2)
                    text(c, "YOU", 0, 56, font("black", 160), WHITE)
        tag(c, "THE EDITOR", 540, fy - 430, 56, WHITE, INK, rot=-2, sc=pop(t, d + 0.35), seed=62)
        marker_underline(c, 330, 750, fy + 470, prog(t, d + 1.7, 0.6), 6, 12, INK)
        fs = K.film_strip()
        kf = eoc(prog(t, d + 2.1, 1.0))
        if kf > 0:
            fs.draw(c, lerp(-900, 540, kf) + 30 * prog(t, d + 3.1, 3), 1640, 2, 0.8)


def sfx6(q):
    a, b, d = q
    ev = [(0.1, "whoosh", 0.6), (1.3, "snip", 1.0), (b + 0.1, "pop", 0.7), (b + 0.6, "marker", 0.7),
          (b + 1.0, "whoosh", 0.5), (b + 1.3, "pop", 0.7), (b + 1.6, "pop", 0.6)]
    ev += [(b + 1.8 + i / 14, "type", 0.5) for i in range(9) if "cut here."[i] != " "]
    ev += [(d - 0.4, "whoosh", 0.8), (d + 0.35, "pop", 0.6), (d + 1.0, "stamp", 1.0), (d + 1.0, "impact", 0.6),
           (d + 1.7, "marker", 0.7), (d + 2.1, "rustle", 0.7)]
    return ev


SCENES = [s1, s2, s3, s4, s5, s6]
SFX = [sfx1, sfx2, sfx3, sfx4, sfx5, sfx6]
