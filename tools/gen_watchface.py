"""
gen_watchface.py - Generates res/raw/watchface.xml for the Clawd face.

Why a generator: Clawd has ~18 states (moods, calendar surprises, dayparts),
each with a backdrop scene, an idle loop, a tap reaction and a caption.
Hand-editing that XML is error-prone, so the layout lives here as data.

Priority of what Clawd shows (first match wins):
  1. Mood from health data   heart rate > 120 / 10k steps / battery < 15%
  2. Calendar surprise       birthday, Oct 31, Dec 25, Jan 1, Fri after 5pm
  3. Daypart                 sleep, coffee, code, lunch, walk, ship, gym, read, game

Other behaviour:
  - Clock colour follows the hour: ivory by day, amber evening, silver overnight.
  - Ambient mode: rings, data row and the live Clawd fade out; a still of
    Clawd asleep fades in and the clock thins to a regular weight.

Run:  python gen_watchface.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "res" / "raw" / "watchface.xml"
BITMAPFONTS = Path(__file__).with_name("bitmapfont.xml").read_text(encoding="utf-8")  # from make_font.py

BIRTHDAY = None           # e.g. (3, 14) for March 14 -> cake with candle
STEP_GOAL = 10000                      # fallback when the watch reports no goal
GOAL = "([STEP_GOAL] > 0 ? [STEP_GOAL] : 10000)"

# Colours
IVORY, ORANGE, CRAIL = "#FFFAF9F5", "#FFD97757", "#FFC96442"
ACCENT = "[CONFIGURATION.theme.0]"       # user-picked accent (default Claude orange)
ACCENT2 = "[CONFIGURATION.theme.1]"
AMBER, NIGHT = "#FFE8C9A0", "#FFB8BDC3"          # evening / overnight clock tints
SILVER, RED, GRAPHITE, GUNMETAL = "#FFB8BDC3", "#FFD71920", "#FF2C2C2C", "#FF4A4A4A"
BG = "#FF1F1E1D"
HEALTH_APP = "com.samsung.android.wear.shealth"
WEATHER_APP = "com.samsung.android.watch.weather"

# Clawd band geometry (sprites are 264x168, drawn at 75%)
SW, SH = 198, 126
POS = {"left": 30, "center": 141, "right": 252}
H = "[HOUR_0_23]"


LIVING_SCENES = {"night", "tv", "lamp"}      # animated WebP backdrops (make_scenes.py)


def scene_xml(scene):
    if scene in LIVING_SCENES:
        return f'''
            <PartAnimatedImage x="0" y="0" width="480" height="128">
                <AnimatedImage resource="scene_{scene}" format="WEBP" />
                <AnimationController play="ON_VISIBLE" repeat="TRUE" resumePlayBack="TRUE" />
            </PartAnimatedImage>'''
    return f'''
            <PartImage x="0" y="0" width="480" height="128">
                <Image resource="scene_{scene}" />
            </PartImage>'''


def state(idle, tap, label, pos, scene, overlay=""):
    """One Clawd state: backdrop + idle loop + tap reaction on top + caption.
    overlay: extra XML drawn above the sprite (e.g. the unread count)."""
    x = POS[pos]
    # pixel font is ~13.7 px per glyph at size 16; caption boxes run to the panel edge (18..462)
    if pos == "right":
        cw = x - 4 - 18
        cap = f'''
            <PartText x="18" y="54" width="{cw}" height="24">
                <Text align="END"><BitmapFont family="pixel" size="16" color="{SILVER}">{label}</BitmapFont></Text>
            </PartText>'''
    else:
        cx = x + SW + 4
        cw = 462 - cx
        cap = f'''
            <PartText x="{cx}" y="54" width="{cw}" height="24">
                <Text align="START"><BitmapFont family="pixel" size="16" color="{SILVER}">{label}</BitmapFont></Text>
            </PartText>'''
    return f'''
        <Group x="0" y="0" width="480" height="128">
{scene_xml(scene)}{cap}
            <PartAnimatedImage x="{x}" y="0" width="{SW}" height="{SH}">
                <Transform target="x" value="{x} + clamp([ACCELEROMETER_ANGLE_X], -45, 45) / 45 * 8" />
                <AnimatedImage resource="{idle}" format="WEBP" />
                <AnimationController play="ON_VISIBLE" repeat="TRUE" resumePlayBack="TRUE" />
            </PartAnimatedImage>
            <PartAnimatedImage x="{x}" y="0" width="{SW}" height="{SH}">
                <AnimatedImage resource="{tap}" format="WEBP" />
                <AnimationController play="TAP" beforePlaying="HIDE" afterPlaying="HIDE" />
            </PartAnimatedImage>
            <PartAnimatedImage x="{x}" y="0" width="{SW}" height="{SH}">
                <AnimatedImage resource="tap_flip" format="WEBP" />
                <AnimationController play="ON_NEXT_HOUR" beforePlaying="HIDE" afterPlaying="HIDE" />
            </PartAnimatedImage>{overlay}
        </Group>'''


def condition(exprs, branches, default):
    e = "".join(f'\n            <Expression name="{n}">{x}</Expression>' for n, x in exprs)
    b = "".join(f'\n        <Compare expression="{n}">{body}\n        </Compare>' for n, body in branches)
    return f'''
    <Condition>
        <Expressions>{e}
        </Expressions>{b}
        <Default>{default}
        </Default>
    </Condition>'''


# --- moon phase (0 new .. 4 full .. 7) drawn top-right of night scenes ------
moon_overlay = (
    "\n            <Condition>\n                <Expressions>"
    + "".join(f'\n                    <Expression name="m{i}">[MOON_PHASE_TYPE] == {i}</Expression>' for i in range(1, 8))
    + "\n                </Expressions>"
    + "".join(
        f'\n                <Compare expression="m{i}"><PartImage x="396" y="6" width="28" height="28"><Image resource="moon_{i}" /></PartImage></Compare>'
        for i in range(1, 8))
    + '\n                <Default><PartImage x="396" y="6" width="28" height="28"><Image resource="moon_0" /></PartImage></Default>'
    + "\n            </Condition>"
)

# --- 3. dayparts -----------------------------------------------------------
daypart_exprs = [
    ("sleep",  f"{H} &lt; 6"),
    ("coffee", f"{H} &gt;= 6 &amp;&amp; {H} &lt; 8"),
    ("code",   f"{H} &gt;= 8 &amp;&amp; {H} &lt; 12"),
    ("lunch",  f"{H} &gt;= 12 &amp;&amp; {H} &lt; 13"),
    ("walk",   f"{H} &gt;= 13 &amp;&amp; {H} &lt; 14"),
    ("ship",   f"{H} &gt;= 14 &amp;&amp; {H} &lt; 17"),
    ("gym",    f"{H} &gt;= 17 &amp;&amp; {H} &lt; 19"),
    ("read",   f"{H} &gt;= 19 &amp;&amp; {H} &lt; 21"),
]
daypart_branches = [
    ("sleep",  state("clawd_sleep",  "tap_wave",  "sleeping", "left",   "night", moon_overlay)),
    ("coffee", state("clawd_coffee", "tap_wave",  "coffee",   "center", "morning")),
    ("code",   state("clawd_code",   "tap_pump",  "coding",   "right",  "work")),
    ("lunch",  state("clawd_lunch",  "tap_pizza", "lunch",    "center", "lunch")),
    ("walk",   state("clawd_walk",   "tap_wave",  "walking",  "left",   "park")),
    ("ship",   state("clawd_code",   "tap_pump",  "shipping", "right",  "work")),
    ("gym",    state("clawd_lift",   "tap_wave",  "gym",      "center", "gym")),
    ("read",   state("clawd_read",   "tap_wave",  "reading",  "left",   "lamp")),
]
dayparts = condition(daypart_exprs, daypart_branches,
                     state("clawd_game", "tap_wave", "gaming", "right", "tv"))

# --- 3b. weekend schedule (Sat/Sun) -----------------------------------------
weekend_exprs = [
    ("wsleep",   f"{H} &lt; 8"),
    ("wcoffee",  f"{H} &gt;= 8 &amp;&amp; {H} &lt; 10"),
    ("wguitar",  f"{H} &gt;= 10 &amp;&amp; {H} &lt; 12"),
    ("wgrill",   f"{H} &gt;= 12 &amp;&amp; {H} &lt; 14"),
    ("wgame",    f"{H} &gt;= 14 &amp;&amp; {H} &lt; 17"),
    ("whammock", f"{H} &gt;= 17 &amp;&amp; {H} &lt; 19"),
    ("wread",    f"{H} &gt;= 19 &amp;&amp; {H} &lt; 21"),
]
weekend_branches = [
    ("wsleep",   state("clawd_sleep",    "tap_wave", "sleeping in", "left",   "night", moon_overlay)),
    ("wcoffee",  state("clawd_coffee",   "tap_wave", "coffee", "center", "morning")),
    ("wguitar",  state("clawd_guitar",   "tap_wave", "jamming",     "center", "yard")),
    ("wgrill",   state("clawd_grill",    "tap_wave", "grilling",    "center", "yard")),
    ("wgame",    state("clawd_football", "tap_wave", "the game",    "right",  "tv")),
    ("whammock", state("clawd_hammock",  "tap_wave", "hammock",     "center", "yard")),
    ("wread",    state("clawd_read",     "tap_wave", "reading",     "left",   "lamp")),
]
weekend = condition(weekend_exprs, weekend_branches,
                    state("clawd_game", "tap_wave", "gaming", "right", "tv"))
schedule = condition([("weekend", "[DAY_OF_WEEK] == 1 || [DAY_OF_WEEK] == 7")],
                     [("weekend", weekend)], dayparts)

# --- 2. calendar surprises -------------------------------------------------
surprise_exprs = [
    ("fri",   f"[DAY_OF_WEEK] == 6 &amp;&amp; {H} &gt;= 17"),
    ("hallo", "[MONTH] == 10 &amp;&amp; [DAY] == 31"),
    ("xmas",  "[MONTH] == 12 &amp;&amp; [DAY] == 25"),
    ("ny",    "[MONTH] == 1 &amp;&amp; [DAY] == 1"),
]
surprise_branches = [
    ("hallo", state("clawd_halloween", "tap_wave", "boo!",       "center", "night", moon_overlay)),
    ("xmas",  state("clawd_xmas",      "tap_wave", "xmas!", "center", "night", moon_overlay)),
    ("ny",    state("clawd_newyear",   "tap_wave", "new year!",  "center", "plain")),
    ("fri",   state("clawd_friday",    "tap_wave", "weekend!",   "center", "plain")),
]
if BIRTHDAY:
    m, d = BIRTHDAY
    surprise_exprs.insert(0, ("bday", f"[MONTH] == {m} &amp;&amp; [DAY] == {d}"))
    surprise_branches.insert(0, ("bday", state("clawd_birthday", "tap_wave", "cake!", "center", "plain")))
surprises = condition(surprise_exprs, surprise_branches, schedule)

# --- 2b. weather (needs format version 2) ------------------------------------
# Condition codes: 4 heavy rain, 6 rain, 9 thunderstorm, 10 sleet, 12 light rain
#                  5 heavy snow, 7 snow, 11 light snow
# Temperature compared in Fahrenheit; unit 1 = Celsius.
W = "[WEATHER.CONDITION]"
TEMP_F = "([WEATHER.TEMPERATURE_UNIT] == 1 ? [WEATHER.TEMPERATURE] * 9 / 5 + 32 : [WEATHER.TEMPERATURE])"
weather_exprs = [
    ("rain", f"[WEATHER.IS_AVAILABLE] &amp;&amp; ({W} == 4 || {W} == 6 || {W} == 9 || {W} == 10 || {W} == 12)"),
    ("snow", f"[WEATHER.IS_AVAILABLE] &amp;&amp; ({W} == 5 || {W} == 7 || {W} == 11)"),
    ("hot",  f"[WEATHER.IS_AVAILABLE] &amp;&amp; [WEATHER.IS_DAY] &amp;&amp; {TEMP_F} &gt;= 90"),
]
weather_branches = [
    ("rain", state("clawd_rain",  "tap_wave", "rainy",    "center", "rain")),
    ("snow", state("clawd_snow",  "tap_wave", "snow day", "center", "snow")),
    ("hot",  state("clawd_sunny", "tap_wave", "scorcher", "center", "sun")),
]
weather = condition(weather_exprs, weather_branches, surprises)

# --- 1b. unread notifications ----------------------------------------------
count_overlay = f'''
            <PartText x="{POS["center"] + 150}" y="18" width="48" height="30">
                <Text align="CENTER"><Font family="orbitron_bold" size="22" weight="BOLD" color="{RED}">
                    <Template>%d<Parameter expression="[UNREAD_NOTIFICATION_COUNT]" /></Template></Font></Text>
            </PartText>'''
mail = condition([("mail", "[UNREAD_NOTIFICATION_COUNT] &gt; 0")],
                 [("mail", state("clawd_mail", "tap_wave", "mail!", "center", "plain", count_overlay))],
                 weather)

# --- 1. moods from health data --------------------------------------------
mood_exprs = [
    ("chg",  "[BATTERY_CHARGING_STATUS]"),
    ("hot",  "[HEART_RATE] &gt; 120"),
    ("done", f"[STEP_COUNT] &gt;= {GOAL}"),
    ("low",  "[BATTERY_PERCENT] &lt; 15 &amp;&amp; [BATTERY_PERCENT] &gt; 0"),
]
mood_branches = [
    ("chg",  state("clawd_charging",  "tap_wave", "charging",    "center", "plain")),
    ("hot",  state("clawd_hot",       "tap_wave", "cardio!",     "center", "plain")),
    ("low",  state("clawd_lowbatt",   "tap_wave", "low battery", "left",   "plain")),
    ("done", state("clawd_celebrate", "tap_wave", "goal!",       "center", "plain")),
]
live = condition(mood_exprs, mood_branches, mail)

# Showcase (Customize > Showcase): option 0 is the live tree, the rest force a state.
SHOWCASE = [
    ("1",  state("clawd_rain",      "tap_wave",  "rainy",       "center", "rain")),
    ("2",  state("clawd_snow",      "tap_wave",  "snow day",    "center", "snow")),
    ("3",  state("clawd_sunny",     "tap_wave",  "scorcher",    "center", "sun")),
    ("4",  state("clawd_mail",      "tap_wave",  "mail!",       "center", "plain", count_overlay)),
    ("5",  state("clawd_celebrate", "tap_wave",  "goal!",       "center", "plain")),
    ("6",  state("clawd_hot",       "tap_wave",  "cardio!",     "center", "plain")),
    ("7",  state("clawd_lowbatt",   "tap_wave",  "low battery", "left",   "plain")),
    ("8",  state("clawd_charging",  "tap_wave",  "charging",    "center", "plain")),
    ("9",  state("clawd_birthday",  "tap_wave",  "cake!",  "center", "plain")),
    ("10", state("clawd_halloween", "tap_wave",  "boo!",        "center", "night", moon_overlay)),
    ("11", state("clawd_xmas",      "tap_wave",  "xmas!",  "center", "night", moon_overlay)),
    ("12", state("clawd_newyear",   "tap_wave",  "new year!",   "center", "plain")),
    ("13", state("clawd_friday",    "tap_wave",  "weekend!",    "center", "plain")),
    ("14", state("clawd_grill",     "tap_wave",  "grilling",    "center", "yard")),
    ("15", state("clawd_hammock",   "tap_wave",  "hammock",     "center", "yard")),
]
def band(body):
    """The Clawd band Group (hidden in ambient) around one option's subtree."""
    return ('\n        <Group x="0" y="176" width="480" height="128" name="clawd_band" alpha="255">'
            '\n            <Variant mode="AMBIENT" target="alpha" value="0" />' + body + '\n        </Group>')


# Showcase list sits directly under Scene, like Google's Flavors sample; each
# option carries its own copy of the band so the editor can swap the whole tree.
clawd = (
    '\n    <ListConfiguration id="show">'
    + f'\n        <ListOption id="0">{band(live)}\n        </ListOption>'
    + "".join(f'\n        <ListOption id="{i}">{band(body)}\n        </ListOption>' for i, body in SHOWCASE)
    + "\n    </ListConfiguration>"
)


# --- clock, tinted by hour --------------------------------------------------
def clock(main, secs):
    return f'''
        <DigitalClock x="0" y="62" width="480" height="112">
            <TimeText format="hh:mm" hourFormat="SYNC_TO_DEVICE" align="CENTER" x="3" y="11" width="400" height="100" alpha="200">
                <Font family="orbitron_bold" size="82" weight="BOLD" color="#FF0A0A0B" />
                <Variant mode="AMBIENT" target="alpha" value="0" />
            </TimeText>
            <TimeText format="hh:mm" hourFormat="SYNC_TO_DEVICE" align="CENTER" x="0" y="8" width="400" height="100" alpha="255">
                <Font family="orbitron_bold" size="82" weight="BOLD" color="{main}">
                    <Variant mode="AMBIENT" target="weight" value="NORMAL" />
                    <Variant mode="AMBIENT" target="color" value="{NIGHT}" />
                </Font>
            </TimeText>
            <!-- seconds digits retired: see the orbiting pixel in the rings PartDraw -->
        </DigitalClock>'''


tinted_clock = condition(
    [("night", f"{H} &lt; 6"), ("evening", f"{H} &gt;= 20")],
    [("night", clock(NIGHT, SILVER)), ("evening", clock(AMBER, ORANGE))],
    clock(IVORY, ORANGE),
)

# --- rings ----------------------------------------------------------------
RING = 456
rings = f'''

        <!-- ===== instrument tick ring (hidden in ambient) ===== -->
        <PartDraw x="0" y="0" width="480" height="480" name="ticks" alpha="255">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <Line startX="240.0" startY="2.0" endX="240.0" endY="14.0"><Stroke color="{ACCENT}" thickness="3" cap="BUTT" /></Line>
            <Line startX="264.9" startY="3.3" endX="264.3" endY="9.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="289.5" startY="7.2" endX="288.2" endY="13.1"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="313.5" startY="13.6" endX="311.7" endY="19.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="336.8" startY="22.6" endX="334.4" endY="28.1"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="359.0" startY="33.9" endX="356.0" endY="39.1"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="379.9" startY="47.5" endX="376.4" endY="52.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="399.3" startY="63.1" endX="395.2" endY="67.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="416.9" startY="80.7" endX="412.4" endY="84.8"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="432.5" startY="100.1" endX="427.7" endY="103.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="446.1" startY="121.0" endX="440.9" endY="124.0"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="457.4" startY="143.2" endX="451.9" endY="145.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="466.4" startY="166.5" endX="460.6" endY="168.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="472.8" startY="190.5" endX="466.9" endY="191.8"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="476.7" startY="215.1" endX="470.7" endY="215.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="478.0" startY="240.0" endX="466.0" endY="240.0"><Stroke color="{ACCENT}" thickness="3" cap="BUTT" /></Line>
            <Line startX="476.7" startY="264.9" endX="470.7" endY="264.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="472.8" startY="289.5" endX="466.9" endY="288.2"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="466.4" startY="313.5" endX="460.6" endY="311.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="457.4" startY="336.8" endX="451.9" endY="334.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="446.1" startY="359.0" endX="440.9" endY="356.0"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="432.5" startY="379.9" endX="427.7" endY="376.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="416.9" startY="399.3" endX="412.4" endY="395.2"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="399.3" startY="416.9" endX="395.2" endY="412.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="379.9" startY="432.5" endX="376.4" endY="427.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="359.0" startY="446.1" endX="356.0" endY="440.9"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="336.8" startY="457.4" endX="334.4" endY="451.9"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="313.5" startY="466.4" endX="311.7" endY="460.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="289.5" startY="472.8" endX="288.2" endY="466.9"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="264.9" startY="476.7" endX="264.3" endY="470.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="240.0" startY="478.0" endX="240.0" endY="466.0"><Stroke color="{ACCENT}" thickness="3" cap="BUTT" /></Line>
            <Line startX="215.1" startY="476.7" endX="215.7" endY="470.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="190.5" startY="472.8" endX="191.8" endY="466.9"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="166.5" startY="466.4" endX="168.3" endY="460.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="143.2" startY="457.4" endX="145.6" endY="451.9"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="121.0" startY="446.1" endX="124.0" endY="440.9"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="100.1" startY="432.5" endX="103.6" endY="427.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="80.7" startY="416.9" endX="84.8" endY="412.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="63.1" startY="399.3" endX="67.6" endY="395.2"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="47.5" startY="379.9" endX="52.3" endY="376.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="33.9" startY="359.0" endX="39.1" endY="356.0"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="22.6" startY="336.8" endX="28.1" endY="334.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="13.6" startY="313.5" endX="19.4" endY="311.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="7.2" startY="289.5" endX="13.1" endY="288.2"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="3.3" startY="264.9" endX="9.3" endY="264.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="2.0" startY="240.0" endX="14.0" endY="240.0"><Stroke color="{ACCENT}" thickness="3" cap="BUTT" /></Line>
            <Line startX="3.3" startY="215.1" endX="9.3" endY="215.7"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="7.2" startY="190.5" endX="13.1" endY="191.8"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="13.6" startY="166.5" endX="19.4" endY="168.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="22.6" startY="143.2" endX="28.1" endY="145.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="33.9" startY="121.0" endX="39.1" endY="124.0"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="47.5" startY="100.1" endX="52.3" endY="103.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="63.1" startY="80.7" endX="67.6" endY="84.8"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="80.7" startY="63.1" endX="84.8" endY="67.6"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="100.1" startY="47.5" endX="103.6" endY="52.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="121.0" startY="33.9" endX="124.0" endY="39.1"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="143.2" startY="22.6" endX="145.6" endY="28.1"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="166.5" startY="13.6" endX="168.3" endY="19.4"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="190.5" startY="7.2" endX="191.8" endY="13.1"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
            <Line startX="215.1" startY="3.3" endX="215.7" endY="9.3"><Stroke color="{GUNMETAL}" thickness="2" cap="BUTT" /></Line>
        </PartDraw>
        <!-- ===== ring glow: wide, low-opacity copies under the gauges ===== -->
        <PartDraw x="0" y="0" width="480" height="480" name="ring_glow" alpha="60">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <Arc centerX="240" centerY="240" width="{RING}" height="{RING}" startAngle="30" endAngle="30" direction="CLOCKWISE">
                <Transform target="endAngle" value="30 + clamp([STEP_COUNT], 0, {GOAL}) / {GOAL} * 120" />
                <Stroke color="{ACCENT}" thickness="26" cap="ROUND" />
            </Arc>
            <Arc centerX="240" centerY="240" width="{RING}" height="{RING}" startAngle="330" endAngle="330" direction="COUNTER_CLOCKWISE">
                <Transform target="endAngle" value="330 - [BATTERY_PERCENT] / 100 * 120" />
                <Stroke color="{SILVER}" thickness="26" cap="ROUND" />
            </Arc>
        </PartDraw>

        <!-- ===== bezel ring gauges (hidden in ambient) ===== -->
        <PartDraw x="0" y="0" width="480" height="480" name="rings" alpha="255">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <Arc centerX="240" centerY="240" width="{RING}" height="{RING}" startAngle="30" endAngle="150" direction="CLOCKWISE">
                <Stroke color="{GRAPHITE}" thickness="10" cap="ROUND" />
            </Arc>
            <Arc centerX="240" centerY="240" width="{RING}" height="{RING}" startAngle="330" endAngle="210" direction="COUNTER_CLOCKWISE">
                <Stroke color="{GRAPHITE}" thickness="10" cap="ROUND" />
            </Arc>
            <Arc centerX="240" centerY="240" width="{RING}" height="{RING}" startAngle="30" endAngle="30" direction="CLOCKWISE">
                <Transform target="endAngle" value="30 + clamp([STEP_COUNT], 0, {GOAL}) / {GOAL} * 120" />
                <Stroke color="{ACCENT}" thickness="10" cap="ROUND" />
            </Arc>
            <!-- seconds: a single accent pixel block running one lap per minute, just inside the rings -->
            <Arc centerX="240" centerY="240" width="{RING - 30}" height="{RING - 30}" startAngle="0" endAngle="5" direction="CLOCKWISE">
                <Transform target="startAngle" value="[SECOND] * 6" />
                <Transform target="endAngle" value="[SECOND] * 6 + 5" />
                <Stroke color="{ACCENT}" thickness="8" cap="BUTT" />
            </Arc>
            <!-- battery: silver, drains counter-clockwise from the top -->
            <Arc centerX="240" centerY="240" width="{RING}" height="{RING}" startAngle="330" endAngle="330" direction="COUNTER_CLOCKWISE">
                <Transform target="endAngle" value="330 - [BATTERY_PERCENT] / 100 * 120" />
                <Stroke color="{SILVER}" thickness="10" cap="ROUND" />
            </Arc>
        </PartDraw>'''

data_row = f'''
        <!-- ===== data row (hidden in ambient) ===== -->
        <Group x="0" y="312" width="480" height="40" name="data_row" alpha="255">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <PartImage x="0" y="-2" width="480" height="44"><Image resource="data_pills" /></PartImage>
            <PartImage x="72" y="8" width="24" height="24" tintColor="{ACCENT}"><Image resource="ic_steps" /><Launch target="{HEALTH_APP}" /></PartImage>
            <PartText x="100" y="0" width="100" height="40">
                <Launch target="{HEALTH_APP}" />
                <Text align="START"><Font family="orbitron_bold" size="24" weight="BOLD" color="{IVORY}">
                    <Template>%d<Parameter expression="[STEP_COUNT]" /></Template></Font></Text>
            </PartText>
            <PartAnimatedImage x="212" y="8" width="24" height="24" tintColor="{ACCENT}">
                <AnimatedImage resource="ic_heart_pulse" format="WEBP" />
                <AnimationController play="ON_VISIBLE" repeat="TRUE" resumePlayBack="TRUE" />
            </PartAnimatedImage>
            <Condition>
                <Expressions>
                    <Expression name="z2">[HEART_RATE] &gt;= 100 &amp;&amp; [HEART_RATE] &lt; 140</Expression>
                    <Expression name="z3">[HEART_RATE] &gt;= 140</Expression>
                </Expressions>
                <Compare expression="z3">
                    <PartText x="240" y="0" width="70" height="40">
                        <Launch target="HEALTH_HEART_RATE" />
                        <Text align="START"><Font family="orbitron_bold" size="24" weight="BOLD" color="{RED}">
                            <Template>%d<Parameter expression="[HEART_RATE]" /></Template></Font></Text>
                    </PartText>
                </Compare>
                <Compare expression="z2">
                    <PartText x="240" y="0" width="70" height="40">
                        <Launch target="HEALTH_HEART_RATE" />
                        <Text align="START"><Font family="orbitron_bold" size="24" weight="BOLD" color="{ACCENT}">
                            <Template>%d<Parameter expression="[HEART_RATE]" /></Template></Font></Text>
                    </PartText>
                </Compare>
                <Default>
                    <PartText x="240" y="0" width="70" height="40">
                        <Launch target="HEALTH_HEART_RATE" />
                        <Text align="START"><Font family="orbitron_bold" size="24" weight="BOLD" color="{IVORY}">
                            <Template>%d<Parameter expression="[HEART_RATE]" /></Template></Font></Text>
                    </PartText>
                </Default>
            </Condition>
            <PartImage x="322" y="8" width="24" height="24" tintColor="{ACCENT}"><Image resource="ic_batt" /><Launch target="BATTERY_STATUS" /></PartImage>
            <PartText x="350" y="0" width="90" height="40">
                <Launch target="BATTERY_STATUS" />
                <Text align="START"><Font family="orbitron_bold" size="24" weight="BOLD" color="{IVORY}">
                    <Template>%d%%<Parameter expression="[BATTERY_PERCENT]" /></Template></Font></Text>
            </PartText>
        </Group>'''

HF = "([HOUR_0_23] + [MINUTE] / 60)"          # fractional hour
MU = f"([HOUR_0_23] >= 18 ? {HF} - 18 : {HF} + 6)"  # hours since moonrise (18:00)

xml = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by tools/gen_watchface.py - edit that file, not this one. -->
<WatchFace width="480" height="480" clipShape="CIRCLE">
    <Metadata key="CLOCK_TYPE" value="DIGITAL" />
    <Metadata key="PREVIEW_TIME" value="10:08:32" />

    <!-- long-press the face > Customize: accent colour. Clawd stays orange. -->
    <UserConfigurations>
        <ListConfiguration id="show" displayName="show_name" defaultValue="0">
            <ListOption id="0"  displayName="show_live" />
            <ListOption id="1"  displayName="show_rain" />
            <ListOption id="2"  displayName="show_snow" />
            <ListOption id="3"  displayName="show_hot" />
            <ListOption id="4"  displayName="show_mail" />
            <ListOption id="5"  displayName="show_goal" />
            <ListOption id="6"  displayName="show_cardio" />
            <ListOption id="7"  displayName="show_lowbatt" />
            <ListOption id="8"  displayName="show_charging" />
            <ListOption id="9"  displayName="show_bday" />
            <ListOption id="10" displayName="show_hallo" />
            <ListOption id="11" displayName="show_xmas" />
            <ListOption id="12" displayName="show_ny" />
            <ListOption id="13" displayName="show_fri" />
            <ListOption id="14" displayName="show_grill" />
            <ListOption id="15" displayName="show_hammock" />
        </ListConfiguration>
        <ColorConfiguration id="theme" displayName="theme_name" defaultValue="0">
            <ColorOption id="0" displayName="theme_claude"  colors="#FFD97757 #FFC96442" />
            <ColorOption id="1" displayName="theme_redline" colors="#FFD71920 #FFFF3B3B" />
            <ColorOption id="2" displayName="theme_usaf"    colors="#FF4F7BC5 #FF0033A0" />
        </ColorConfiguration>
    </UserConfigurations>

{BITMAPFONTS}
    <Scene backgroundColor="{BG}">

        <!-- ===== Clawd's World: sky by daypart (hidden in ambient) ===== -->
        <Group x="0" y="0" width="480" height="480" name="world" alpha="255">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <Condition>
                <Expressions>
                    <Expression name="dawn">[HOUR_0_23] &gt;= 5 &amp;&amp; [HOUR_0_23] &lt; 8</Expression>
                    <Expression name="day">[HOUR_0_23] &gt;= 8 &amp;&amp; [HOUR_0_23] &lt; 17</Expression>
                    <Expression name="dusk">[HOUR_0_23] &gt;= 17 &amp;&amp; [HOUR_0_23] &lt; 21</Expression>
                </Expressions>
                <Compare expression="dawn"><PartImage x="0" y="0" width="480" height="480"><Image resource="sky_dawn" /></PartImage></Compare>
                <Compare expression="day"><PartImage x="0" y="0" width="480" height="480"><Image resource="sky_day" /></PartImage></Compare>
                <Compare expression="dusk"><PartImage x="0" y="0" width="480" height="480"><Image resource="sky_dusk" /></PartImage></Compare>
                <Default><PartImage x="0" y="0" width="480" height="480"><Image resource="sky_night" /></PartImage></Default>
            </Condition>

            <!-- sun: rises left at 06:00, peaks at noon, sets right at 18:00 -->
            <Condition>
                <Expressions><Expression name="sunup">[HOUR_0_23] &gt;= 6 &amp;&amp; [HOUR_0_23] &lt; 18</Expression></Expressions>
                <Compare expression="sunup">
                    <PartImage x="0" y="0" width="32" height="32">
                        <Transform target="x" value="240 - 190 * cos(rad(({HF} - 6) * 15)) - 16" />
                        <Transform target="y" value="170 - 110 * sin(rad(({HF} - 6) * 15)) - 16" />
                        <Image resource="sun" />
                    </PartImage>
                </Compare>
                <Default>
                    <!-- moon: same arc from 18:00 to 06:00, real phase -->
                    <Condition>
                        <Expressions>
                            <Expression name="m1">[MOON_PHASE_TYPE] == 1</Expression>
                            <Expression name="m2">[MOON_PHASE_TYPE] == 2</Expression>
                            <Expression name="m3">[MOON_PHASE_TYPE] == 3</Expression>
                            <Expression name="m4">[MOON_PHASE_TYPE] == 4</Expression>
                            <Expression name="m5">[MOON_PHASE_TYPE] == 5</Expression>
                            <Expression name="m6">[MOON_PHASE_TYPE] == 6</Expression>
                            <Expression name="m7">[MOON_PHASE_TYPE] == 7</Expression>
                        </Expressions>
                <Compare expression="m1">
                    <PartImage x="0" y="0" width="28" height="28">
                        <Transform target="x" value="240 - 190 * cos(rad({MU} * 15)) - 14" />
                        <Transform target="y" value="170 - 110 * sin(rad({MU} * 15)) - 14" />
                        <Image resource="moon_1" />
                    </PartImage>
                </Compare>
                <Compare expression="m2">
                    <PartImage x="0" y="0" width="28" height="28">
                        <Transform target="x" value="240 - 190 * cos(rad({MU} * 15)) - 14" />
                        <Transform target="y" value="170 - 110 * sin(rad({MU} * 15)) - 14" />
                        <Image resource="moon_2" />
                    </PartImage>
                </Compare>
                <Compare expression="m3">
                    <PartImage x="0" y="0" width="28" height="28">
                        <Transform target="x" value="240 - 190 * cos(rad({MU} * 15)) - 14" />
                        <Transform target="y" value="170 - 110 * sin(rad({MU} * 15)) - 14" />
                        <Image resource="moon_3" />
                    </PartImage>
                </Compare>
                <Compare expression="m4">
                    <PartImage x="0" y="0" width="28" height="28">
                        <Transform target="x" value="240 - 190 * cos(rad({MU} * 15)) - 14" />
                        <Transform target="y" value="170 - 110 * sin(rad({MU} * 15)) - 14" />
                        <Image resource="moon_4" />
                    </PartImage>
                </Compare>
                <Compare expression="m5">
                    <PartImage x="0" y="0" width="28" height="28">
                        <Transform target="x" value="240 - 190 * cos(rad({MU} * 15)) - 14" />
                        <Transform target="y" value="170 - 110 * sin(rad({MU} * 15)) - 14" />
                        <Image resource="moon_5" />
                    </PartImage>
                </Compare>
                <Compare expression="m6">
                    <PartImage x="0" y="0" width="28" height="28">
                        <Transform target="x" value="240 - 190 * cos(rad({MU} * 15)) - 14" />
                        <Transform target="y" value="170 - 110 * sin(rad({MU} * 15)) - 14" />
                        <Image resource="moon_6" />
                    </PartImage>
                </Compare>
                <Compare expression="m7">
                    <PartImage x="0" y="0" width="28" height="28">
                        <Transform target="x" value="240 - 190 * cos(rad({MU} * 15)) - 14" />
                        <Transform target="y" value="170 - 110 * sin(rad({MU} * 15)) - 14" />
                        <Image resource="moon_7" />
                    </PartImage>
                </Compare>
                        <Default>
                            <PartImage x="0" y="0" width="28" height="28">
                                <Transform target="x" value="240 - 190 * cos(rad(([HOUR_0_23] >= 18 ? ([HOUR_0_23] + [MINUTE] / 60) - 18 : ([HOUR_0_23] + [MINUTE] / 60) + 6) * 15)) - 14" />
                                <Transform target="y" value="170 - 110 * sin(rad(([HOUR_0_23] >= 18 ? ([HOUR_0_23] + [MINUTE] / 60) - 18 : ([HOUR_0_23] + [MINUTE] / 60) + 6) * 15)) - 14" />
                                <Image resource="moon_0" />
                            </PartImage>
                        </Default>
                    </Condition>
                </Default>
            </Condition>

            <!-- stars overnight, rain / snow from the weather feed (behind the clock) -->
            <Condition>
                <Expressions>
                    <Expression name="fxrain">[WEATHER.IS_AVAILABLE] &amp;&amp; ([WEATHER.CONDITION] == 4 || [WEATHER.CONDITION] == 6 || [WEATHER.CONDITION] == 9 || [WEATHER.CONDITION] == 10 || [WEATHER.CONDITION] == 12)</Expression>
                    <Expression name="fxsnow">[WEATHER.IS_AVAILABLE] &amp;&amp; ([WEATHER.CONDITION] == 5 || [WEATHER.CONDITION] == 7 || [WEATHER.CONDITION] == 11)</Expression>
                    <Expression name="fxnight">[HOUR_0_23] &lt; 5 || [HOUR_0_23] &gt;= 21</Expression>
                </Expressions>
                <Compare expression="fxrain">
                    <PartAnimatedImage x="0" y="0" width="480" height="480">
                        <AnimatedImage resource="fx_rain" format="WEBP" />
                        <AnimationController play="ON_VISIBLE" repeat="TRUE" resumePlayBack="TRUE" />
                    </PartAnimatedImage>
                </Compare>
                <Compare expression="fxsnow">
                    <PartAnimatedImage x="0" y="0" width="480" height="480">
                        <AnimatedImage resource="fx_snow" format="WEBP" />
                        <AnimationController play="ON_VISIBLE" repeat="TRUE" resumePlayBack="TRUE" />
                    </PartAnimatedImage>
                </Compare>
                <Compare expression="fxnight">
                    <PartAnimatedImage x="0" y="0" width="480" height="480">
                        <AnimatedImage resource="fx_stars" format="WEBP" />
                        <AnimationController play="ON_VISIBLE" repeat="TRUE" resumePlayBack="TRUE" />
                    </PartAnimatedImage>
                </Compare>
                <Default>
                    <PartImage x="0" y="0" width="1" height="1" alpha="0"><Image resource="moon_0" /></PartImage>
                </Default>
            </Condition>

            <!-- skyline on the horizon, just above Clawd's window -->
            <PartImage x="0" y="130" width="480" height="48"><Image resource="skyline" /></PartImage>
        </Group>
        <!-- vignette + faint blueprint grid (now an alpha overlay on the sky) -->
        <PartImage x="0" y="0" width="480" height="480" alpha="255">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <Image resource="bg_vignette" />
        </PartImage>
{rings}

        <!-- ===== date ===== -->
        <PartText x="0" y="28" width="480" height="32">
            <Text align="CENTER"><BitmapFont family="pixel" size="28" color="{ACCENT}">
                <Template>%s %s %d<Parameter expression="[DAY_OF_WEEK_S]" /><Parameter expression="[MONTH_S]" /><Parameter expression="[DAY]" /></Template>
            </BitmapFont></Text>
        </PartText>

        <!-- ===== time, tinted by hour ===== -->
        <Group x="0" y="0" width="480" height="180" name="clock">{tinted_clock}
        </Group>

        <!-- ===== temperature (format v2 weather; hidden if unavailable / ambient) ===== -->
        <Group x="372" y="118" width="90" height="30" name="temp" alpha="255">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <Condition>
                <Expressions><Expression name="wx">[WEATHER.IS_AVAILABLE]</Expression></Expressions>
                <Compare expression="wx">
                    <PartText x="0" y="0" width="90" height="30">
                        <Launch target="{WEATHER_APP}" />
                        <Text align="CENTER"><Font family="orbitron_bold" size="18" weight="BOLD" color="{SILVER}">
                            <Template>%d°<Parameter expression="[WEATHER.TEMPERATURE]" /></Template></Font></Text>
                    </PartText>
                </Compare>
                <Default>
                    <PartText x="0" y="0" width="90" height="30" alpha="0"><Text align="CENTER"><Font family="SYNC_TO_DEVICE" size="18" color="{SILVER}">-</Font></Text></PartText>
                </Default>
            </Condition>
        </Group>

        <!-- ===== Clawd, live (hidden in ambient); Showcase list at scene level ===== -->{clawd}

        <!-- ===== Clawd, asleep (ambient only) ===== -->
        <PartImage x="141" y="176" width="{SW}" height="{SH}" alpha="0" name="clawd_ambient">
            <Variant mode="AMBIENT" target="alpha" value="255" />
            <Image resource="clawd_ambient" />
        </PartImage>
{data_row}

        <!-- ===== Redline Tech Solutions: silver RL mark at six o'clock ===== -->
        <PartImage x="216" y="372" width="48" height="36" alpha="255">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <Image resource="redline_mark_lg" />
        </PartImage>
    </Scene>
</WatchFace>
'''

OUT.write_text(xml, encoding="utf-8")
print("wrote", OUT, len(xml), "chars,", xml.count("<Compare"), "branches")
