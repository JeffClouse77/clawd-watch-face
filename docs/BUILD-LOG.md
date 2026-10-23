# Clawd Watch Face Build Story

*Built 2026-10-23 by Jeffery Clouse with Claude Code.*

In one day, Claude Code and I took a Galaxy Watch7 from a stock Samsung face to a hand-built Watch Face Format face starring Clawd, the Claude Code mascot: a pixel character who keeps a daily schedule, reacts to my heart rate, steps, battery, weather and notifications, and lives under a sky with a sun that actually moves. No Android Studio, no Watch Face Studio: Python scripts draw every asset and generate the XML, a PowerShell script builds and signs the package, and ADB pushes it to the wrist over Wi-Fi.

## Starting point

The watch began the day on Samsung's Spatial Number face: a dark green dashboard with steps, heart rate, compass and temperature. The brief was simple and specific: an AI-designed face featuring the Claude Code character, showing time, date and steps, with the character moving around through the day doing activities, in the Claude color scheme, with Redline Tech Solutions branding and seconds. The only hardware was a Galaxy Watch7, a phone acting as a Wi-Fi hotspot, and a Windows 11 PC.

## Getting the PC talking to the watch

A Galaxy Watch cannot be customized over the network directly; the only developer door is Android Debug Bridge (ADB), and on Wear OS 3 and later that means Wireless debugging over Wi-Fi. Getting there took several false starts, all now documented so nobody repeats them.

1. Bluetooth-pairing the watch to the PC does nothing useful: it shows up only as an audio device.
2. The watch and PC must share one Wi-Fi network. The phone's hotspot worked once the watch's Wi-Fi was set to Always on, because the watch silently drops Wi-Fi whenever it is Bluetooth-connected to the phone.
3. Developer options come from tapping the software version seven times. The older Debug over Wi-Fi switch never opened a port; the newer Wireless debugging mode did, on a random port, after a one-time pairing with a six-digit code.
4. From the PC: a batched TCP sweep of ports 30000 to 49999 finds the watch's debug port in a couple of seconds, then `adb pair` once and `adb connect` after that. The port changes every time the watch reboots or the setting is toggled.

The toolchain was installed with winget as needed: Android platform tools, a Microsoft OpenJDK 17, the Android SDK command-line tools with build-tools 35 and platform 34, and later the GitHub CLI. Nothing needed Android Studio.

## Drawing Clawd

Every sprite is grid-based pixel art drawn by a Python script with Pillow: a 22 by 14 cell canvas, one letter per color, scaled 12 pixels per cell to 264 by 168. Clawd's body is a 14 by 9 block in Claude orange with a darker crail shade, two-by-two ink eyes, and four little feet. Props and expressions are stamped on top: a coffee mug with curling steam, a laptop with scrolling green code, a pizza slice that loses bites, a barbell, a book that turns pages, a controller, a nightcap and floating Zs.

Moods and holidays came next: sweating with flushed cheeks, confetti and happy eyes, a yawn under a low-battery icon, a Friday drink with an umbrella, a pumpkin, a Santa hat, a party hat, and a birthday cake with a flickering candle.

Tap reactions are drawn on an opaque background so they can play over the idle loop: a wave with a heart, offering the pizza, and a ship-it fist pump with terminal sparks.

Weather and weekend states followed: umbrella, scarf, sunglasses, an envelope for mail, guitar, grill, hammock and football.

## Round 1: the first face, and why the GIFs never moved

The face is a Watch Face Format package: an APK with no code, only XML and images. The first version had the time, a "FRI 23" date, seconds, steps, heart rate, battery, the Redline wordmark, and Clawd in a band across the middle, changing activity and position by hour of day using eight time-of-day conditions. It built, signed with a local debug key, installed over ADB, and rendered correctly on the first try.

Except Clawd did not move. Eight screenshots over three seconds were pixel-identical. The watch's log showed the runtime loading the animated GIFs without complaint, and that was the clue: Samsung's Watch Face Format runtime decodes a GIF, draws its first frame, and never advances it. Re-exporting every sprite as animated WebP fixed it immediately, and every animation since has been WebP. That one lesson is at the top of the README.

## Round 2: moods, taps, rings and surprises

The XML grew too large to write by hand, so from here on a generator script holds the schedule and priority tables and writes the file. This round added:

- **Moods from health data**, which outrank everything else: heart rate over 120 makes Clawd sweat with a "cardio!" caption, reaching the step goal gets a jump in confetti, and battery under 15 percent gets a yawn under a red icon. The battery mood was verified live by faking the watch's battery level to 10 percent over ADB, then resetting it.
- **Tap reactions** that play over the idle loop and vanish when done: the pizza offer at lunch, the fist pump while coding, the wave everywhere else. Verified with a simulated tap.
- **Ring gauges** hugging the bezel: steps fill the right side in orange, battery drains the left side in silver, and the heart icon pulses once a second.
- **Calendar surprises**: Friday after 5pm, Halloween, Christmas, New Year's Day, and an optional birthday set in the generator.

## Round 3: scenes, blinking, tinted clock, ambient, Orbitron

Each daypart got a low-contrast pixel backdrop so Clawd still pops: a starry sky, a sunrise over a counter, a second monitor and desk, a lunch table, a skyline with trees, a squat rack, a reading lamp, and a glowing TV.

Every idle loop now cycles its frames three times and then closes Clawd's eyes for a tenth of a second. The blink is applied generically by finding two-by-two eye blocks on body color, so every state gets it for free.

The clock tints by hour: ivory by day, amber after 8pm, silver overnight. A real ambient mode fades out the rings and data and shows a sleeping Clawd. The numerals moved to Orbitron Bold, instanced from Google's variable font with fontTools and bundled under its open license, after a first build where it ran wide enough to clip the round bezel.

## Round 4: weather, mail, weekends, tap-to-launch

The package moved to Watch Face Format version 2 for weather. Rain, thunder and sleet put Clawd under an umbrella, snow gives him a scarf, and a daytime 90 degrees puts him in sunglasses. A temperature readout appeared under the seconds. At first the weather feed reported nothing, which turned out to be timing: the runtime fetches weather for a face about a minute after install, and a diagnostic line soon read "available, no error, condition 8, 79 degrees".

Unread notifications put an envelope in Clawd's hand with the count in red above it, verified by posting a test notification from the PC and watching the count go from 1 to 2. Saturdays and Sundays got their own schedule: sleeping in, a slow coffee, guitar, grilling, the game, a hammock, reading. And the data row became a launcher: tapping steps opens Samsung Health, confirmed by the watch reporting the app in the foreground; the heart starts a measurement, the battery opens battery status, and the temperature opens the weather app.

## Round 5: theme picker, hourly flip, orbiting seconds, moon, step goal, wallpapers

- **Accent theme** in the watch's Customize menu: Claude orange, Redline red, or Air Force blue recolors the date, rings, icons, seconds and mail count. Clawd stays orange on principle.
- **Hourly flip**: at the top of every hour he squats, jumps, flips upside down and lands.
- **Orbiting seconds**: the two-digit seconds were retired for a single accent pixel that runs one lap per minute just inside the rings, confirmed moving by diffing two screenshots.
- **Real moon phase** on the night scenes from the watch's own moon data, eight phases drawn by script.
- **Step goal** read from Samsung Health instead of a hard-coded 10,000, with a fallback.
- **Phone wallpapers** in the same palette: Clawd coding with the RL mark for the home screen, Clawd asleep under the stars for the lock screen.

## Round 6: Showcase, charging, heart zones, tilt, and the Customize mystery

A **Showcase** setting joined the Customize menu with 16 entries: Live, plus every mood, weather state and holiday, so any of them can be demoed on demand. Charging got its own state with a cable and blinking bolt. The heart-rate number colors by zone: ivory at rest, accent from 100, red from 140. And the scene slides a few pixels with wrist tilt using the accelerometer.

Then a puzzle: Showcase choices previewed in the editor but reset on exit. Two real causes surfaced. First, the face had to be declared editable in its info file before One UI would even show a Customize button. Second, and the subtle one: the ADB broadcast used to activate the face from the PC creates a separate favorite instance of it, so the editor was saving to the carousel's copy while the screen showed the broadcast's copy. Installing updates with plain `adb install -r` and never using that broadcast again fixed it, and the proof arrived by accident when the editor flipped Clawd to Cardio at a resting heart rate.

## Round 7: the design pass

With the features in, the face was still visually flat, so two rounds of pure design followed.

A **5 by 7 pixel typeface** drawn by script, one PNG per glyph with lowercase as small caps, replaced the system font for the date and captions, so the whole face reads as one object. A **vignette background** with a faint blueprint grid gave it a surface. Clawd's scene moved inside a **rounded window panel**, and he got a one-pixel **outline and a drop shadow** so he sits on the surface instead of floating.

Round two of design: a soft **glow** under the ring gauges, rounded **pills** behind the data row, **living scenes** where the stars twinkle, the TV flickers and the lamp breathes, and an **ambient rework** to an outline-only Clawd with everything else off for the OLED.

## Round 8: Clawd's World

The final and biggest visual change turned the face into a place. The sky changes with the day: near-black night, warm dawn from 5am, deep blue day, a burnt dusk from 5pm. A pixel **sun rises on the left at 6am, peaks behind the clock at noon and sets on the right at 6pm**, driven by sine and cosine expressions in the layout, which the Samsung runtime turned out to support. From 6pm a real-phase moon takes the same arc. A pixel **skyline** with lit windows sits on the horizon above Clawd's window. Rain, snow and a twinkling starfield now fall across the whole face behind the clock. A 60-tick instrument ring circles the bezel, the clock digits float on a drop shadow, and the date reads "FRI OCT 23" in the pixel font.

One last fix in this round: the pixel font runs about 40 percent wider than the system font, so "SHIPPING" clipped to "IPPING" until the caption boxes were sized to the panel instead of the text.

## Publishing

The project went public in this repository: the manifest, all 143 drawables, the six Python generators, the build script, the Orbitron font with its license note, both wallpapers, and a README with the feature list, the build pipeline, the lessons below and a session log.

An export script produced the copy that went up, and it is deliberately strict. It drops the signing keystore, every built APK, and live screenshots that carry health data. It resets the birthday to a placeholder, replaces the watch's IP address and the keystore password with generic values, and then scans every text file for personal names, the hotspot name or the home subnet before it will finish. Commits are authored with a GitHub no-reply address. The GitHub CLI was installed and authorized through the device-code flow during the session.

## What we learned the hard way

| Lesson | Detail |
| --- | --- |
| Animated GIFs do not animate | Samsung's runtime draws frame one and stops. Use animated WebP with `repeat="TRUE"`. |
| Weather arrives late | The availability flag is false for about a minute after install, even with the watch's own weather app full of data. |
| Never activate updates with the debug broadcast | It creates a second favorite instance; Customize edits then save to the wrong copy. Use `adb install -r`. |
| Editable must be true | Otherwise One UI shows no Customize button at all. |
| Showcase lists belong at scene level | A ListConfiguration holding whole subtrees must be a direct child of Scene, as in Google's Flavors sample. |
| Charging is invisible | Samsung's charger overlay covers every face; the charging state shows only via Showcase. |
| The always-on clock is Samsung's | After the first dimming stage the watch offloads to its own system clock; a face's ambient layout appears only briefly. |
| Screenshots over ADB | `screencap -p /sdcard/x.png` then pull; PowerShell's `exec-out` corrupts PNGs; Git Bash needs `MSYS_NO_PATHCONV=1`. |
| Wireless debugging wanders | Random port, drops when the watch dozes; a batched port sweep in 1,500-port chunks finds it again. Wi-Fi must be Always on. |
| The face never needs Wi-Fi | Health, weather and notifications arrive over Bluetooth; Wi-Fi only matters for pushing builds. |
| Expressions do trigonometry | `sin`, `cos`, `rad` and `clamp` work in Transform values; that is how the sun and moon travel. |
| Pixel fonts are wide | Size caption boxes to the panel, not to the text you first tried. |
| Do not drive the face carousel over ADB | A second long-press enters remove mode with a delete button on every face. |

Fourteen builds, eight feature rounds, two design rounds, one public repository, and a watch face that knows what day it is.
