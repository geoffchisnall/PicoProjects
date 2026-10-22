# astronomy.py
# Raspberry Pi Pico W + Waveshare 2.13-inch V4 e-Paper (landscape)
# Uses the existing netman.py and paper.py modules.
#
# Displays sunrise, sunset, Moon phase and approximate illumination
# for Helderberg, South Africa. Sunrise/sunset data is from
# sunrise-sunset.org; attribution is shown on the screen.

import time
import math
import json
import gc
import urequests
import ntptime
import netman
from paper import EPD_2in13_V4_Landscape

# ---- Wi-Fi settings ----
COUNTRY = "ZA"
SSID = "xxx"
PASSWORD = "xxx"

# ---- Helderberg, South Africa ----
LAT = "-34.046706"
LON = "18.762889"
UTC_OFFSET_HOURS = 2  # South Africa Standard Time (UTC+2)

UPDATE_SECONDS = 60 * 60  # Sunrise/sunset refresh: hourly
EVENT_UPDATE_SECONDS = 12 * 60 * 60  # Live event calendar: every 12 hours
VISIBLE_UPDATE_SECONDS = 30 * 60  # Local sky objects: every 30 minutes
BLACK = 0x00
WHITE = 0xFF

SUN_URL = (
    "https://api.sunrise-sunset.org/json?lat="
    + LAT + "&lng=" + LON + "&formatted=0"
)

def get_sun_data():
    response = None
    try:
        response = urequests.get(SUN_URL)
        if response.status_code != 200:
            raise Exception("Sun API HTTP " + str(response.status_code))
        data = response.json()
        if data.get("status") != "OK":
            raise Exception("Sun API status: " + str(data.get("status")))
        return data["results"]
    finally:
        if response is not None:
            response.close()

def sync_clock():
    # Pico's RTC is set to UTC by NTP.
    ntptime.settime()

def local_time_tuple():
    # Convert UTC epoch to South African local time.
    return time.localtime(time.time() + UTC_OFFSET_HOURS * 3600)

def format_api_time(iso_time):
    # API returns ISO strings such as 2026-10-21T04:30:00+00:00.
    # Extract UTC hour/minute, then convert to SAST (UTC+2).
    hour = int(iso_time[11:13])
    minute = int(iso_time[14:16])
    total = (hour * 60 + minute + UTC_OFFSET_HOURS * 60) % (24 * 60)
    local_hour = total // 60
    local_minute = total % 60
    return "{:02d}:{:02d}".format(local_hour, local_minute)

def moon_phase():
    # Approximate lunar phase using the synodic month.
    # Reference new Moon: 2000-01-06 18:14 UTC.
    now = time.time()
    reference = 947182440
    synodic_month = 29.530588853 * 24 * 60 * 60
    phase = ((now - reference) % synodic_month) / synodic_month

    illumination = (1 - math.cos(2 * math.pi * phase)) / 2 * 100

    if phase < 0.03 or phase >= 0.97:
        name = "New Moon"
        icon = "( )"
    elif phase < 0.22:
        name = "Waxing crescent"
        icon = "( D"
    elif phase < 0.28:
        name = "First quarter"
        icon = "(|)"
    elif phase < 0.47:
        name = "Waxing gibbous"
        icon = "( O"
    elif phase < 0.53:
        name = "Full Moon"
        icon = "(O)"
    elif phase < 0.72:
        name = "Waning gibbous"
        icon = "O )"
    elif phase < 0.78:
        name = "Last quarter"
        icon = "(|)"
    else:
        name = "Waning crescent"
        icon = "D )"

    return name, int(illumination + 0.5), icon, phase

def next_full_moon_text():
    # Estimate the next full Moon from the same synodic-month model.
    # This is approximate; it is not an ephemeris-grade prediction.
    now = time.time()
    reference = 947182440  # 2000-01-06 18:14 UTC, approximate new Moon
    synodic_month = 29.530588853 * 24 * 60 * 60
    cycle_number = int((now - reference) / synodic_month)
    full_epoch = reference + (cycle_number + 0.5) * synodic_month
    if full_epoch <= now:
        full_epoch += synodic_month

    local_full = time.localtime(int(full_epoch + UTC_OFFSET_HOURS * 3600))
    return "Full: {:02d}/{:02d} {:02d}:{:02d}".format(
        local_full[2], local_full[1], local_full[3], local_full[4]
    )

def draw_moon(epd, center_x, center_y, radius, phase):
    """Draw a visible monochrome Moon with a curved phase boundary."""
    r2 = radius * radius
    angle = 2 * math.pi * phase
    waxing = phase < 0.5
    terminator = math.cos(angle)

    # Start with a solid black lunar disc so the dark portion is visible.
    for y in range(-radius, radius + 1):
        for x in range(-radius, radius + 1):
            if x * x + y * y <= r2:
                epd.pixel(center_x + x, center_y + y, BLACK)

    # Paint the illuminated portion white. The terminator is curved, as
    # seen from Earth; waxing phases are lit from the right, waning from left.
    for y in range(-radius, radius + 1):
        row_extent_sq = r2 - y * y
        if row_extent_sq < 0:
            continue
        row_extent = math.sqrt(row_extent_sq)
        boundary = terminator * row_extent
        for x in range(-radius, radius + 1):
            if x * x + y * y > r2:
                continue
            if waxing:
                lit = x >= boundary
            else:
                lit = x <= -boundary
            if lit:
                epd.pixel(center_x + x, center_y + y, WHITE)

    # Restore a crisp circular outline, including around the white side.
    for degree in range(0, 360, 5):
        a = degree * math.pi / 180
        px = center_x + int(radius * math.cos(a))
        py = center_y + int(radius * math.sin(a))
        epd.pixel(px, py, BLACK)

    # Small four-point stars around the Moon.
    for sx, sy in ((center_x - radius - 5, center_y - 8),
                   (center_x + radius + 4, center_y - 12),
                   (center_x + radius + 5, center_y + 9)):
        epd.pixel(sx, sy, BLACK)
        epd.pixel(sx - 1, sy, BLACK)
        epd.pixel(sx + 1, sy, BLACK)
        epd.pixel(sx, sy - 1, BLACK)
        epd.pixel(sx, sy + 1, BLACK)

def draw_sun_icon(epd, center_x, horizon_y, arrow_up):
    """Draw matching sunrise/sunset icons; only the arrow direction differs."""
    # Sun is a filled semicircle above the horizon.
    radius = 11
    for y in range(-radius, 1):
        for x in range(-radius, radius + 1):
            if x * x + y * y <= radius * radius:
                epd.pixel(center_x + x, horizon_y + y, BLACK)

    # Rays: short, chunky marks above and beside the sun.
    epd.line(center_x, horizon_y - 20, center_x, horizon_y - 16, BLACK)
    epd.line(center_x - 17, horizon_y - 14, center_x - 14, horizon_y - 11, BLACK)
    epd.line(center_x + 14, horizon_y - 11, center_x + 17, horizon_y - 14, BLACK)
    epd.line(center_x - 22, horizon_y - 3, center_x - 18, horizon_y - 2, BLACK)
    epd.line(center_x + 18, horizon_y - 2, center_x + 22, horizon_y - 3, BLACK)

    # Horizon and three shorter reflection/horizon lines.
    epd.hline(center_x - 24, horizon_y, 48, BLACK)
    epd.hline(center_x - 17, horizon_y + 5, 34, BLACK)
    epd.hline(center_x - 11, horizon_y + 10, 22, BLACK)

    # Same arrow shape for both icons, reversed vertically for sunset.
    if arrow_up:
        epd.line(center_x, horizon_y - 31, center_x, horizon_y - 24, BLACK)
        epd.line(center_x, horizon_y - 31, center_x - 4, horizon_y - 27, BLACK)
        epd.line(center_x, horizon_y - 31, center_x + 4, horizon_y - 27, BLACK)
    else:
        epd.line(center_x, horizon_y + 14, center_x, horizon_y + 21, BLACK)
        epd.line(center_x, horizon_y + 21, center_x - 4, horizon_y + 17, BLACK)
        epd.line(center_x, horizon_y + 21, center_x + 4, horizon_y + 17, BLACK)


# PBM icon assets must be copied to /icons on the Pico.
ICON_DIR = "icons"

def load_pbm_icon(filename, x, y):
    """Draw an ASCII PBM (P1) icon; PBM 1=black, 0=white."""
    path = ICON_DIR + "/" + filename
    with open(path, "r") as f:
        tokens = []
        for line_text in f:
            line_text = line_text.strip()
            if not line_text or line_text.startswith("#"):
                continue
            tokens.extend(line_text.split())

    if len(tokens) < 3 or tokens[0] != "P1":
        raise Exception("Invalid PBM icon: " + filename)

    width = int(tokens[1])
    height = int(tokens[2])
    pixels = tokens[3:]
    if len(pixels) < width * height:
        raise Exception("Incomplete PBM icon: " + filename)

    # Only paint black pixels; the display background has already been cleared white.
    index = 0
    for py in range(height):
        for px in range(width):
            if pixels[index] == "1":
                epd_pixel = (x + px, y + py)
                # Drawing is performed by the wrapper below.
                _active_epd.pixel(epd_pixel[0], epd_pixel[1], BLACK)
            index += 1

def draw_icon(epd, filename, x, y):
    global _active_epd
    _active_epd = epd
    load_pbm_icon(filename, x, y)

def moon_icon_filename(phase):
    # Keep the phase names aligned with moon_phase() boundaries.
    if phase < 0.03 or phase >= 0.97:
        return "moon_new.pbm"
    if phase < 0.22:
        return "moon_waxing_crescent.pbm"
    if phase < 0.28:
        return "moon_first_quarter.pbm"
    if phase < 0.47:
        return "moon_waxing_gibbous.pbm"
    if phase < 0.53:
        return "moon_full.pbm"
    if phase < 0.72:
        return "moon_waning_gibbous.pbm"
    if phase < 0.78:
        return "moon_last_quarter.pbm"
    return "moon_waning_crescent.pbm"


def get_json(url):
    """Fetch JSON with explicit garbage collection for the Pico W."""
    gc.collect()
    response = None
    try:
        response = urequests.get(url)
        if response.status_code != 200:
            raise Exception("Astronomy API HTTP " + str(response.status_code))
        data = response.json()
        gc.collect()
        return data
    finally:
        if response is not None:
            response.close()
        gc.collect()


EVENTS_URL = "https://spacecatalog.org/api/v1/events?limit=10"
VISIBLE_URL = (
    "https://spacecatalog.org/api/v1/visible?lat=" + LAT
    + "&lon=" + LON + "&min_alt=15&limit=10"
)


def get_live_events():
    """Get upcoming dated sky events from SpaceCatalog.org."""
    data = get_json(EVENTS_URL)
    raw_events = data.get("events", [])
    now = time.gmtime(time.time())
    now_text = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
        now[0], now[1], now[2], now[3], now[4], now[5]
    )
    # Keep only a small number of upcoming entries and only fields used on-screen.
    upcoming = []
    for event in raw_events:
        event_time = event.get("time", "")
        window = event.get("window", {})
        if window and window.get("start"):
            event_time = window.get("start")
        if event_time >= now_text:
            upcoming.append({
                "title": event.get("title", "Sky event"),
                "time": event_time,
                "kind": event.get("kind", ""),
                "summary": event.get("summary", event.get("description", "Upcoming sky event")),
                "window": {"start": event_time} if event.get("kind") == "shower" else {}
            })
    upcoming.sort(key=lambda item: item.get("time", "9999"))
    del data
    del raw_events
    gc.collect()
    return upcoming[:5]


def get_visible_objects():
    """Get objects above the Helderberg horizon right now."""
    return get_json(VISIBLE_URL)


def format_event_time(iso_time):
    """Convert an ISO UTC event timestamp to South African local date/time."""
    if not iso_time or len(iso_time) < 16:
        return "Date/time TBC"
    try:
        year = int(iso_time[0:4])
        month = int(iso_time[5:7])
        day = int(iso_time[8:10])
        hour = int(iso_time[11:13])
        minute = int(iso_time[14:16])
        second = int(iso_time[17:19]) if len(iso_time) >= 19 else 0
        epoch = time.mktime((year, month, day, hour, minute, second, 0, 0))
        local = time.gmtime(epoch + UTC_OFFSET_HOURS * 3600)
        return "{:02d}/{:02d} {:02d}:{:02d}".format(
            local[2], local[1], local[3], local[4]
        )
    except Exception:
        # Fallback still labels the time as UTC-derived if parsing fails.
        return iso_time[0:10]


def event_icon_filename(kind):
    """Choose an icon from the PBM assets already used by this project."""
    if kind == "shower":
        return "meteor.pbm"
    if kind == "eclipse" or kind == "moon":
        return "moon_full.pbm"
    if kind in ("conjunction", "opposition", "elongation"):
        return "stars.pbm"
    return "stars.pbm"


def get_next_event(events):
    """Return the next event and its existing local PBM icon."""
    if not events:
        return (
            "NO EVENTS FOUND", "Try again later", "Calendar unavailable",
            "Check Wi-Fi/API", "stars.pbm"
        )

    event = events[0]
    title = event.get("title", "Sky event")
    kind = event.get("kind", "")
    date_text = format_event_time(event.get("time", ""))
    if kind == "shower" and event.get("window"):
        date_text = format_event_time(event["window"].get("start", event.get("time", "")))
        timing = "Meteor shower window"
    else:
        timing = kind.upper()[:20] if kind else "ASTRONOMY EVENT"

    summary = event.get("summary", event.get("description", "Upcoming sky event"))
    return (title, date_text, timing, summary, event_icon_filename(kind))


def short_object_name(obj):
    name = obj.get("name", obj.get("slug", "Sky object"))
    return str(name)[:18]


def draw_visible_objects(epd, visible):
    """Show two locally computed objects above the horizon."""
    objects = visible.get("objects", [])
    sun = visible.get("sun", {})
    condition = sun.get("condition", "unknown")

    if condition == "daylight":
        epd.text("LOCAL SKY: DAYLIGHT", 8, 99, BLACK)
    elif condition in ("civil twilight", "nautical twilight", "astronomical twilight"):
        epd.text("LOCAL SKY: TWILIGHT", 8, 99, BLACK)
    elif condition == "night":
        epd.text("LOCAL SKY: NIGHT", 8, 99, BLACK)
    else:
        epd.text("LOCAL SKY OBJECTS", 8, 99, BLACK)

    if not objects:
        epd.text("No objects returned", 8, 110, BLACK)
        return

    first = objects[0]
    first_text = short_object_name(first)
    if first.get("direction"):
        first_text += " " + str(first.get("direction"))
    epd.text(first_text[:28], 8, 110, BLACK)

    if len(objects) > 1:
        second = objects[1]
        second_text = short_object_name(second)
        if second.get("direction"):
            second_text += " " + str(second.get("direction"))
        epd.text(second_text[:28], 8, 120, BLACK)



def draw_header(epd, now, page_number):
    date_text = "{:02d}/{:02d}/{:04d}".format(now[2], now[1], now[0])
    clock_text = "{:02d}:{:02d}".format(now[3], now[4])
    epd.fill(WHITE)
    epd.text("SKY WATCH", 5, 8, BLACK)
    epd.text(date_text, 95, 8, BLACK)
    epd.text(clock_text, 190, 8, BLACK)
    epd.hline(5, 20, 240, BLACK)

def draw_page1(epd, sun):
    # Preserve the user's current Page 1 layout: Moon status and sun times.
    now = local_time_tuple()
    sunrise = format_api_time(sun["sunrise"])
    sunset = format_api_time(sun["sunset"])
    phase_name, illumination, moon_icon, phase = moon_phase()

    draw_header(epd, now, 1)
    draw_icon(epd, moon_icon_filename(phase), 12, 21)
    epd.text(phase_name, 60, 27, BLACK)
    epd.text("Illumination: " + str(illumination) + "%", 60, 38, BLACK)
    epd.text(next_full_moon_text(), 60, 49, BLACK)

    epd.hline(5, 61, 240, BLACK)
    draw_icon(epd, "sunrise.pbm", 45, 75)
    draw_icon(epd, "sunset.pbm", 165, 70)
    epd.text("SUNRISE", 40, 66, BLACK)
    epd.text(sunrise, 45, 120, BLACK)
    epd.text("SUNSET", 160, 66, BLACK)
    epd.text(sunset, 165, 120, BLACK)
    epd.text("1/2", 220, 120, BLACK)

def draw_page2(epd, events, visible):
    now = local_time_tuple()
    draw_header(epd, now, 2)

    title, date_text, timing, hint, icon_name = get_next_event(events)
    epd.text("NEXT SKY EVENT", 8, 27, BLACK)
    epd.hline(8, 39, 234, BLACK)

    try:
        draw_icon(epd, icon_name, 12, 48)
    except Exception as error:
        print("Event icon unavailable:", icon_name, error)

    epd.text(title[:23], 58, 48, BLACK)
    epd.text(date_text[:23], 58, 62, BLACK)
    epd.text(timing[:23], 58, 76, BLACK)
    epd.text(hint[:23], 58, 88, BLACK)

    draw_visible_objects(epd, visible)


def draw_page(epd, sun, page, events, visible):
    if page == 0:
        draw_page1(epd, sun)
    else:
        draw_page2(epd, events, visible)
    epd.display(epd.buffer)
    epd.sleep()

def main():
    print("Connecting to Wi-Fi...")
    netman.connectWiFi(SSID, PASSWORD, COUNTRY)

    print("Syncing clock...")
    sync_clock()

    epd = EPD_2in13_V4_Landscape()
    sun = None
    events = []
    visible = {"objects": [], "sun": {"condition": "unknown"}}
    last_sun_fetch = 0
    last_event_fetch = 0
    last_visible_fetch = 0
    page = 0

    while True:
        now_epoch = time.time()
        try:
            if sun is None or now_epoch - last_sun_fetch >= UPDATE_SECONDS:
                print("Fetching sunrise/sunset...")
                sun = get_sun_data()
                last_sun_fetch = time.time()
                print("Sunrise UTC:", sun["sunrise"])
                print("Sunset UTC:", sun["sunset"])

            if not events or now_epoch - last_event_fetch >= EVENT_UPDATE_SECONDS:
                print("Fetching live astronomy events...")
                try:
                    events = get_live_events()
                    gc.collect()
                    last_event_fetch = time.time()
                    print("Upcoming events:", len(events))
                except Exception as event_error:
                    print("Event fetch failed:", event_error)
                    # Keep cached events; retry on the next loop if none exist.
                    if not events:
                        events = []

            if not visible.get("objects") or now_epoch - last_visible_fetch >= VISIBLE_UPDATE_SECONDS:
                print("Fetching objects above Helderberg...")
                try:
                    visible = get_visible_objects()
                    gc.collect()
                    last_visible_fetch = time.time()
                    print("Objects returned:", len(visible.get("objects", [])))
                except Exception as visible_error:
                    print("Visible-object fetch failed:", visible_error)
                    # Keep the previous result if the API is temporarily unavailable.

            epd = EPD_2in13_V4_Landscape()
            draw_page(epd, sun, page, events, visible)
            print("Displayed page", page + 1)
            page = 1 - page

        except Exception as error:
            print("Astronomy update failed:", error)

        print("Switching page in 1 minute...")
        time.sleep(60)

main()
