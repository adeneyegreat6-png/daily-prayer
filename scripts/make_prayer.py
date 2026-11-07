#!/usr/bin/env python3
"""Daily prayer video builder.
Usage: python3 make_prayer.py days/day01.json out/
Produces: 9:16 + 16:9 MP4, two thumbnails, SRT subtitles.
"""
import json, os, re, subprocess, sys
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # repo root
FONTS = os.path.join(ROOT, "fonts")
BG = {  # source file, clean crop band (y0, y1) avoiding baked-in template text
    1: (os.path.join(ROOT, "bg", "bg1.mp4"), 650, 1705),
    2: (os.path.join(ROOT, "bg", "bg2.mp4"), 790, 1700),
}
VOICE, SPEED, LANG = "bm_george", 0.88, "en-gb"
SR = 24000
GOLD = (233, 196, 106)

def font(name, size): return ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), size)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: print(r.stderr[-3000:]); raise SystemExit(1)

# ---------- audio ----------
def build_audio(d, work):
    k = Kokoro(os.path.join(ROOT, "models/kokoro-v1.0.onnx"), os.path.join(ROOT, "models/voices-v1.0.bin"))
    # (segment_id, spoken text, pause_after_seconds)
    segs = [("intro", f"{d['prayer_type']}. Today's verse is from {d['reference_spoken']}", 1.0)]
    for i, v in enumerate(d["verse_spoken"]):
        segs.append((f"verse{i}", v, 0.6 if i < len(d["verse_spoken"]) - 1 else 1.4))
    segs.append(("letus", "Let us pray.", 1.0))
    for i, p in enumerate(d["prayer"]):
        segs.append((f"p{i}", p, 0.75))
    segs.append(("amen", "Amen.", 0.0))
    audio = [np.zeros(int(SR * 0.8), dtype=np.float32)]
    t = 0.8; timeline = []
    for sid, text, pause in segs:
        s, sr = k.create(text, voice=VOICE, speed=SPEED, lang=LANG)
        assert sr == SR
        timeline.append((sid, text, t, t + len(s) / SR))
        audio += [s.astype(np.float32), np.zeros(int(SR * pause), dtype=np.float32)]
        t += len(s) / SR + pause
    audio.append(np.zeros(int(SR * 3.5), dtype=np.float32))  # hold end card
    a = np.concatenate(audio); a = a / max(1e-6, np.abs(a).max()) * 0.89
    path = os.path.join(work, "voice.wav"); sf.write(path, a, SR)
    return path, timeline, len(a) / SR

# ---------- text layout ----------
def wrap(draw, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def shadow_text(img, xy_lines, f, fill, anchor="ma"):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    for (x, y), line in xy_lines: sd.text((x, y + 3), line, font=f, fill=(0, 0, 0, 200), anchor=anchor)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    for (x, y), line in xy_lines: d.text((x, y), line, font=f, fill=fill, anchor=anchor)

def block(img, text, f, fill, cx, cy, maxw, lh):
    d = ImageDraw.Draw(img); lines = wrap(d, text, f, maxw)
    h = lh * len(lines); y0 = cy - h / 2
    shadow_text(img, [((cx, y0 + i * lh), l) for i, l in enumerate(lines)], f, fill)
    return y0, y0 + h

def spaced(img, text, f, fill, cx, y, track):
    d = ImageDraw.Draw(img)
    w = sum(d.textlength(c, font=f) for c in text) + track * (len(text) - 1)
    x = cx - w / 2; items = []
    for c in text:
        items.append(((x, y), c)); x += d.textlength(c, font=f) + track
    shadow_text(img, items, f, fill, anchor="la")

def make_layers(d, timeline, W, H, work, tag):
    v = H > W
    s = W / 1080 if v else H / 1080  # base scale
    maxw = W * (0.84 if v else 0.66)
    layers = []
    # persistent overlay: darkening gradient + header
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = np.zeros((H, W, 4), dtype=np.uint8)
    yy = np.linspace(0, 1, H)[:, None]
    grad[..., 3] = (95 + 70 * np.abs(yy - 0.5) * 2).astype(np.uint8)  # darker at edges
    base.alpha_composite(Image.fromarray(grad, "RGBA"))
    hy = (150 if v else 70) * s
    spaced(base, "DAILY PRAYER", font("MS-600", int(30 * s)), (255, 255, 255, 235), W / 2, hy, 6 * s)
    dd = ImageDraw.Draw(base)
    dd.line([(W / 2 - 40 * s, hy + 60 * s), (W / 2 + 40 * s, hy + 60 * s)], fill=GOLD + (255,), width=max(2, int(3 * s)))
    p = os.path.join(work, f"{tag}_base.png"); base.save(p); layers.append((p, 0, None, 0, 0))

    cy = H * (0.5 if v else 0.53)
    T = {sid: (st, en) for sid, _, st, en in timeline}
    def add(name, img, st, en):
        x0, y0, x1, y1 = img.getbbox(); x0, y0 = max(0, x0 - 4) & ~1, max(0, y0 - 4) & ~1
        q = os.path.join(work, f"{tag}_{name}.png"); img.crop((x0, y0, x1 + 4, y1 + 4)).save(q)
        layers.append((q, st, en, x0, y0))
    # title card (intro)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _, ty1 = block(im, d["prayer_type"], font("CG-700", int(118 * s)), (255, 255, 255, 255), W / 2, cy - 60 * s, maxw, 120 * s)
    spaced(im, d["reference"].upper(), font("MS-600", int(34 * s)), GOLD + (255,), W / 2, ty1 + 45 * s, 4 * s)
    add("title", im, 0.3, T["verse0"][0] - 0.15)
    # verse (whole verse on screen while it is read)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vf = font("CG-600i", int(76 * s)); y0, y1 = block(im, f"“{d['verse']}”", vf, (255, 255, 255, 255), W / 2, cy - 30 * s, maxw, 92 * s)
    spaced(im, f"{d['reference'].upper()}  ({d['translation']})", font("MS-600", int(30 * s)), GOLD + (255,), W / 2, y1 + 40 * s, 4 * s)
    vk = [k for k in T if k.startswith("verse")]
    add("verse", im, T["verse0"][0] - 0.1, T["letus"][0] - 0.2)
    # let us pray
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    block(im, "Let us pray", font("CG-600i", int(110 * s)), GOLD + (255,), W / 2, cy, maxw, 120 * s)
    add("letus", im, T["letus"][0] - 0.1, T["p0"][0] - 0.15)
    # prayer lines
    pf = font("CG-600", int(80 * s))
    n = len(d["prayer"])
    for i, line in enumerate(d["prayer"]):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        block(im, line, pf, (255, 255, 255, 255), W / 2, cy, maxw, 96 * s)
        nxt = T[f"p{i+1}"][0] if i + 1 < n else T["amen"][0]
        add(f"p{i}", im, T[f"p{i}"][0] - 0.1, nxt - 0.15)
    # amen / end card
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    block(im, "Amen", font("CG-700", int(150 * s)), (255, 255, 255, 255), W / 2, cy - 40 * s, maxw, 150 * s)
    spaced(im, "COMMENT “AMEN”  ·  SHARE  ·  FOLLOW FOR DAILY PRAYER", font("MS-600", int((26 if v else 28) * s)), GOLD + (255,), W / 2, cy + 90 * s, 3 * s)
    add("amen", im, T["amen"][0] - 0.1, None)
    return layers

# ---------- background ----------
def bg_loop(d, W, H, work, tag):
    src, y0, y1 = BG[d["bg"]]
    ch = y1 - y0
    out = os.path.join(work, f"{tag}_bgloop.mp4")
    vf = (f"crop=1080:{ch}:0:{y0},scale=-2:{H}" if H > W else f"crop=1080:{ch}:0:{y0},scale={W}:-2")
    vf += f",crop={W}:{H},gblur=sigma=1.2,eq=saturation=1.05,fps=30,setsar=1,split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0"
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-an", "-filter_complex", f"[0:v]{vf}[o]", "-map", "[o]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out])
    return out

def render(d, timeline, dur, voice, W, H, work, outpath, tag):
    loop = bg_loop(d, W, H, work, tag)
    layers = make_layers(d, timeline, W, H, work, tag)
    cmd = ["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", loop, "-i", voice]
    for p, *_ in layers: cmd += ["-loop", "1", "-framerate", "30", "-t", f"{dur:.2f}", "-i", p]
    fc, last = [], "[0:v]"
    fd = 0.35
    for i, (p, st, en, x, y) in enumerate(layers):
        idx = i + 2; f = f"[{idx}:v]format=rgba"
        if st > 0: f += f",fade=t=in:st={st:.2f}:d={fd}:alpha=1"
        if en is not None: f += f",fade=t=out:st={en - fd:.2f}:d={fd}:alpha=1"
        fc.append(f + f"[l{i}]")
        win = "" if (st == 0 and en is None) else f":enable='between(t,{max(0, st - 0.05):.2f},{(en if en else dur) + 0.05:.2f})'"
        fc.append(f"{last}[l{i}]overlay={x}:{y}:format=auto{win}[v{i}]"); last = f"[v{i}]"
    fc.append(f"{last}fade=t=in:st=0:d=0.8,fade=t=out:st={dur-1.0:.2f}:d=1.0,format=yuv420p[vout]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "1:a", "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", outpath]
    run(cmd)

# ---------- thumbnails ----------
def thumbnail(d, W, H, work, outpath, tag):
    loop = os.path.join(work, f"{tag}_bgloop.mp4"); fr = os.path.join(work, f"{tag}_frame.png")
    run(["ffmpeg", "-y", "-v", "error", "-ss", "1.5", "-i", loop, "-frames:v", "1", fr])
    img = Image.open(fr).convert("RGBA").resize((W, H), Image.LANCZOS); v = H > W; s = W / 1080 if v else H / 720
    g = np.zeros((H, W, 4), dtype=np.uint8)
    if v:
        yy = np.linspace(0, 1, H)[:, None]; g[..., 3] = (110 + 60 * np.abs(yy - 0.5) * 2).astype(np.uint8)
    else:
        xx = np.linspace(0, 1, W)[None, :]; g[..., 3] = np.clip(215 - 230 * xx, 40, 215).astype(np.uint8)
    img.alpha_composite(Image.fromarray(g, "RGBA"))
    maxw = W * (0.88 if v else 0.62); size = int((128 if v else 118) * s)
    while True:
        big = font("MS-700", size); dr = ImageDraw.Draw(img)
        if max(dr.textlength(t, font=big) for t in (d["thumb_line1"], d["thumb_line2"])) <= maxw or size < 40: break
        size -= 4
    if v:
        cx, y = W / 2, H * 0.36; anc = "ma"
    else:
        cx, y = 70 * s, 150 * s; anc = "la"
    shadow_text(img, [((cx, y), d["thumb_line1"])], big, (255, 255, 255, 255), anchor=anc)
    shadow_text(img, [((cx, y + big.size * 1.05), d["thumb_line2"])], big, GOLD + (255,), anchor=anc)
    sub = font("CG-600i", int((72 if v else 60) * s))
    y2 = y + big.size * 2.35
    shadow_text(img, [((cx, y2), d.get("thumb_sub", "Pray along with me"))], sub, (255, 255, 255, 255), anchor=anc)
    tag_f = font("MS-600", int((34 if v else 28) * s))
    shadow_text(img, [((cx, y2 + sub.size * 1.5), d["reference"].upper())], tag_f, GOLD + (255,), anchor=anc)
    img.convert("RGB").save(outpath, quality=92)

def srt(timeline, d, path):
    def ts(t): h, m = int(t // 3600), int(t % 3600 // 60); return f"{h:02}:{m:02}:{t%60:06.3f}".replace(".", ",")
    with open(path, "w") as f:
        for i, (_, text, st, en) in enumerate(timeline, 1):
            f.write(f"{i}\n{ts(st)} --> {ts(en)}\n{text}\n\n")

if __name__ == "__main__":
    d = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    work = os.path.join(out, "_work"); os.makedirs(work, exist_ok=True)
    name = re.sub(r"[^a-z0-9]+", "-", d["prayer_type"].lower()).strip("-")
    voice, tl, dur = build_audio(d, work); print(f"audio {dur:.1f}s")
    for W, H, tag in [(1080, 1920, "9x16"), (1920, 1080, "16x9")]:
        render(d, tl, dur, voice, W, H, work, os.path.join(out, f"{name}_{tag}.mp4"), tag)
    thumbnail(d, 1280, 720, work, os.path.join(out, f"{name}_thumbnail_16x9.jpg"), "16x9")
    thumbnail(d, 1080, 1920, work, os.path.join(out, f"{name}_cover_9x16.jpg"), "9x16")
    srt(tl, d, os.path.join(out, f"{name}_subtitles.srt"))
    print("done")
