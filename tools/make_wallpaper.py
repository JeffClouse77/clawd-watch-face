"""
make_wallpaper.py - Matching phone wallpaper: Clawd at his desk on the Claude
background with the Redline RL mark, 1080 x 2400 (fits most Samsung phones).

Output: ../wallpaper/clawd_wallpaper.png and clawd_lockscreen.png
Run:    python make_wallpaper.py   (after make_sprites.py)
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "res" / "drawable"
OUT = ROOT / "wallpaper"
OUT.mkdir(exist_ok=True)

W, H = 1080, 2400
BG = (31, 30, 29)
ORANGE = (217, 119, 87)
SILVER = (184, 189, 195)
GRAPHITE = (44, 44, 44)


def frame0(name):
    im = Image.open(D / name)
    im.seek(0)
    return im.convert("RGBA")


def build(name, sprite, scene, with_mark=True):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    # faint blueprint grid (Redline graphic language, very low contrast)
    for x in range(0, W, 60):
        d.line([x, 0, x, H], fill=(36, 35, 34, 255))
    for y in range(0, H, 60):
        d.line([0, y, W, y], fill=(36, 35, 34, 255))
    # scene strip, scaled 2.25x, centred vertically a bit below middle
    sc = frame0(scene).resize((1080, 288), Image.NEAREST)
    sy = 1380
    img.paste(sc, (0, sy), sc)
    # Clawd, scaled 3x (792 x 504), standing on the scene floor line
    sp = frame0(sprite).resize((792, 504), Image.NEAREST)
    img.paste(sp, ((W - 792) // 2, sy + 288 - 504 + 60), sp)
    if with_mark:
        rl = Image.open(D / "redline_mark_lg.png").convert("RGBA").resize((144, 108), Image.NEAREST)
        img.paste(rl, ((W - 144) // 2, H - 300), rl)
    img.save(OUT / name)
    print("wrote", OUT / name)


if __name__ == "__main__":
    build("clawd_wallpaper.png", "clawd_code.webp", "scene_work.png")
    build("clawd_lockscreen.png", "clawd_sleep.webp", "scene_night.png", with_mark=False)
