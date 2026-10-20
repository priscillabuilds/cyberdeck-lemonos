import json
import math
import os
import random
import sys
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
import pygame

WIDTH, HEIGHT = 640, 480
FPS = 30

CREAM=(255,248,199); GOLD=(255,230,162); LAV=(222,205,252); BLUE=(149,184,242)
AQUA=(216,247,248); PAPER=(248,248,255); INK=(59,53,111); PINK=(247,199,223)

ASSET_DIR = Path(__file__).parent / "assets"
ASSETS = {
    "lemon": ASSET_DIR/"lemon.png",
    "cloud1": ASSET_DIR/"cloud1.png",
    "cloud2": ASSET_DIR/"cloud2.png",
    "star": ASSET_DIR/"star.png",
    "weather_button": ASSET_DIR/"weather-button.png",
    "reminder_button": ASSET_DIR/"reminder-button.png",
    "paint_button": ASSET_DIR/"paint-button.png",
    "blank_button": ASSET_DIR/"button-blank.png",
}
WEATHER_ICONS = ("sun", "partly-cloudy", "cloud", "rain", "storm", "fog", "snow", "moon")
for name in WEATHER_ICONS:
    ASSETS["weather_" + name] = ASSET_DIR / "weather" / (name + ".png")

SF_LAT, SF_LON = 37.7749, -122.4194

AFFIRMATIONS = [
    "small steps still count",
    "make something silly today",
    "you are allowed to take your time",
    "curiosity counts as progress",
    "something lovely can happen today",
    "do the tiny version first",
    "you receive all the good that life has to offer",
    "you have unique thoughts to offer the world",
    "you are becoming more sure of yourself with each passing day",
    "you overcome your personal challenges",
    "you believe in yourself",
    "you deserve to have fun and play",
]

WEATHER_TEXT = {
    0:"CLEAR",1:"MOSTLY CLEAR",2:"PARTLY CLOUDY",3:"CLOUDY",45:"FOGGY",48:"FOGGY",
    51:"LIGHT DRIZZLE",53:"DRIZZLE",55:"HEAVY DRIZZLE",61:"LIGHT RAIN",63:"RAIN",
    65:"HEAVY RAIN",71:"LIGHT SNOW",73:"SNOW",75:"HEAVY SNOW",80:"RAIN SHOWERS",
    81:"RAIN SHOWERS",82:"HEAVY SHOWERS",95:"THUNDERSTORM",96:"THUNDERSTORM",99:"THUNDERSTORM"
}

WEATHER_TEXT.update({56: "FREEZING DRIZZLE", 57: "FREEZING DRIZZLE",
                     66: "FREEZING RAIN", 67: "FREEZING RAIN", 77: "SNOW GRAINS",
                     85: "SNOW SHOWERS", 86: "SNOW SHOWERS"})

pygame.init()
DEVELOPMENT = sys.platform == "darwin"
screen = pygame.display.set_mode((WIDTH, HEIGHT), 0 if DEVELOPMENT else pygame.FULLSCREEN)
pygame.mouse.set_visible(DEVELOPMENT)
pygame.display.set_caption("LemonOS")
clock = pygame.time.Clock()

pixel_font = ASSET_DIR / "PixelOperatorMono.ttf"
if pixel_font.exists():
    FONT = pygame.font.Font(str(pixel_font), 32)
    SMALL = pygame.font.Font(str(pixel_font), 24)
    BIG = pygame.font.Font(str(pixel_font), 64)
else:
    FONT = pygame.font.SysFont("monospace", 22, bold=True)
    SMALL = pygame.font.SysFont("monospace", 16, bold=True)
    BIG = pygame.font.SysFont("monospace", 52, bold=True)

def load_img(path):
    try: return pygame.image.load(str(path)).convert_alpha()
    except (pygame.error, FileNotFoundError): return None

images = {key: load_img(path) for key, path in ASSETS.items()}
# Ignore transparent export margins when fitting button art; keep the PNG intact.
for key, button_image in images.items():
    if "button" in key and button_image is not None:
        bounds = button_image.get_bounding_rect()
        if bounds.width and bounds.height:
            images[key] = button_image.subsurface(bounds).copy()

def draw_text(text,x,y,font=FONT,color=INK,center=False):
    surf=font.render(text,False,color); r=surf.get_rect()
    r.center=(x,y) if center else r.center
    if not center: r.topleft=(x,y)
    screen.blit(surf,r)

def blit_fitted(image, rect):
    # Nearest-neighbor scaling keeps pixels crisp and preserves proportions.
    rect = pygame.Rect(rect)
    scale = min(rect.width / image.get_width(), rect.height / image.get_height())
    size = (max(1, round(image.get_width() * scale)),
            max(1, round(image.get_height() * scale)))
    fitted = pygame.transform.scale(image, size)
    fitted_rect = fitted.get_rect(center=rect.center)
    screen.blit(fitted, fitted_rect)
    return fitted_rect


def pixel_button(rect, label, fill=BLUE, image=None, font=SMALL, selected=False):
    rect = pygame.Rect(rect)
    pressed = pressed_button == rect and pygame.time.get_ticks() < pressed_until
    image = image if image is not None else images.get("blank_button")
    if image is not None:
        area = rect.inflate(-6, -6)
        if pressed:
            area.move_ip(2, 2)
        face = blit_fitted(image, area)
        # Center the label on the raised face, above the artwork's lower shadow.
        label_y = face.centery - round(face.height * 0.10)
    else:
        face = rect.inflate(-5, -5).move(-2, -2)
        pygame.draw.rect(screen, INK, face.move(4, 4))
        if pressed:
            face.move_ip(3, 3)
        pygame.draw.rect(screen, fill, face)
        pygame.draw.rect(screen, INK, face, 3)
        label_y = face.centery
    if selected:
        pygame.draw.rect(screen, INK, face.inflate(4, 4), 2)
    draw_text(label, face.centerx, label_y, font, INK, True)


def cloud_blob(x,y,w,h):
    pygame.draw.ellipse(screen,AQUA,(x,y+h//4,w,h//2))
    pygame.draw.ellipse(screen,AQUA,(x+w//8,y,h,h))
    pygame.draw.ellipse(screen,AQUA,(x+w//2-h//3,y+h//10,h,h))
    pygame.draw.ellipse(screen,AQUA,(x+w-h,y+h//5,h,h))

def draw_cloud(x,y,w,h,key="cloud1"):
    img=images.get(key)
    if img: blit_fitted(img, (x,y,w,h))
    else: cloud_blob(x,y,w,h)

def draw_star(x,y,size=24):
    # Each star gently grows in turn; no rapid flashing.
    phase = (pygame.time.get_ticks() / 1000 + x * 0.03) % 7
    sparkle = math.sin(math.pi * phase / 1.6) if phase < 1.6 else 0
    extra = round(6 * sparkle)
    x -= extra // 2
    y -= extra // 2
    size += extra
    img=images.get("star")
    if img: blit_fitted(img, (x,y,size,size))
    else: draw_text("*",x,y,FONT,GOLD)

def draw_lemon(x,y,size=92):
    img=images.get("lemon")
    if img: blit_fitted(img, (x,y,size,size))
    else:
        pygame.draw.ellipse(screen,GOLD,(x,y+10,size,size-20))
        pygame.draw.circle(screen,INK,(x+size//3,y+size//2),3); pygame.draw.circle(screen,INK,(x+2*size//3,y+size//2),3)

weather={"loading":True,"error":None,"temp":"--","high":"--","low":"--","code":2,"is_day":1}
def fetch_weather():
    weather["loading"]=True; weather["error"]=None
    params={
        "latitude":SF_LAT,"longitude":SF_LON,
        "current":"temperature_2m,weather_code,is_day",
        "daily":"temperature_2m_max,temperature_2m_min",
        "temperature_unit":"fahrenheit",
        "timezone":"America/Los_Angeles",
        "forecast_days":1
    }
    url="https://api.open-meteo.com/v1/forecast?"+urllib.parse.urlencode(params)
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"LemonOS/0.1"})
        with urllib.request.urlopen(req,timeout=8) as r: data=json.load(r)
        weather.update({
            "temp":round(data["current"]["temperature_2m"]),
            "high":round(data["daily"]["temperature_2m_max"][0]),
            "low":round(data["daily"]["temperature_2m_min"][0]),
            "code":int(data["current"]["weather_code"]),
            "is_day":int(data["current"].get("is_day", 1)),
            "loading":False,"error":None
        })
    except Exception as e:
        weather["loading"]=False; weather["error"]=str(e)

weather_thread = None

def refresh_weather_async():
    global weather_thread
    if weather_thread is None or not weather_thread.is_alive():
        weather_thread = threading.Thread(target=fetch_weather, daemon=True)
        weather_thread.start()
refresh_weather_async(); last_weather_refresh=time.time()

# The canvas occupies most of the display; every control has its own hit area.
paint_rect = pygame.Rect(12, 64, 616, 338)
paint_surface = pygame.Surface(paint_rect.size)
paint_surface.fill(PAPER)
paint_color = INK
brush_size = 4
last_point = None
screen_name = "home"
affirmation = random.choice(AFFIRMATIONS)
pressed_button = None
pressed_until = 0
last_activity = pygame.time.get_ticks()
home_seconds = 0.0
hop_started = -1000
home_lemon_rect = pygame.Rect(240, 180, 170, 170)
paint_tool = "brush"
DRAWINGS_DIR = Path(__file__).parent / "drawings"
gallery_files = []
gallery_index = 0
gallery_image = None
gallery_error = ""
paint_notice = ""

TOOLS_BTN = pygame.Rect(220, 8, 128, 48)
RETURN_PAINT_BTN = pygame.Rect(360, 8, 128, 48)
STAMP_BTN = pygame.Rect(44, 125, 176, 72)
SAVE_BTN = pygame.Rect(232, 125, 176, 72)
GALLERY_BTN = pygame.Rect(420, 125, 176, 72)
PREV_BTN = pygame.Rect(12, 416, 128, 52)
NEXT_BTN = pygame.Rect(500, 416, 128, 52)

DESKTOP_BTN = pygame.Rect(204, 4, 48, 48)
EXIT_CANCEL_BTN = pygame.Rect(120, 335, 180, 72)
EXIT_CONFIRM_BTN = pygame.Rect(340, 335, 180, 72)
quit_requested = False

HOME_WEATHER = pygame.Rect(24, 388, 184, 68)
HOME_REMINDER = pygame.Rect(228, 388, 184, 68)
HOME_PAINT = pygame.Rect(432, 388, 184, 68)
BACK_BTN = pygame.Rect(500, 8, 128, 48)
AGAIN_BTN = pygame.Rect(230, 350, 180, 60)
CLEAR_BTN = pygame.Rect(360, 8, 128, 48)
SMALL_BTN = pygame.Rect(12, 416, 98, 52)
BIG_BTN = pygame.Rect(118, 416, 98, 52)
PALETTE = [CREAM, GOLD, LAV, BLUE, AQUA, PAPER, INK, PINK]
palette_rects = [pygame.Rect(228 + i * 50, 416, 48, 52)
                 for i in range(len(PALETTE))]

def draw_header(title):
    draw_text(title, 18, 18, FONT)


def home_lemon_position(seconds):
    # A slow wander and a tiny hop, always above the navigation buttons.
    x = 240 + 100 * math.sin(seconds * 0.45)
    y = 180 + 20 * math.sin(seconds * 0.7) - 6 * abs(math.sin(seconds * 3))
    return round(x), round(y)


def weather_icon_name(code, is_day=1):
    if code == 0:
        return "sun" if is_day else "moon"
    if code in (1, 2):
        return "partly-cloudy" if is_day else "cloud"
    if code == 3:
        return "cloud"
    if code in (45, 48):
        return "fog"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    return "cloud"


def draw_weather_icon(rect):
    name = weather_icon_name(weather["code"], weather.get("is_day", 1))
    icon = images.get("weather_" + name)
    if icon is not None:
        blit_fitted(icon, rect)


def lemon_is_sleeping():
    return pygame.time.get_ticks() - last_activity >= 60000


wifi_status = "DEV MODE" if DEVELOPMENT else "WI-FI --"
wifi_thread = None
last_wifi_refresh = -10.0


def check_wifi():
    global wifi_status
    if DEVELOPMENT:
        wifi_status = "DEV MODE"
        return
    try:
        # Read connection state only; never change Wi-Fi settings or request secrets.
        result = subprocess.run(
            ["nmcli", "-t", "-f", "TYPE,STATE", "device", "status"],
            capture_output=True, text=True, timeout=4,
            env=dict(os.environ, LC_ALL="C"))
        states = [line.split(":", 1)[1] for line in result.stdout.splitlines()
                  if line.startswith("wifi:")]
        if result.returncode != 0 or not states or "unmanaged" in states:
            wifi_status = "WI-FI --"
        elif any(state.startswith("connected") for state in states):
            wifi_status = "WI-FI OK"
        else:
            wifi_status = "NO WI-FI"
    except (OSError, subprocess.TimeoutExpired):
        wifi_status = "WI-FI --"


def refresh_wifi():
    global wifi_thread, last_wifi_refresh
    if wifi_thread is None or not wifi_thread.is_alive():
        last_wifi_refresh = time.monotonic()
        wifi_thread = threading.Thread(target=check_wifi, daemon=True)
        wifi_thread.start()


def draw_desktop_control():
    # A small monitor symbol with a full 48x48 touch target.
    x, y = DESKTOP_BTN.center
    if pressed_button == DESKTOP_BTN and pygame.time.get_ticks() < pressed_until:
        pygame.draw.circle(screen, LAV, (x, y), 20)
    pygame.draw.rect(screen, (0, 0, 0), (x - 8, y - 7, 16, 11), 2)
    pygame.draw.line(screen, (0, 0, 0), (x, y + 4), (x, y + 8), 2)
    pygame.draw.line(screen, (0, 0, 0), (x - 5, y + 8), (x + 5, y + 8), 2)


def draw_wifi_icon():
    x, y = 180, DESKTOP_BTN.centery + 8
    known = wifi_status in ("WI-FI OK", "NO WI-FI")
    color = (0, 0, 0)
    for radius in (6, 11, 16):
        pygame.draw.arc(screen, color,
                        (x - radius, y - radius, radius * 2, radius * 2),
                        math.pi * 0.25, math.pi * 0.75, 2)
    pygame.draw.circle(screen, color, (x, y - 1), 2, 0 if known else 1)
    if wifi_status == "NO WI-FI":
        pygame.draw.line(screen, CREAM, (x - 10, y - 18), (x + 11, y + 1), 4)
        pygame.draw.line(screen, (0, 0, 0), (x - 10, y - 18), (x + 11, y + 1), 2)


def draw_home():
    global home_lemon_rect
    screen.fill(CREAM); draw_header("LEMON.OS")
    draw_desktop_control()
    draw_wifi_icon()
    mini="SF  --" if weather["loading"] else ("SF  OFFLINE" if weather["error"] else f"SF  {weather['temp']}°")
    draw_text(mini, WIDTH - SMALL.size(mini)[0] - 16, 15, SMALL)
    if not weather["loading"] and not weather["error"]:
        draw_weather_icon((440, 12, 28, 28))
    draw_cloud(15,72,130,62); draw_cloud(180,72,160,55,"cloud2"); draw_cloud(468,102,115,55)
    draw_cloud(55,225,130,60); draw_cloud(430,230,150,48,"cloud2")
    draw_star(150,130,34); draw_star(410,86,26); draw_star(392,205,26)
    lemon_x, lemon_y = home_lemon_position(home_seconds)
    now = pygame.time.get_ticks()
    if lemon_is_sleeping():
        lemon_y += round(2 * math.sin(now / 1200))
        for i in range(3):
            draw_text("z", lemon_x + 115 + i * 15,
                      lemon_y - 8 - i * 15 - round(3 * math.sin(now / 900)), SMALL)
    else:
        progress = (now - hop_started) / 700
        if 0 <= progress <= 1:
            lemon_y -= round(42 * math.sin(math.pi * progress))
    home_lemon_rect = pygame.Rect(lemon_x, lemon_y, 170, 170)
    draw_lemon(lemon_x, lemon_y, 170)
    pixel_button(HOME_WEATHER,"WEATHER",BLUE,images.get("weather_button"))
    pixel_button(HOME_REMINDER,"REMINDER",GOLD,images.get("reminder_button"))
    pixel_button(HOME_PAINT,"PAINT",AQUA,images.get("paint_button"))

def draw_exit():
    screen.fill(CREAM)
    draw_header("BACK TO DESKTOP")
    draw_lemon(270, 75, 100)
    draw_text("close LemonOS?", 320, 210, FONT, INK, True)
    draw_text("save your drawings in Paint first", 320, 250, SMALL, INK, True)
    draw_text("your computer will stay on", 320, 280, SMALL, INK, True)
    pixel_button(EXIT_CANCEL_BTN, "CANCEL")
    pixel_button(EXIT_CONFIRM_BTN, "DESKTOP")


def draw_weather():
    screen.fill(CREAM); draw_header("WEATHER"); draw_cloud(455,65,140,55,"cloud2"); draw_star(175,95,28)
    if weather["loading"]: draw_text("LOADING SF WEATHER...",320,190,FONT,INK,True)
    elif weather["error"]:
        draw_text("WEATHER OFFLINE",320,165,FONT,INK,True); draw_text("check Wi-Fi + try again",320,200,SMALL,INK,True)
    else:
        condition=WEATHER_TEXT.get(weather["code"],"WEATHER")
        draw_text(f"{weather['temp']}°F",70,110,BIG); draw_text(condition,70,190,FONT)
        draw_text(f"H {weather['high']}°   L {weather['low']}°",70,235,SMALL); draw_text("SAN FRANCISCO",70,280,SMALL)
        draw_weather_icon((440, 155, 96, 96))
    pixel_button(BACK_BTN,"HOME",LAV,images.get("blank_button"))

def draw_reminder():
    screen.fill(CREAM)
    draw_header("REMINDER")
    draw_cloud(420, 85, 170, 65, "cloud2")
    draw_star(65, 110, 40)
    draw_lemon(265, 75, 110)
    # Wrap at word boundaries so every affirmation fits the small display.
    lines = []
    line = ""
    for word in affirmation.split():
        candidate = (line + " " + word).strip()
        if FONT.size(candidate)[0] > 520:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    for i, line in enumerate(lines):
        draw_text(line, 320, 230 + i * 30, FONT, INK, True)
    pixel_button(AGAIN_BTN, "ANOTHER", GOLD, images.get("blank_button"))
    pixel_button(BACK_BTN, "HOME", LAV, images.get("blank_button"))


def draw_paint():
    screen.fill(CREAM)
    draw_header("PAINT")
    screen.blit(paint_surface, paint_rect.topleft)
    pygame.draw.rect(screen, INK, paint_rect.inflate(4, 4), 2)
    pixel_button(SMALL_BTN, "SMALL", LAV if brush_size == 4 else PAPER,
                 selected=paint_tool == "brush" and brush_size == 4)
    pixel_button(BIG_BTN, "BIG", LAV if brush_size == 12 else PAPER,
                 selected=paint_tool == "brush" and brush_size == 12)
    for rect, color in zip(palette_rects, PALETTE):
        pygame.draw.rect(screen, color, rect.inflate(-8, -8))
        pygame.draw.rect(screen, INK, rect.inflate(-8, -8), 2)
        if color == paint_color:
            pygame.draw.rect(screen, INK, rect, 3)
            # A contrasting check remains visible even on the dark swatch.
            check = PAPER if color == INK else INK
            x, y = rect.center
            pygame.draw.lines(screen, check, False,
                              [(x-7, y), (x-2, y+5), (x+8, y-7)], 3)
    pixel_button(TOOLS_BTN, "LEMON" if paint_tool == "stamp" else "TOOLS",
                 selected=paint_tool == "stamp")
    pixel_button(CLEAR_BTN, "CLEAR", GOLD)
    pixel_button(BACK_BTN, "HOME", LAV)


def draw_paint_tools():
    screen.fill(CREAM)
    draw_header("PAINT TOOLS")
    pixel_button(RETURN_PAINT_BTN, "PAINT")
    pixel_button(BACK_BTN, "HOME")
    pixel_button(STAMP_BTN, "STAMP", selected=paint_tool == "stamp")
    pixel_button(SAVE_BTN, "SAVE")
    pixel_button(GALLERY_BTN, "GALLERY")
    draw_lemon(94, 215, 76)
    draw_text("tap STAMP, then tap your canvas", 320, 325, SMALL, INK, True)
    draw_text("SMALL or BIG switches back to drawing", 320, 355, SMALL, INK, True)
    if paint_notice:
        draw_text(paint_notice, 320, 425, SMALL, INK, True)


def stamp_lemon(pos):
    lemon = images.get("lemon")
    if lemon is None:
        return
    scale = 76 / max(lemon.get_size())
    stamp = pygame.transform.scale(lemon, (round(lemon.get_width() * scale),
                                           round(lemon.get_height() * scale)))
    paint_surface.blit(stamp, stamp.get_rect(center=local_paint_pos(pos)))


def save_drawing():
    global paint_notice
    try:
        DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
        filename = "lemon-" + time.strftime("%Y%m%d-%H%M%S") + "-" + str(time.time_ns()) + ".png"
        destination = DRAWINGS_DIR / filename
        temporary = DRAWINGS_DIR / ("." + filename)
        pygame.image.save(paint_surface, str(temporary))
        temporary.replace(destination)
        paint_notice = "saved! find it in GALLERY"
    except (OSError, pygame.error):
        paint_notice = "could not save - check disk space"


def load_gallery_image():
    global gallery_image, gallery_error
    gallery_image = None
    gallery_error = ""
    if gallery_files:
        gallery_image = load_img(gallery_files[gallery_index])
        if gallery_image is None:
            gallery_error = "could not open this drawing"


def open_gallery():
    global gallery_files, gallery_index, screen_name, gallery_error
    gallery_index = 0
    try:
        gallery_files = sorted(DRAWINGS_DIR.glob("lemon-*.png"), reverse=True)
        load_gallery_image()
    except OSError:
        gallery_files = []
        gallery_error = "could not read saved drawings"
    screen_name = "gallery"


def draw_gallery():
    screen.fill(CREAM)
    draw_header("GALLERY")
    pixel_button(RETURN_PAINT_BTN, "PAINT")
    pixel_button(BACK_BTN, "HOME")
    if gallery_error:
        draw_text(gallery_error, 320, 235, SMALL, INK, True)
    elif gallery_image is not None:
        frame = blit_fitted(gallery_image, (24, 76, 592, 320))
        pygame.draw.rect(screen, INK, frame.inflate(4, 4), 2)
    else:
        draw_lemon(270, 125, 100)
        draw_text("your little art collection goes here", 320, 255, SMALL, INK, True)
        draw_text("save a drawing from PAINT > TOOLS", 320, 295, SMALL, INK, True)
    if gallery_index > 0:
        pixel_button(PREV_BTN, "PREV")
    if gallery_index + 1 < len(gallery_files):
        pixel_button(NEXT_BTN, "NEXT")
    if gallery_files:
        draw_text(f"{gallery_index + 1} / {len(gallery_files)}", 320, 440, SMALL, INK, True)


def local_paint_pos(pos):
    return (pos[0] - paint_rect.x, pos[1] - paint_rect.y)


def paint_to(pos):
    global last_point
    point = local_paint_pos(pos)
    if last_point is None:
        pygame.draw.circle(paint_surface, paint_color, point, brush_size)
    else:
        # Connect every event, even when the pointer moves quickly.
        pygame.draw.line(paint_surface, paint_color, last_point, point)
        dx = point[0] - last_point[0]
        dy = point[1] - last_point[1]
        steps = max(1, math.ceil(math.hypot(dx, dy)))
        # Fill the whole segment with overlapping round brush marks, one pixel
        # apart. Thickness stays consistent at every angle and at the joins.
        for step in range(1, steps + 1):
            fraction = step / steps
            center = (round(last_point[0] + dx * fraction),
                      round(last_point[1] + dy * fraction))
            pygame.draw.circle(paint_surface, paint_color, center, brush_size)
    last_point = point


def buttons_for_screen():
    if screen_name == "exit":
        return [EXIT_CANCEL_BTN, EXIT_CONFIRM_BTN]
    if screen_name == "home":
        return [HOME_WEATHER, HOME_REMINDER, HOME_PAINT, DESKTOP_BTN]
    if screen_name == "reminder":
        return [BACK_BTN, AGAIN_BTN]
    if screen_name == "paint":
        return [BACK_BTN, TOOLS_BTN, CLEAR_BTN, SMALL_BTN, BIG_BTN] + palette_rects
    if screen_name == "paint_tools":
        return [BACK_BTN, RETURN_PAINT_BTN, STAMP_BTN, SAVE_BTN, GALLERY_BTN]
    if screen_name == "gallery":
        buttons = [BACK_BTN, RETURN_PAINT_BTN]
        if gallery_index > 0:
            buttons.append(PREV_BTN)
        if gallery_index + 1 < len(gallery_files):
            buttons.append(NEXT_BTN)
        return buttons
    return [BACK_BTN]


def activate_button(rect):
    global screen_name, affirmation, brush_size, paint_color, paint_tool, gallery_index, paint_notice, quit_requested
    if screen_name == "exit":
        if rect == EXIT_CANCEL_BTN:
            screen_name = "home"
        elif rect == EXIT_CONFIRM_BTN:
            quit_requested = True
    elif screen_name == "home":
        if rect == DESKTOP_BTN:
            screen_name = "exit"
        elif rect == HOME_WEATHER:
            screen_name = "weather"
            refresh_weather_async()
        elif rect == HOME_REMINDER:
            screen_name = "reminder"
            affirmation = random.choice(AFFIRMATIONS)
        elif rect == HOME_PAINT:
            screen_name = "paint"
    elif rect == BACK_BTN:
        screen_name = "home"
    elif screen_name in ("paint_tools", "gallery") and rect == RETURN_PAINT_BTN:
        screen_name = "paint"
    elif screen_name == "paint_tools":
        if rect == STAMP_BTN:
            paint_tool = "stamp"
            screen_name = "paint"
        elif rect == SAVE_BTN:
            save_drawing()
        elif rect == GALLERY_BTN:
            open_gallery()
    elif screen_name == "gallery":
        if rect == PREV_BTN and gallery_index > 0:
            gallery_index -= 1
        elif rect == NEXT_BTN and gallery_index + 1 < len(gallery_files):
            gallery_index += 1
        load_gallery_image()
    elif screen_name == "reminder" and rect == AGAIN_BTN:
        affirmation = random.choice([text for text in AFFIRMATIONS if text != affirmation])
    elif screen_name == "paint":
        if rect == TOOLS_BTN:
            paint_notice = ""
            screen_name = "paint_tools"
        elif rect == SMALL_BTN:
            paint_tool = "brush"
            brush_size = 4
        elif rect == BIG_BTN:
            paint_tool = "brush"
            brush_size = 12
        elif rect == CLEAR_BTN:
            paint_surface.fill(PAPER)
        else:
            for swatch, color in zip(palette_rects, PALETTE):
                if rect == swatch:
                    paint_color = color
                    paint_tool = "brush"


def handle_event(event):
    global last_point, pressed_button, pressed_until, last_activity, hop_started
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.KEYDOWN):
        last_activity = pygame.time.get_ticks()
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and DEVELOPMENT:
        return False
    if event.type == pygame.WINDOWFOCUSLOST:
        last_point = None
        pressed_button = None
    # SDL maps touchscreen taps to mouse events; handle that single event stream.
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        last_point = None
        pressed_button = None
        if screen_name == "home" and home_lemon_rect.collidepoint(event.pos):
            hop_started = pygame.time.get_ticks()
        elif screen_name == "paint" and paint_rect.collidepoint(event.pos):
            if paint_tool == "stamp":
                stamp_lemon(event.pos)
            else:
                paint_to(event.pos)
        else:
            for rect in buttons_for_screen():
                if rect.collidepoint(event.pos):
                    pressed_button = rect
                    pressed_until = pygame.time.get_ticks() + 60000
                    break
    elif event.type == pygame.MOUSEMOTION and screen_name == "paint":
        if last_point is not None:
            paint_to(event.pos)  # The surface clips strokes at the canvas edges.
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        if last_point is not None and screen_name == "paint":
            paint_to(event.pos)
        last_point = None
        if pressed_button is not None:
            if pressed_button.collidepoint(event.pos):
                activate_button(pressed_button)
                pressed_until = pygame.time.get_ticks() + 140
            else:
                pressed_button = None
    return not quit_requested


DRAW_SCREEN = {"home": draw_home, "weather": draw_weather,
               "reminder": draw_reminder, "paint": draw_paint,
               "paint_tools": draw_paint_tools, "gallery": draw_gallery,
               "exit": draw_exit}


def main():
    global last_weather_refresh, home_seconds
    running = True
    while running:
        elapsed = min(clock.tick(FPS) / 1000, 0.1)
        if screen_name == "home" and not lemon_is_sleeping():
            home_seconds += elapsed
        if time.monotonic() - last_wifi_refresh >= 10:
            refresh_wifi()
        if time.time() - last_weather_refresh > 600:
            refresh_weather_async()
            last_weather_refresh = time.time()
        for event in pygame.event.get():
            if not handle_event(event):
                running = False
        DRAW_SCREEN[screen_name]()
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
