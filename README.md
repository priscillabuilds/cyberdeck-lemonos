# LemonOS quick start

My custom OS for my cyberdeck, running on a Raspberry Pi 4B 2GB with a Waveshare 3.5" DSI display.

## Develop on macOS

The Mac version opens a normal 640x480 window with a visible mouse pointer.
Press Escape or close the window to quit.

From this project folder, run:

```bash
.venv/bin/python main.py
```

For a fresh checkout, create the local environment first:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Controls

- Home opens Weather, Reminder, or Paint.
- Reminder shows one affirmation; Another always chooses a different one.
- Paint has Home and Clear at the top, a large canvas, and brush/color controls below.
- Selected brushes have an extra dark outline. Selected colors have an outline and check mark.
- Drag on the canvas to draw continuous strokes. A tap makes a dot.
- Buttons activate on release inside the same button and show a pressed state.
- Touchscreen input uses SDL's mouse events, matching mouse navigation.

## On the Raspberry Pi

1. Install Pygame:

```bash
sudo apt update
sudo apt install -y python3-pygame
```

2. Put this folder at:

```text
/home/priscilla/lemonos_quickstart/
```

3. First run:

```bash
cd ~/lemonos_quickstart
python3 main.py
```

The Linux/Pi version runs fullscreen at 640x480 and includes:
- Home
- live San Francisco weather
- Reminder
- Paint
- touch/mouse navigation

## Optional: use your real PNG art

Put these files in `assets/`:

```text
lemon.png
cloud1.png
cloud2.png
star.png
weather-button.png
reminder-button.png
paint-button.png
button-blank.png
PixelOperatorMono.ttf
```

The app runs even if they are missing.

## If you are launching over SSH

If the Pi desktop is already visible on the Waveshare:

```bash
cd ~/lemonos_quickstart
export XDG_RUNTIME_DIR=/run/user/$(id -u)
ls "$XDG_RUNTIME_DIR"/wayland-*
```

If you see `wayland-0`:

```bash
export WAYLAND_DISPLAY=wayland-0
SDL_VIDEODRIVER=wayland python3 main.py
```

If you see `wayland-1`, use that instead.

If it does not appear, run `python3 main.py` from a terminal directly on the Pi for the first test.

## Weather

San Francisco is hard-coded to 37.7749, -122.4194.
Weather is fetched from Open-Meteo at startup, when Weather opens, and every 10 minutes.

## Little LemonOS extras

- Tap the wandering lemon on Home for a happy hop.
- After one minute without mouse/touch/key activity, he stops wandering and shows floating zzz letters. Interaction wakes him up.
- Stars gently pulse in size.
- Home and Weather show a weather emoji matching Open-Meteo's current condition. Clear nights show a moon.
- Weather icons are bundled locally and require no emoji font. Artwork credit and license are in `assets/weather/CREDITS.md` and `LICENSE-GRAPHICS`.
- In Paint, tap **Tools > Stamp**, then tap the canvas to place a lemon. Small, Big, or a palette color returns to drawing.
- **Tools > Save** saves the canvas as a new PNG in the project's `drawings/` folder. Every save gets its own filename.
- **Tools > Gallery** browses saved PNGs using Prev/Next. Paint returns to your current canvas; viewing saved art does not replace it.
- Save artwork before quitting if you want to keep it. Clear affects only the current canvas, not saved drawings.

## Desktop access and Wi-Fi status

Home has a small monitor icon for Desktop, with a 48x48 touch target. Tap it, then Desktop on the confirmation screen, to close LemonOS and reach the regular desktop without powering off. Cancel returns Home. Save any drawing first. This does not disable startup-on-boot.

Both header icons are black and vertically aligned. The Wi-Fi icon is crossed out when disconnected; a hollow dot indicates unknown status or Mac development mode. On the Pi, Home checks NetworkManager's Wi-Fi connection state every 10 seconds. Internal status values:
- WI-FI OK: associated/connected to Wi-Fi; this does not guarantee internet access.
- NO WI-FI: a managed Wi-Fi interface is disconnected, unavailable, or connecting.
- WI-FI --: status is unavailable (for example, nmcli is missing).
- DEV MODE: running on macOS; no Pi Wi-Fi check is attempted.

The checks run in the background and never change network settings. Weather errors remain separate from Wi-Fi connection status.
The power-off button and all operating-system shutdown commands have been removed.
