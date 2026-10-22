# Pico W e-Paper Two-Page Weather Display

A MicroPython weather display for the Raspberry Pi Pico W and a
Waveshare 2.13-inch e-Paper display in landscape orientation. The
program retrieves current weather conditions and a short forecast from
OpenWeather and presents them on two alternating pages.

## Features

### Page 1 --- Current weather

Displays current conditions returned by OpenWeather, using the icons and
layout defined in `main.py`.

### Page 2 --- Five-day forecast

-   Displays up to five forecast days.
-   Groups forecast entries by local date using UTC+2.
-   Uses OpenWeather's three-hour forecast entries to estimate each
    day's high and low temperatures.
-   Shows forecast information using the available weather icons.

**Forecast limitation:** The daily high and low are estimates calculated
from the available three-hour forecast entries. The first forecast day
may cover only part of the day, so its high and low may not represent a
full 24-hour period.

## Hardware and requirements

-   Raspberry Pi Pico W
-   Compatible Waveshare 2.13-inch e-Paper display, landscape version
-   USB cable and Wi-Fi network
-   MicroPython installed on the Pico W
-   An OpenWeather API key

## Project files

Copy these files and folders to the Pico's root directory, preserving
the expected names:

``` text
/
├── main.py       # Weather application and page-switching loop
├── netman.py     # Wi-Fi connection helper
├── paper.py      # E-Paper display driver
└── icons/        # Weather icon assets used by main.py
```

The `icons` folder must contain the PBM files referenced by `main.py`.
Keep the filenames and capitalisation unchanged.

## Configuration

Before running the program, open `main.py` in Thonny and replace the
example values for:

-   `SSID` --- your Wi-Fi network name.
-   `PASSWORD` --- your Wi-Fi password.
-   `API_KEY` --- your OpenWeather API key.

Do not share or publish a copy of `main.py` containing your Wi-Fi
password or API key.

The forecast grouping is configured for **UTC+2**. If you use the
display in a different time zone, update the time-zone handling in the
script accordingly.

## Installation with Thonny

1.  Connect the Pico W to your computer.
2.  Open Thonny and select the Raspberry Pi Pico / MicroPython
    interpreter.
3.  Select **View → Files** to show the computer and Pico file panes.
4.  Copy `netman.py` to the Pico's root directory.
5.  Copy `paper.py` to the Pico's root directory.
6.  Copy the complete `icons` folder and its PBM files to the Pico.
7.  Open `main.py` on your computer, update `SSID`, `PASSWORD`, and
    `API_KEY`, then save it **to the Pico** as `/main.py`.
8.  Click **Run** in Thonny and check the Shell for connection or API
    errors.
9.  Once it works, stop the program and unplug/reconnect the Pico W to
    test automatic startup.

## Normal operation

-   **Page 1:** current weather conditions.
-   **Page 2:** up to five forecast days.
-   **Page interval:** pages alternate every 15 seconds.
-   **Refresh interval:** current conditions and forecast are fetched
    every 15 minutes.

MicroPython automatically executes `main.py` at startup. Make sure the
working script is saved on the Pico itself as `main.py`, not just on
your computer or under another filename.

The e-Paper display has no backlight. It does not glow when power is
connected; the image changes when the program refreshes the display.

## Troubleshooting

### The display does not update after power-on

-   Check that the application is saved on the Pico as `/main.py`.
-   Connect with Thonny and inspect the Shell for startup errors.
-   Confirm `netman.py`, `paper.py`, and the `icons` directory are
    present on the Pico.

### Wi-Fi does not connect

-   Check the SSID and password for spelling and capitalisation.
-   Confirm the Wi-Fi network is available to the Pico W.
-   Check the Thonny Shell for connection errors.

### OpenWeather requests fail

-   Verify that `API_KEY` is correct.
-   Confirm that the network has internet access.
-   Check the Shell for HTTP or API error messages.

### Icons are missing or incorrect

-   Make sure the `icons` folder and PBM files were copied to the Pico.
-   Preserve the filenames and capitalisation expected by `main.py`.

## Notes and limitations

-   The forecast uses three-hour forecast entries rather than a separate
    daily forecast feed.
-   Daily high/low values are estimates derived from those entries.
-   The first forecast day may be partial.
-   Display layout and icon availability depend on the files and driver
    version used by the project.
