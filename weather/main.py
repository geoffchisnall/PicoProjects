import netman
import urequests
import json
import framebuf
import time
import os
import ntptime

from paper import EPD_2in13_V4_Landscape

COUNTRY = "ZA"
SSID = "xxx"
PASSWORD = "xxx"
API_KEY = "xxx"
CITY_QUERY = "Helderberg,ZA"
UPDATE_INTERVAL = 15 * 60
PAGE_INTERVAL = 60
UTC_OFFSET_HOURS = 2
BLACK = 0x00
WHITE = 0xFF
ICON_DIR = "icons"

# Keep the same Waveshare driver and PBM icon format as the original script.
epd = EPD_2in13_V4_Landscape()


def connect_wifi():
    print("Connecting to Wi-Fi...")
    result = netman.connectWiFi(SSID, PASSWORD, COUNTRY)
    print("Wi-Fi connection attempted.")
    return result


def sync_clock():
    """Set the Pico RTC to UTC using NTP."""
    try:
        print("Syncing clock with NTP...")
        ntptime.settime()
        print("Clock synchronised.")
        return True
    except Exception as error:
        print("NTP clock sync failed:", error)
        return False


def get_local_time():
    """Current South African local time (UTC+2)."""
    return time.gmtime(time.time() + UTC_OFFSET_HOURS * 3600)


def get_json(url):
    response = None
    try:
        response = urequests.get(url)
        if response.status_code != 200:
            raise Exception("Weather API HTTP status: " + str(response.status_code))
        return response.json()
    finally:
        if response is not None:
            response.close()


def get_weather():
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        "?q=" + CITY_QUERY + "&appid=" + API_KEY + "&units=metric"
    )
    return get_json(url)

def wind_direction(degrees):
    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]

    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]


def get_forecast():
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        "?q=" + CITY_QUERY + "&appid=" + API_KEY + "&units=metric"
    )
    return get_json(url)

def icon_filename(weather_main):
    return ICON_DIR + "/" + str(weather_main) + ".pbm"


def load_icon(weather_main):
    """Load a P4 PBM and return (framebuffer, width, height)."""
    filename = icon_filename(weather_main)
    with open(filename, "rb") as f:
        magic = f.readline().strip()
        if magic != b"P4":
            raise Exception("Unsupported PBM format: " + filename)

        dimensions = b""
        while not dimensions:
            line = f.readline()
            if not line:
                raise Exception("Invalid PBM header")
            line = line.strip()
            if line and not line.startswith(b"#"):
                dimensions = line

        width, height = map(int, dimensions.split())
        data = bytearray(f.read())

    expected_size = ((width + 7) // 8) * height
    if len(data) < expected_size:
        raise Exception("PBM pixel data is truncated: " + filename)

    buffer = framebuf.FrameBuffer(data, width, height, framebuf.MONO_HLSB)
    return buffer, width, height


def draw_icon(weather_main):
    """Draw the full-size current-weather PBM icon."""
    filename = icon_filename(weather_main)
    try:
        icon_buffer, icon_width, icon_height = load_icon(weather_main)
        epd.blit(icon_buffer, 0, 55, WHITE)
    except Exception as error:
        print("Icon unavailable:", filename, error)


def draw_forecast_icon(weather_main, x, y, target_size=20):
    """Scale a PBM icon into a small square for a forecast column."""
    filename = icon_filename(weather_main)
    try:
        source, source_width, source_height = load_icon(weather_main)

        # Preserve the icon's aspect ratio instead of stretching it into a square.
        scale = min(target_size / source_width, target_size / source_height)
        draw_width = max(1, int(source_width * scale))
        draw_height = max(1, int(source_height * scale))

        stride = (draw_width + 7) // 8
        data = bytearray(stride * draw_height)
        small = framebuf.FrameBuffer(
            data, draw_width, draw_height, framebuf.MONO_HLSB
        )

        for py in range(draw_height):
            sy = min(source_height - 1, py * source_height // draw_height)
            for px in range(draw_width):
                sx = min(source_width - 1, px * source_width // draw_width)
                small.pixel(px, py, source.pixel(sx, sy))

        draw_x = x + (50 - draw_width) // 2
        epd.blit(small, draw_x, y, WHITE)
    except Exception as error:
        print("Forecast icon unavailable:", filename, error)


def draw_weather(weather):
    city = weather.get("name", CITY_QUERY)
    main_data = weather.get("main", {})
    weather_data = weather.get("weather", [{}])[0]
    wind_data = weather.get("wind", {})

    temp = main_data.get("temp", "N/A")
    feels_like = main_data.get("feels_like", "N/A")
    humidity = main_data.get("humidity", "N/A")
    wind_speed = wind_data.get("speed", "N/A")
    wind_deg = wind_data.get("deg", "N/A")
    weather_main = weather_data.get("main", "Unknown")
    description = weather_data.get("description", "N/A")

    now = get_local_time()
    date_text = "{:04d}-{:02d}-{:02d}".format(now[0], now[1], now[2])
    time_text = "{:02d}:{:02d}".format(now[3], now[4])

    epd.fill(WHITE)
    epd.text("Date:" + date_text, 5, 10, BLACK)
    epd.text("Time:" + time_text, 155, 10, BLACK)
    epd.text("Current Weather", 5, 20, BLACK)

    draw_icon(weather_main)

    epd.text("City: " + str(city), 65, 35, BLACK)
    epd.text("Conditions: " + str(weather_main), 65, 47, BLACK)
    epd.text("Description: " + str(description), 65, 59, BLACK)
    epd.text("Temp: " + str(temp) + "C", 65, 71, BLACK)
    epd.text("Feels: " + str(feels_like) + "C", 65, 83, BLACK)
    epd.text("Humidity: " + str(humidity) + "%", 65, 95, BLACK)
    epd.text("Wind Speed: " + str(wind_speed) + "m/s ", 65, 107, BLACK)
    epd.text("Wind Degrees: " + wind_direction(wind_deg), 65, 119, BLACK)

    epd.display(epd.buffer)
    epd.sleep()


def short_condition(main):
    """Short labels that fit in the narrow forecast columns."""
    value = str(main).lower()
    if "thunder" in value:
        return "Storm"
    if "drizzle" in value:
        return "Drizzle"
    if "rain" in value:
        return "Rain"
    if "snow" in value:
        return "Snow"
    if "clear" in value:
        return "Clear"
    if "cloud" in value:
        return "Cloud"
    if "mist" in value or "fog" in value or "haze" in value:
        return "Mist"
    return str(main)[:6]


def build_daily_forecast(forecast):
    """Group three-hour forecast slots by South African local calendar day."""
    days = {}
    entries = forecast.get("list", [])

    for entry in entries:
        local_dt = time.gmtime(entry.get("dt", 0) + UTC_OFFSET_HOURS * 3600)
        date_key = "{:04d}-{:02d}-{:02d}".format(local_dt[0], local_dt[1], local_dt[2])
        if date_key not in days:
            days[date_key] = {
                "year": local_dt[0], "month": local_dt[1], "day": local_dt[2],
                "weekday": local_dt[6], "high": -100, "low": 100,
                "condition": "Clouds", "pop": 0
            }

        day = days[date_key]
        main_data = entry.get("main", {})
        temp = main_data.get("temp", 0)
        if temp > day["high"]:
            day["high"] = temp
            weather_data = entry.get("weather", [{}])[0]
            day["condition"] = weather_data.get("main", "Clouds")
        if temp < day["low"]:
            day["low"] = temp

        pop = entry.get("pop", 0)
        pop_percent = int(pop * 100 + 0.5)
        if pop_percent > day["pop"]:
            day["pop"] = pop_percent

    result = []
    for key in sorted(days.keys()):
        result.append(days[key])
        if len(result) >= 5:
            break
    return result


def draw_forecast(forecast):
    daily = build_daily_forecast(forecast)
    now = get_local_time()
    date_text = "{:02d}-{:02d}".format(now[2], now[1])
    time_text = "{:02d}:{:02d}".format(now[3], now[4])

    epd.fill(WHITE)
    epd.text("5-Day Forecast", 5, 10, BLACK)
    epd.text(date_text, 155, 10, BLACK)
    epd.text(time_text, 200, 10, BLACK)
    epd.text("Helderberg", 5, 23, BLACK)

    col_width = 50
    weekdays = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    for index, day in enumerate(daily):
        x = index * col_width
        weekday = weekdays[day["weekday"]] if 0 <= day["weekday"] < 7 else "Day"
        if index > 0:
            epd.vline(x, 34, 84, BLACK)

        epd.text(weekday, x + 3, 42, BLACK)
        draw_forecast_icon(day["condition"], x, 52, 20)
        epd.text(short_condition(day["condition"]), x + 2, 74, BLACK)
        epd.text("H:{:02d}".format(int(day["high"] + 0.5)), x + 2, 87, BLACK)
        epd.text("L:{:02d}".format(int(day["low"] + 0.5)), x + 2, 99, BLACK)
        epd.text("R:{}%".format(day["pop"]), x + 2, 111, BLACK)

    epd.display(epd.buffer)
    epd.sleep()


connect_wifi()
sync_clock()

weather = None
forecast = None
last_fetch = -UPDATE_INTERVAL
seconds_since_page_change = PAGE_INTERVAL
current_page = 0

while True:
    try:
        if time.time() - last_fetch >= UPDATE_INTERVAL or weather is None or forecast is None:
            print("Fetching current weather and forecast...")
            weather = get_weather()
            try:
                forecast = get_forecast()
            except Exception as forecast_error:
                print("Forecast fetch failed:", forecast_error)
                # Keep the previous forecast, if one was already fetched.
                if forecast is None:
                    raise
            last_fetch = time.time()
            print("Weather data refreshed.")

        # Switch between pages every 15 seconds.
        if current_page == 0:
            epd = EPD_2in13_V4_Landscape()
            draw_weather(weather)
            print("Displayed Page 1: current weather")
            current_page = 1
        else:
            epd = EPD_2in13_V4_Landscape()
            draw_forecast(forecast)
            print("Displayed Page 2: five-day forecast")
            current_page = 0

    except Exception as error:
        print("Update failed:", error)

    # Sleep in short increments so page timing stays independent of API refresh.
    for _ in range(PAGE_INTERVAL):
        time.sleep(1)
