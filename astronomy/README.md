# Sky Watch --- Raspberry Pi Pico W Astronomy Display

Sky Watch is a MicroPython project for a Raspberry Pi Pico W and a
Waveshare 2.13-inch V4 e-Paper display in landscape orientation. It uses
Wi-Fi to retrieve astronomy information and alternates between two
display pages.

## Features

### Page 1 --- Sun and Moon

-   Moon phase and approximate illumination.
-   Approximate date of the next full moon.
-   Sunrise and sunset times for the configured location.

### Page 2 --- Live astronomy events

-   Fetches astronomy event information over Wi-Fi.
-   Shows upcoming events and objects reported as visible for the
    configured location.
-   Limits the number of events handled and uses garbage collection to
    help manage the Pico W's limited RAM.

The display alternates pages every 60 seconds. Astronomy events are
refreshed periodically rather than on every page change.

> **Note:** Event availability and descriptions depend on the remote API
> response and network access. The script has not been physically tested
> on every hardware setup.

## Hardware

-   Raspberry Pi Pico W
-   Waveshare 2.13-inch V4 e-Paper display, landscape version
-   USB cable and Wi-Fi network

## Files on the Pico

Save the low-memory astronomy script as `main.py` in the Pico's root
directory for automatic startup.

``` text
/
├── main.py
├── netman.py
├── paper.py
└── icons/
    ├── moon_new.pbm
    ├── moon_waxing_crescent.pbm
    ├── moon_first_quarter.pbm
    ├── moon_waxing_gibbous.pbm
    ├── moon_full.pbm
    ├── moon_waning_gibbous.pbm
    ├── moon_last_quarter.pbm
    ├── moon_waning_crescent.pbm
    ├── sunrise.pbm
    ├── sunset.pbm
    ├── meteor.pbm
    └── stars.pbm
```

Keep the names and folder structure exactly as expected by the script.
Retain your working `netman.py`, `paper.py`, and icon assets.

## Configuration

Check the configuration near the top of the script:

-   **Wi-Fi SSID and password:** enter your Wi-Fi credentials.
-   **Latitude:** `-34.046706`
-   **Longitude:** `18.762889`
-   **UTC offset:** `2` (South African Standard Time, UTC+2)

Change the coordinates and UTC offset if you use the display elsewhere.
Do not publish Wi-Fi credentials in a public repository.

## Install with Thonny

1.  Connect the Pico W and open Thonny.
2.  Select the Pico W's MicroPython interpreter.
3.  Choose **View → Files**.
4.  Save the low-memory astronomy script to the Pico as **`main.py`** in
    the root directory.
5.  Copy `netman.py` and `paper.py` to the root directory if they are
    not already present.
6.  Copy the `icons` directory and PBM files to the Pico, preserving
    their names.
7.  Check Wi-Fi credentials and location settings.
8.  Use **Stop/Restart** in Thonny, then test by unplugging and
    reconnecting the Pico W.

## Automatic startup

MicroPython runs `boot.py` and then `main.py` on startup. A file named
`astronomy.py` will not normally run by itself. Save the application as
`main.py` on the Pico to launch it automatically.

The e-Paper display has no backlight, so it will not glow like an LCD
when power is connected. It updates when the program sends a refresh
command and may continue showing the last image while unpowered.

## Troubleshooting

### It runs only when I click Run in Thonny

Confirm the application is saved on the Pico itself as `/main.py`, not
only on your computer or under another filename.

### Wi-Fi or API fetch fails

-   Confirm the Pico W connects to the configured Wi-Fi.
-   Check that the network has internet access.
-   Read the Thonny Shell for errors.
-   Remote API availability and response formats can change.

### Icons are missing

Check that files are inside `/icons/` and their names match the script
exactly. Filenames are case-sensitive.

### The display is blank or does not update

-   Check the Thonny Shell for startup errors.
-   Confirm `paper.py` matches the Waveshare landscape display.
-   Check display wiring and power.
-   Remember that e-Paper has no backlight; it only changes visibly when
    refreshed.

## Notes

-   Moon phase is approximate, not a precision astronomical ephemeris.
-   Sunrise and sunset depend on the configured coordinates and data
    source.
-   Live event information depends on the remote API's availability and
    response format.
-   Desktop syntax checks do not guarantee successful operation on the
    physical Pico W.
