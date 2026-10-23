"""
make_sky.py - "Clawd's World" layers: sky gradients per daypart, a pixel sun,
a skyline horizon strip, and full-screen particle overlays (rain, snow, stars).

Output (res/drawable):
  sky_night.png sky_dawn.png sky_day.png sky_dusk.png   480x480 gradients
  sun.png                                               32x32 pixel sun
  skyline.png                                           480x48 silhouette
  fx_rain.webp fx_snow.webp fx_stars.webp               480x480, 4 frames, alpha
  bg_vignette.png                                       re-made as an alpha overlay
Run: python make_sky.py
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "res" / "drawable"
W = 480
random.seed(7)

# Sky gradients: (top colour, horizon colour). Kept dark enough for ivory text.
SKIES = {
    "night": ((14, 14, 20), (28, 26, 34)),
    "dawn":  ((30, 24, 40), (120, 64, 52)),
    "day":   ((22, 38, 64), (58, 84, 112)),
    "dusk":  ((36, 20, 36), (150, 70, 48)),
}


def sky(name, top, horizon, horizon_y=200):
    img = Image.new("RGBA", (W, W), top + (255,))
    px = img.load()
    for y in range(W):
        k = min(1.0, y / horizon_y)          # 0 at top .. 1 at horizon, flat below
        k = k * k                            # ease: most colour change near the horizon
        c = tuple(int(top[i] + (horizon[i] - top[i]) * k) for i in range(3))
        if y > horizon_y:                    # below the horizon fade back to charcoal
            k2 = min(1.0, (y - horizon_y) / 120)
            c = tuple(int(c[i] + ((31, 30, 29)[i] - c[i]) * k2) for i in range(3))
        for x in range(W):
            px[x, y] = c + (255,)
    img.save(OUT / f"sky_{name}.png")
    print("wrote sky_" + name)


def vignette_overlay():
    """Transparent centre, darkening toward the bezel, plus a faint grid."""
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    px = img.load()
    for y in range(W):
        for x in range(W):
            r = math.hypot(x - 240, y - 240) / 240
            a = int(170 * max(0.0, min(1.0, (r - 0.55) / 0.45)) ** 1.4)
            px[x, y] = (10, 10, 12, a)
    d = ImageDraw.Draw(img)
    for i in range(0, W, 40):
        d.line([i, 0, i, W], fill=(255, 255, 255, 7))
        d.line([0, i, W, i], fill=(255, 255, 255, 7))
    img.save(OUT / "bg_vignette.png")
    print("wrote bg_vignette (overlay)")


def sun():
    s = 32
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    core, ray = (250, 200, 90, 255), (242, 170, 70, 255)
    d.ellipse([8, 8, 23, 23], fill=core)
    for a in range(0, 360, 45):
        x = 16 + 14 * math.cos(math.radians(a)); y = 16 + 14 * math.sin(math.radians(a))
        d.rectangle([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=ray)
    img.save(OUT / "sun.png")
    print("wrote sun")


def skyline():
    """Low pixel city silhouette, 480x48, sits on the horizon above Clawd's window."""
    img = Image.new("RGBA", (W, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = (24, 23, 24, 255)
    x = 0
    while x < W:
        w = random.choice((12, 18, 24, 30))
        h = random.choice((10, 16, 22, 28, 34, 40))
        d.rectangle([x, 48 - h, x + w - 1, 48], fill=col)
        if h > 20 and random.random() < 0.5:            # antenna
            d.rectangle([x + w // 2, 48 - h - 6, x + w // 2, 48 - h], fill=col)
        for wy in range(48 - h + 4, 46, 6):            # lit windows
            for wx in range(x + 3, x + w - 3, 6):
                if random.random() < 0.25:
                    d.rectangle([wx, wy, wx + 1, wy + 1], fill=(120, 100, 60, 255))
        x += w + random.choice((0, 2, 4))
    img.save(OUT / "skyline.png")
    print("wrote skyline")


def particles(name, count, color, size, dy, dx, frames=4, ms=120, twinkle=False):
    pts = [(random.randrange(W), random.randrange(W)) for _ in range(count)]
    imgs = []
    for f in range(frames):
        img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i, (x, y) in enumerate(pts):
            if twinkle:
                a = color[3] if (i + f) % 3 else color[3] // 3
                c = color[:3] + (a,)
                d.rectangle([x, y, x + size - 1, y + size - 1], fill=c)
            else:
                xx = (x + dx * f) % W; yy = (y + dy * f) % W
                if dy > 6:    # rain streak
                    d.line([xx, yy, xx - dx // 2, yy - 10], fill=color, width=size)
                else:
                    d.rectangle([xx, yy, xx + size - 1, yy + size - 1], fill=color)
        imgs.append(img)
    imgs[0].save(OUT / f"fx_{name}.webp", save_all=True, append_images=imgs[1:], duration=ms, loop=0, lossless=True)
    print(f"wrote fx_{name}.webp")


if __name__ == "__main__":
    for n, (t, h) in SKIES.items():
        sky(n, t, h)
    vignette_overlay()
    sun()
    skyline()
    particles("rain", 70, (140, 180, 220, 150), 2, 28, 6, frames=4, ms=90)
    particles("snow", 60, (240, 240, 245, 200), 3, 9, 2, frames=4, ms=260)
    particles("stars", 90, (220, 220, 230, 200), 2, 0, 0, frames=3, ms=700, twinkle=True)
