"""
make_sprites.py - Draws Clawd (the Claude Code mascot) as pixel-art animated
WebP sprites: one idle loop per state, three tap reactions, the pulsing heart
and the small icons.

Every idle loop gets a blink: the 2-4 base frames cycle three times, then one
short frame with the eyes closed. Builders return grid "canvases" (lists of
character rows) so the blink can be applied generically before rendering.

Output: ../res/drawable/*.webp and *.png
Run:    python make_sprites.py      (requires Pillow)
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "res" / "drawable"
OUT.mkdir(parents=True, exist_ok=True)

SCALE = 12                       # one grid cell = 12 px
CW, CH = 22, 14                  # sprite canvas, cells (-> 264 x 168 px)

# ---- Palette: Claude brand + Redline accents ------------------------------
P = {
    ".": None,
    "O": (217, 119, 87),   # Claude orange
    "D": (201, 100, 66),   # Claude crail (shade)
    "K": (43, 42, 40),     # ink / eyes
    "W": (250, 249, 245),  # Claude ivory
    "S": (184, 189, 195),  # Redline silver
    "G": (74, 74, 74),     # gunmetal
    "L": (44, 44, 44),     # graphite
    "B": (90, 58, 30),     # coffee
    "Y": (242, 193, 78),   # cheese / flame
    "R": (215, 25, 32),    # Redline red
    "N": (106, 155, 209),  # book blue
    "E": (110, 200, 120),  # terminal green
    "Z": (184, 189, 195),  # zzz
    "C": (120, 180, 230),  # sweat
    "H": (230, 90, 90),    # flushed cheek
    "Q": (255, 200, 60),   # confetti gold
    "V": (120, 200, 160),  # confetti teal
    "X": (240, 120, 200),  # confetti pink
    "T": (110, 60, 40),    # cake
    "F": (255, 150, 70),   # pumpkin
    "U": (60, 140, 60),    # stem / umbrella
    "I": (31, 30, 29),     # opaque background (tap sprites)
}

# ---- Clawd bodies (14 x 9) ------------------------------------------------
BODY = [
    "..OOOOOOOOOO..",
    ".OOOOOOOOOOOO.",
    ".OOOOOOOOOOOO.",
    ".OOKKOOOOKKOO.",
    ".OOKKOOOOKKOO.",
    ".OOOOOOOOOOOO.",
    ".DDDDDDDDDDDD.",
    "..DDDDDDDDDD..",
    "...D.D..D.D...",
]
BODY_SLEEP = [r for r in BODY[:3]] + [".OOOOOOOOOOOO.", ".OOKKOOOOKKOO."] + BODY[5:]
BODY_CHEEKS = BODY[:4] + [".OHKKOOOOKKHO.", ".OHHOOOOOOHHO."] + BODY[6:]
BODY_YAWN = BODY[:3] + [".OOOOOOOOOOOO.", ".OOKKOOOOKKOO.", ".OOOOOKKOOOOO.", ".DDDDDKKDDDDD."] + BODY[7:]
BODY_HAPPY = BODY[:3] + [".OKOOKOOKOOKO.", ".OOKKOOOOKKOO."] + BODY[5:]
LEGS_A, LEGS_B = "...D.D..D.D...", "..D...D..D..D."


def blank():
    return [["."] * CW for _ in range(CH)]


def stamp(canvas, rows, x, y):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                yy, xx = y + j, x + i
                if 0 <= yy < CH and 0 <= xx < CW:
                    canvas[yy][xx] = ch


def blink(canvas):
    """Close any 2x2 'KK' eye block whose top row is sitting on body colour."""
    c = [row[:] for row in canvas]
    for y in range(1, CH - 1):
        for x in range(CW - 1):
            if (c[y][x] == c[y][x + 1] == "K" and c[y + 1][x] == c[y + 1][x + 1] == "K"
                    and c[y - 1][x] in "OH" and c[y - 1][x + 1] in "OH"):
                c[y][x] = c[y][x + 1] = "O"
    return c


def opaque(canvas):
    return [["I" if ch == "." else ch for ch in row] for row in canvas]


BODY_CELLS = set("ODH")
P["o"] = (122, 58, 36)          # 1-cell outline around Clawd's body


def outline(canvas):
    """Ring every empty cell that touches the body with a darker outline cell."""
    c = [row[:] for row in canvas]
    for y in range(CH):
        for x in range(CW):
            if canvas[y][x] not in (".", "I"):
                continue
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < CH and 0 <= xx < CW and canvas[yy][xx] in BODY_CELLS:
                    c[y][x] = "o"
                    break
    return c


def body_bounds(canvas):
    xs, ys = [], []
    for y in range(CH):
        for x in range(CW):
            if canvas[y][x] in BODY_CELLS:
                xs.append(x); ys.append(y)
    return (min(xs), max(xs), max(ys)) if xs else None


def render(canvas, scale=SCALE, decorate=True):
    src = outline(canvas) if decorate else canvas
    img = Image.new("RGBA", (CW * scale, CH * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if decorate:
        b = body_bounds(canvas)
        if b:
            x0, x1, yb = b
            cy = min((yb + 1) * scale + 2, CH * scale - 4)
            d.ellipse([x0 * scale + 6, cy - 5, (x1 + 1) * scale - 6, cy + 5], fill=(0, 0, 0, 115))
    for j in range(CH):
        for i in range(CW):
            col = P[src[j][i]]
            if col:
                d.rectangle([i * scale, j * scale, (i + 1) * scale - 1, (j + 1) * scale - 1], fill=col + (255,))
    return img


def save_anim(name, canvases, ms, with_blink=True, still=True):
    frames, durs = [], []
    if with_blink:
        seq = canvases * 3
        frames = [render(c) for c in seq] + [render(blink(canvases[0]))]
        durs = [ms] * len(seq) + [110]
    else:
        frames = [render(c) for c in canvases]
        durs = [ms] * len(canvases)
    frames[0].save(OUT / f"{name}.webp", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, lossless=True, method=6)
    if still:
        frames[0].save(OUT / f"{name}_still.png")
    print(f"wrote {name:16s} {len(frames)} frames")


# ---- Dayparts -------------------------------------------------------------
def sleep():
    out = []
    zz = [["..Z..", ".ZZZ.", "...Z.", ".ZZZ."], ["Z....", "ZZZ..", "..Z..", "ZZZ.."], [".....", "..Z..", ".ZZZ.", "...Z."]]
    for k in range(3):
        c = blank()
        stamp(c, BODY_SLEEP, 2, 5 + (k == 1))
        stamp(c, zz[k], 16, k)
        stamp(c, ["....RRRR", "...RRRRR", "..RRRRRW"], 2, 3 + (k == 1))
        out.append(c)
    return out


def coffee():
    out = []
    steam = [["W.W", ".W.", "W.W"], [".W.", "W.W", ".W."], ["W.W", "W.W", ".W."]]
    for k in range(3):
        c = blank()
        stamp(c, BODY, 2, 5 - (k == 1))
        stamp(c, ["SSSS.", "SBBSS", "SBBSS", "SSSS."], 16, 7)
        stamp(c, steam[k], 17, 3)
        out.append(c)
    return out


def code():
    out = []
    screens = [["GLE.ELG", "GL.EELG"], ["GLEE.LG", "GLE.ELG"], ["GLEEELG", "GL..ELG"], ["GLE..LG", "GLEEELG"]]
    for k in range(4):
        c = blank()
        stamp(c, BODY, 1, 2)
        stamp(c, ["GGGGGGG", "GLLLLLG"] + screens[k] + ["GLLLLLG", "GGGGGGG"], 14, 4)
        stamp(c, ["GGGGGGGG", "SSSSSSSS"], 14, 10)
        stamp(c, ["D", "D"] if k % 2 == 0 else ["D", "."], 13, 9)
        out.append(c)
    return out


def lunch():
    out = []
    pizza = [["..Y.", ".YYR", "YRYY", "YYYY"], ["....", ".YR.", "YRYY", "YYYY"], ["....", "....", ".RYY", "YYYY"]]
    for k in range(3):
        c = blank()
        stamp(c, BODY, 2, 4 + (k == 1))
        stamp(c, pizza[k], 16, 6)
        out.append(c)
    return out


def walk():
    out = []
    for k in range(4):
        c = blank()
        stamp(c, BODY[:-1] + [LEGS_A if k % 2 == 0 else LEGS_B], 4, 3 + (k % 2))
        stamp(c, ["SS", "..", "SS"] if k % 2 == 0 else ["..", "SS", ".."], 1, 6)
        out.append(c)
    return out


def lift():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY, 4, 5)
        stamp(c, ["G.........G", "GGGGGGGGGGG", "G.........G"], 5, 1 + k * 2)
        stamp(c, ["D"], 6, 4 + k)
        stamp(c, ["D"], 15, 4 + k)
        out.append(c)
    return out


def read():
    out = []
    pages = [["NWWWWN", "NWSSWN", "NWWWWN"], ["NWWWWN", "NWWWWN", "NWWWWN"], ["NWWWWN", "NWWSSN", "NWWWWN"]]
    for k in range(3):
        c = blank()
        stamp(c, BODY, 1, 3)
        stamp(c, ["NNNNNN"] + pages[k] + ["NNNNNN"], 15, 6)
        out.append(c)
    return out


def game():
    out = []
    pads = ["GWG.RG", "G.GRGG", "GWGRGG"]
    for k in range(3):
        c = blank()
        stamp(c, BODY, 2, 3 + (k == 1))
        stamp(c, ["GGGGGG", pads[k], "GGGGGG"], 15, 8)
        out.append(c)
    return out


# ---- Moods -----------------------------------------------------------------
def hot():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY_CHEEKS, 2 + k, 4)
        stamp(c, [".C", "CC"] if k == 0 else ["C.", "CC"], 16, 3 + k)
        stamp(c, ["C"], 1, 6 + k)
        out.append(c)
    return out


def celebrate():
    out = []
    conf = [["Q...V...X.....Q.......", "...X...Q....V....X...."], ["...V...Q....X.....Q...", "Q....X....V.....X....."]]
    for k in range(2):
        c = blank()
        stamp(c, BODY_HAPPY, 4, 2 + k * 3)
        stamp(c, conf[k], 0, k)
        out.append(c)
    return out


def lowbatt():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY_YAWN if k == 0 else BODY_SLEEP, 2, 5)
        stamp(c, ["RRRRR.", "R...RR", "RR..RR", "R...RR", "RRRRR."], 16, 2 + k)
        out.append(c)
    return out


# ---- Calendar surprises ---------------------------------------------------
def friday():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY, 2, 5 - k)
        stamp(c, ["..UUU", ".UUUUU", "...W..", "..WYW.", "..WYW.", "..WWW.", "...S..", "..SSS."], 15, 2)
        out.append(c)
    return out


def halloween():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY, 2, 5)
        stamp(c, ["....U.", "..FFFF", ".FKFKF", ".FFFFF", ".FKKKF"], 5, k)
        out.append(c)
    return out


def xmas():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY, 2, 5 - k)
        stamp(c, ["......W", "....RRW", "..RRRR.", ".RRRRR.", "WWWWWW."], 3, 2 - k)
        out.append(c)
    return out


def newyear():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY_HAPPY, 2, 5)
        stamp(c, ["...Q", "..XX", ".VVV", "QQQQ"], 7, 1)
        stamp(c, ["Q..V..X", ".X..Q.."] if k == 0 else [".V..Q..", "X..X..V"], 14, 2)
        out.append(c)
    return out


def birthday():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY_HAPPY, 1, 5)
        stamp(c, ["..F.", "..Y."] if k == 0 else ["..Y.", "..F."], 15, 3)
        stamp(c, ["..W.", "XXXX", "TTTT", "TTTT", "SSSS"], 15, 5)
        out.append(c)
    return out


# ---- Weather ---------------------------------------------------------------
def rain():
    """Rain: umbrella overhead, drops falling."""
    out = []
    drops = [["C....C...", "...C....C", "C....C..."], ["..C....C.", "C....C...", "...C....C"]]
    for k in range(2):
        c = blank()
        stamp(c, BODY, 2, 5)
        stamp(c, ["...NNNNNNNNN...", "..NNNNNNNNNNN..", ".NNNNNNNNNNNNN.", ".......S.......", ".......S......."], 1, 0)
        stamp(c, drops[k], 13, 3 + k)
        out.append(c)
    return out


def snow():
    """Snow: red scarf, flakes drifting."""
    out = []
    flakes = [["W...W..", "..W...W", "W...W.."], [".W...W.", "W...W..", "..W...W"]]
    for k in range(2):
        c = blank()
        stamp(c, BODY, 2, 5 - k)
        stamp(c, ["RRRRRRRRRRRR", "....RR......", "....RR......"], 2, 10 - k)
        stamp(c, flakes[k], 15, 1 + k)
        stamp(c, flakes[1 - k], 0, 2 + k)
        out.append(c)
    return out


def sunny():
    """Hot day: sunglasses, sun blazing."""
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY, 2, 5)
        stamp(c, [".KKKKKKKKKK.", "KKKK.KK.KKKK", ".KKK....KKK."], 3, 8)   # shades over eyes
        stamp(c, ["Y.Y.Y", ".YYY.", "YYYYY" if k == 0 else "YYYYY", ".YYY.", "Y.Y.Y"], 16, 1 + k)
        out.append(c)
    return out


# ---- Notifications --------------------------------------------------------
def mail():
    """Unread notifications: holding an envelope (count drawn over it in XML)."""
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY, 1, 5 - k)
        stamp(c, ["WWWWWWW", "WSWWWSW", "WWSWSWW", "WWWSWWW", "WWWWWWW"], 14, 6)
        stamp(c, ["D"], 13, 9 - k)
        out.append(c)
    return out


# ---- Weekend ----------------------------------------------------------------
def guitar():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY_HAPPY if k else BODY, 2, 4)
        stamp(c, ["T", "T", "T", "T"], 14, 3)
        stamp(c, ["..SS.", ".TTTT", "TTTTT", "TTTTT", ".TTT."], 12, 7)
        stamp(c, ["Z..", ".Z.", "..Z"] if k == 0 else [".Z.", "..Z", "Z.."], 18, 2)
        out.append(c)
    return out


def grill():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY, 1, 4)
        stamp(c, ["GGGGGGG", "GBBRBBG", "GGGGGGG", "..G.G..", "..G.G.."], 14, 7)
        stamp(c, ["S.S", ".S.", "S.S"] if k == 0 else [".S.", "S.S", ".S."], 16, 3)
        out.append(c)
    return out


def hammock():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, ["G", "G", "G", "G", "G", "G", "G", "G", "G"], 1, 2)
        stamp(c, ["G", "G", "G", "G", "G", "G", "G", "G", "G"], 20, 2)
        stamp(c, BODY_SLEEP, 4, 3 + k)
        stamp(c, [".SS................SS.", "...SSS..........SSS...", "......SSSSSSSSSS......"], 0, 10 + k)
        stamp(c, ["Z..", ".Z."] if k == 0 else [".Z.", "Z.."], 17, 1)
        out.append(c)
    return out


def football():
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY_HAPPY if k else BODY, 2, 5)
        stamp(c, ["..TTT.", ".TWTWT", "TTWWWT", "TWTWT.", ".TTT.."], 15, 5 - k)
        out.append(c)
    return out


# ---- Tap reactions (opaque, 4 frames, no blink) ---------------------------
def tap_wave():
    out = []
    arm = [["..D", ".D.", "D.."], ["D..", ".D.", "..D"]]
    heart = [".H.H.", "HHHHH", ".HHH.", "..H.."]
    for k in range(4):
        c = blank()
        stamp(c, BODY_HAPPY if k >= 2 else BODY, 2, 5)
        stamp(c, arm[k % 2], 15, 3)
        stamp(c, heart, 16, 8 - (k // 2))
        out.append(opaque(c))
    return out


def tap_pizza():
    out = []
    for k in range(4):
        c = blank()
        stamp(c, BODY_HAPPY, 2, 5)
        stamp(c, ["...Y..", "..YYR.", ".YRYYY", "YYYYYY", ".YYRY."], 15 - k, 4 + k // 2)
        out.append(opaque(c))
    return out


def tap_pump():
    out = []
    for k in range(4):
        c = blank()
        stamp(c, BODY_HAPPY if k % 2 else BODY, 2, 5 - (k % 2))
        stamp(c, ["DD", "DD"], 15, 2 + (k % 2) * 3)
        stamp(c, ["E.E.E", ".E.E.", "E.E.E"] if k % 2 else ["....."], 17, 7)
        out.append(opaque(c))
    return out


def charging():
    """On the charger: cable in, bolt blinking, content eyes."""
    out = []
    for k in range(2):
        c = blank()
        stamp(c, BODY_HAPPY if k else BODY, 2, 5)
        stamp(c, ["GG", "GG", ".G", ".G", ".G", ".G"], 16, 7)          # plug + cable
        stamp(c, ["SSSSSSSS"], 16, 13)
        stamp(c, ["..Y.", ".YY.", "YYYY", "..Y.", ".Y.."] if k == 0 else ["....", "..Y.", ".YY.", "YYYY", "..Y."], 17, 1)
        out.append(c)
    return out


def flip():
    """Top of the hour: squat, jump, backflip, land. Opaque, 6 frames."""
    out = []
    squat = BODY[:2] + BODY[3:]                # one row shorter
    upside = [row[::-1] for row in BODY[::-1]]  # rotated 180
    seq = [(BODY, 5), (squat, 6), (BODY, 2), (upside, 1), (BODY, 3), (BODY, 5)]
    for rows, y in seq:
        c = blank()
        stamp(c, rows, 2, y)
        out.append(opaque(c))
    return out


# ---- Moon phases (28 px, 0 new .. 4 full .. 7 waning crescent) -------------
def moons():
    import math
    size, r = 28, 12
    for phase in range(8):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cx = cy = size // 2
        lit = (200, 190, 150, 255)
        dark = (58, 58, 58, 255)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dark)
        # fraction illuminated, 0..1..0, and which side is lit
        f = (1 - math.cos(phase / 8 * 2 * math.pi)) / 2
        for y in range(-r, r + 1):
            half = int(math.sqrt(max(r * r - y * y, 0)))
            # terminator x for this row
            t = int(round((2 * f - 1) * half))
            if phase <= 4:      # waxing: right side lit
                x0, x1 = -t if phase < 4 else -half, half
                x0 = max(-half, -t) if phase < 4 else -half
                if phase == 0:
                    continue
                d.line([cx + x0, cy + y, cx + x1, cy + y], fill=lit)
            else:               # waning: left side lit
                x0, x1 = -half, min(half, t)
                d.line([cx + x0, cy + y, cx + x1, cy + y], fill=lit)
        img.save(OUT / f"moon_{phase}.png")
    print("wrote moon_0..7")


# ---- Icons ------------------------------------------------------------------
ICON_STEPS = ["....OO......", "...OOOO.....", "...OOOO.....", "....OO......", "........OO..", ".......OOOO.",
              ".......OOOO.", "........OO..", "....OO......", "...OOOO.....", "...OOOO.....", "....OO......"]
ICON_HEART = ["............", "..OO...OO...", ".OOOO.OOOO..", ".OOOOOOOOO..", ".OOOOOOOOO..", "..OOOOOOO...",
              "...OOOOO....", "....OOO.....", ".....O......", "............", "............", "............"]
ICON_BATT = ["............", "............", "............", "OOOOOOOOOO..", "O........OO.", "O.OOOOOO.OO.",
             "O.OOOOOO.OO.", "O........OO.", "OOOOOOOOOO..", "............", "............", "............"]
REDLINE = ["SSSS...S....", "S...S..S....", "S...S..S....", "SSSS...S....", "S..S...S....", "S...S..S....",
           "S...S..SSSSS", "............", "RRRRRRRRRRRR"]


def icon(name, rows, scale=2):
    h, w = len(rows), len(rows[0])
    img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for j in range(h):
        for i in range(w):
            if rows[j][i] != ".":
                d.rectangle([i * scale, j * scale, (i + 1) * scale - 1, (j + 1) * scale - 1], fill=P[rows[j][i]] + (255,))
    img.save(OUT / f"{name}.png")


def ambient_clawd():
    """Always-on Clawd: outline and closed eyes only, dim silver, no fill."""
    c = blank()
    stamp(c, BODY_SLEEP, 2, 5)
    src = outline(c)
    img = Image.new("RGBA", (CW * SCALE, CH * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dim = (150, 154, 160, 255)
    for j in range(CH):
        for i in range(CW):
            ch = src[j][i]
            if ch == "o" or ch == "K":
                d.rectangle([i * SCALE, j * SCALE, (i + 1) * SCALE - 1, (j + 1) * SCALE - 1], fill=dim)
    img.save(OUT / "clawd_ambient.png")
    print("wrote clawd_ambient")


def data_pills():
    """Three rounded pills behind the data row (480 x 44)."""
    img = Image.new("RGBA", (480, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x0, x1 in ((56, 198), (204, 284), (290, 432)):
        d.rounded_rectangle((x0, 2, x1, 41), radius=20, fill=(38, 37, 36, 255), outline=(62, 61, 60, 255), width=2)
    img.save(OUT / "data_pills.png")
    print("wrote data_pills")


def heart_pulse():
    full = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(full)
    for j, row in enumerate(ICON_HEART):
        for i, ch in enumerate(row):
            if ch != ".":
                d.rectangle([i * 2, j * 2, i * 2 + 1, j * 2 + 1], fill=P["O"] + (255,))
    small = full.resize((18, 18), Image.NEAREST)
    f2 = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    f2.paste(small, (3, 3), small)
    full.save(OUT / "ic_heart_pulse.webp", save_all=True, append_images=[f2], duration=[650, 250], loop=0, lossless=True)


if __name__ == "__main__":
    for old in list(OUT.glob("*.gif")) + list(OUT.glob("clawd_*.webp")) + list(OUT.glob("tap_*.webp")):
        old.unlink()
    save_anim("clawd_sleep", sleep(), 600)
    save_anim("clawd_coffee", coffee(), 400)
    save_anim("clawd_code", code(), 220)
    save_anim("clawd_lunch", lunch(), 450)
    save_anim("clawd_walk", walk(), 220)
    save_anim("clawd_lift", lift(), 600)
    save_anim("clawd_read", read(), 700)
    save_anim("clawd_game", game(), 200)
    save_anim("clawd_hot", hot(), 250)
    save_anim("clawd_celebrate", celebrate(), 300)
    save_anim("clawd_lowbatt", lowbatt(), 900)
    save_anim("clawd_friday", friday(), 500)
    save_anim("clawd_halloween", halloween(), 600)
    save_anim("clawd_xmas", xmas(), 500)
    save_anim("clawd_newyear", newyear(), 300)
    save_anim("clawd_birthday", birthday(), 400)
    save_anim("clawd_rain", rain(), 300)
    save_anim("clawd_snow", snow(), 450)
    save_anim("clawd_sunny", sunny(), 500)
    save_anim("clawd_mail", mail(), 500)
    save_anim("clawd_guitar", guitar(), 350)
    save_anim("clawd_grill", grill(), 400)
    save_anim("clawd_hammock", hammock(), 800)
    save_anim("clawd_football", football(), 300)
    save_anim("clawd_charging", charging(), 500)
    save_anim("tap_flip", flip(), 110, with_blink=False, still=False)
    moons()
    save_anim("tap_wave", tap_wave(), 150, with_blink=False, still=False)
    save_anim("tap_pizza", tap_pizza(), 150, with_blink=False, still=False)
    save_anim("tap_pump", tap_pump(), 150, with_blink=False, still=False)
    heart_pulse()
    ambient_clawd()
    data_pills()
    # icons are drawn white and tinted on the watch by the theme colour
    P["O"] = (255, 255, 255)
    icon("ic_steps", ICON_STEPS)
    icon("ic_heart", ICON_HEART)
    icon("ic_batt", ICON_BATT)
    P["O"] = (217, 119, 87)
    icon("redline_mark", REDLINE, scale=3)
    icon("redline_mark_lg", REDLINE, scale=4)
    print("done ->", OUT)
