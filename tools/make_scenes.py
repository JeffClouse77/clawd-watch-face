"""
make_scenes.py - Low-contrast pixel-art backdrops for Clawd's band (480 x 128).

Each scene is a 40 x 11 grid at 12 px per cell (cropped to 128 px tall).
Colours stay close to the face background so Clawd and the captions pop.

Output: ../res/drawable/scene_*.png
Run:    python make_scenes.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "res" / "drawable"
SCALE, W, H = 12, 40, 11

P = {
    ".": None,
    "g": (44, 44, 44),      # graphite shapes
    "G": (58, 58, 58),      # lighter structure
    "s": (90, 92, 96),      # dim star / highlight
    "m": (120, 110, 80),    # dim moon
    "o": (96, 66, 52),      # dim sunrise orange
    "e": (52, 84, 60),      # dim terminal green / foliage
    "t": (60, 80, 56),      # tree
    "w": (62, 54, 46),      # warm lamp glow
    "b": (46, 52, 64),      # tv glow blue
}


PANEL = (16, 0, 463, 127)        # Clawd's window: rounded panel inset from the bezel
PANEL_FILL = (38, 37, 36, 255)
PANEL_EDGE = (62, 61, 60, 255)


def compose(rows, palette=None):
    """Draw one grid into the window panel; returns a 480x128 RGBA image."""
    pal = palette or P
    art = Image.new("RGBA", (480, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            c = pal[ch]
            if c:
                d.rectangle([i * SCALE, j * SCALE, (i + 1) * SCALE - 1, (j + 1) * SCALE - 1], fill=c + (255,))
    img = Image.new("RGBA", (480, 128), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(PANEL, radius=22, fill=PANEL_FILL, outline=PANEL_EDGE, width=2)
    mask = Image.new("L", (480, 128), 0)
    ImageDraw.Draw(mask).rounded_rectangle((PANEL[0] + 2, PANEL[1] + 2, PANEL[2] - 2, PANEL[3] - 2), radius=20, fill=255)
    img.paste(art, (0, 0), Image.composite(art.split()[3], Image.new("L", (480, 128), 0), mask))
    return img


def scene(name, rows):
    compose(rows).save(OUT / f"scene_{name}.png")
    print("wrote scene_" + name)


def scene_anim(name, frames, ms):
    """Living scene: list of (rows, palette-overrides) frames -> animated WebP."""
    imgs = []
    for rows, over in frames:
        pal = dict(P); pal.update(over or {})
        imgs.append(compose(rows, pal))
    imgs[0].save(OUT / f"scene_{name}.webp", save_all=True, append_images=imgs[1:], duration=ms, loop=0, lossless=True)
    (OUT / f"scene_{name}.png").unlink(missing_ok=True)
    print(f"wrote scene_{name}.webp ({len(imgs)} frames)")


def shift_stars(rows, dx):
    """Move the 's' star cells sideways for a twinkle variant."""
    out = []
    for row in rows:
        r = ["."] * len(row)
        for i, ch in enumerate(row):
            if ch == "s":
                j = (i + dx) % len(row)
                r[j] = "s"
            elif ch != ".":
                r[i] = ch
        out.append("".join(r))
    return out


def background():
    """480x480 vignette with a faint blueprint grid (Redline graphic language)."""
    import math
    w = 480
    img = Image.new("RGBA", (w, w), (31, 30, 29, 255))
    px = img.load()
    for y in range(w):
        for x in range(w):
            r = math.hypot(x - 240, y - 240) / 240
            k = max(0.0, min(1.0, (r - 0.45) / 0.55))    # 0 at centre .. 1 at bezel
            v = int(34 - 12 * k)                           # 34 at centre -> 22 at edge
            px[x, y] = (v + 1, v, v - 1, 255)
    d = ImageDraw.Draw(img)
    for i in range(0, w, 40):
        d.line([i, 0, i, w], fill=(38, 37, 36, 255))
        d.line([0, i, w, i], fill=(38, 37, 36, 255))
    img.save(OUT / "bg_vignette.png")
    print("wrote bg_vignette")


# Clawd sits LEFT for sleep/walk/read, CENTER for coffee/lunch/gym, RIGHT for code/ship/game.
SCENES = {
    # night sky: stars and a crescent, Clawd on the left
    "night": [
        "..........s...............s.............",
        "....................s...................",
        ".......s................................",
        "..............................s.........",
        "...........................s............",
        "......................s.................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "gggggggggggggggggggggggggggggggggggggggg",
    ],
    # sunrise over a counter, Clawd centre
    "morning": [
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "....oo...........................oo.....",
        "...oooo.........................oooo....",
        "..oooooo.......................oooooo...",
        "gggggggggggggggggggggggggggggggggggggggg",
        "...GG........................GG.........",
        "...GG........................GG.........",
        "........................................",
    ],
    # office: second monitor on the left, desk line, Clawd right
    "work": [
        "........................................",
        "..GGGGGGGGGG............................",
        "..Ge.ee..e.G............................",
        "..G.eee.e..G............................",
        "..Ge..ee...G............................",
        "..GGGGGGGGGG............................",
        "......GG................................",
        "....GGGGGG..............................",
        "gggggggggggggggggggggggggggggggggggggggg",
        "..GG................................GG..",
        "..GG................................GG..",
    ],
    # lunch table with a cup and plate
    "lunch": [
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        ".....GG.................................",
        ".....GG.........................GGGGG...",
        "....GGGG.......................GGGGGGG..",
        "gggggggggggggggggggggggggggggggggggggggg",
        "...GG................................GG.",
        "...GG................................GG.",
        "........................................",
    ],
    # park: skyline and trees, Clawd walks on the left
    "park": [
        "........................................",
        "........................gg..............",
        "....................gg..gg....gg........",
        "....................gg..gg....gg..gg....",
        "...............tt...gg..gg....gg..gg....",
        "..............tttt..gg..gg....gg..gg....",
        "...............tt...gggggg....gggggg....",
        "...............GG.......................",
        "gggggggggggggggggggggggggggggggggggggggg",
        "........................................",
        "........................................",
    ],
    # gym: rack uprights and a bench
    "gym": [
        "..GG................................GG..",
        "..GG................................GG..",
        "..GGGGGG........................GGGGGG..",
        "..GG................................GG..",
        "..GG................................GG..",
        "..GGGGGG........................GGGGGG..",
        "..GG................................GG..",
        "..GG................................GG..",
        "..GG................................GG..",
        "gggggggggggggggggggggggggggggggggggggggg",
        "........................................",
    ],
    # reading nook: lamp with a warm cone, Clawd left
    "lamp": [
        "..............................GGGG......",
        ".............................GGGGGG.....",
        "............................GGGGGGGG....",
        ".............................wwwwww.....",
        "............................wwwwwwww....",
        "...........................wwwwwwwwww...",
        "...............................GG.......",
        "...............................GG.......",
        "...............................GG.......",
        "gggggggggggggggggggggggggggggggggggggggg",
        "........................................",
    ],
    # late night: TV glow on the left, Clawd right
    "tv": [
        "........................................",
        "..GGGGGGGGGGGG..........................",
        "..Gbbbbbbbbbb G.........................",
        "..GbbbbbbbbbbG..........................",
        "..GbbbbbbbbbbG..........................",
        "..GbbbbbbbbbbG..........................",
        "..GGGGGGGGGGGG..........................",
        ".......GG...............................",
        "gggggggggggggggggggggggggggggggggggggggg",
        "........................................",
        "........................................",
    ],
    # rain: slanted streaks
    "rain": [
        ".s....s....s....s....s....s....s....s...",
        "..s....s....s....s....s....s....s....s..",
        "........................................",
        "s....s....s....s....s....s....s....s....",
        ".s....s....s....s....s....s....s....s...",
        "........................................",
        "...s....s....s....s....s....s....s....s.",
        "....s....s....s....s....s....s....s....s",
        "........................................",
        "gggggggggggggggggggggggggggggggggggggggg",
        "........................................",
    ],
    # snow: drifting flakes and a snow bank
    "snow": [
        "...s.......s.........s........s.........",
        ".........s.......s.........s.......s....",
        "..s....................s................",
        "......s.......s.............s......s....",
        "s..........s........s..........s........",
        "....s...........s.........s.............",
        ".........s..........s...........s.......",
        "..s...........s.............s.......s...",
        "........................................",
        "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
    ],
    # hot and sunny: big dim sun up high
    "sun": [
        "..................oooo..................",
        ".................oooooo.................",
        ".................oooooo.................",
        "..................oooo..................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "gggggggggggggggggggggggggggggggggggggggg",
        "........................................",
    ],
    # weekend yard: fence and grass
    "yard": [
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "G..G..G..G..G..G..G..G..G..G..G..G..G..G",
        "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        "G..G..G..G..G..G..G..G..G..G..G..G..G..G",
        "G..G..G..G..G..G..G..G..G..G..G..G..G..G",
        "........................................",
        "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        "........................................",
    ],
    # plain floor line, for moods and surprises
    "plain": [
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "........................................",
        "gggggggggggggggggggggggggggggggggggggggg",
        "........................................",
    ],
}

LIVING = {
    # night: stars twinkle (some dim, some drift)
    "night": lambda rows: [(rows, None), (rows, {"s": (60, 62, 66)}), (shift_stars(rows, 3), None), (rows, {"s": (120, 122, 128)})],
    # tv: screen glow flickers
    "tv": lambda rows: [(rows, None), (rows, {"b": (58, 66, 84)}), (rows, {"b": (40, 46, 58)}), (rows, {"b": (52, 60, 76)})],
    # lamp: warm cone breathes
    "lamp": lambda rows: [(rows, None), (rows, {"w": (72, 62, 52)}), (rows, {"w": (80, 68, 56)}), (rows, {"w": (72, 62, 52)})],
}
LIVING_MS = {"night": 900, "tv": 180, "lamp": 700}

if __name__ == "__main__":
    background()
    for name, rows in SCENES.items():
        rows = [r.replace(" ", ".") for r in rows]
        assert all(len(r) == W for r in rows), name
        if name in LIVING:
            scene_anim(name, LIVING[name](rows), LIVING_MS[name])
        else:
            scene(name, rows)
