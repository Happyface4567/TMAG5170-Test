# TMAG5170 Test

Python test suite for the TI TMAG5170 3-axis Hall-effect sensor on Raspberry Pi. Includes a pure Python SPI driver ported from the [Arduino-TMAG5170](https://github.com/light655/arduino-tmag5170) library, a console test script, and a live tkinter GUI.

## Wiring (Raspberry Pi SPI0, CE0)

| TMAG5170 | Raspberry Pi       |
|----------|--------------------|
| SCLK     | GPIO 11 (pin 23)   |
| MOSI     | GPIO 10 (pin 19)   |
| MISO     | GPIO 9 (pin 21)    |
| CS       | GPIO 8 (pin 24)    |
| VCC      | 3.3V               |
| GND      | GND                |

## Setup

Enable SPI on the Raspberry Pi:

```bash
sudo raspi-config  # Interface Options -> SPI -> Enable
```

Clone and install dependencies:

```bash
git clone --recurse-submodules https://github.com/Happyface4567/TMAG5170-Test.git
cd TMAG5170-Test
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Console test

Prints X, Y, Z magnetic field readings to the terminal. Use this first to verify the sensor is connected and responding.

```bash
python test_console.py
```

### Live GUI

Tkinter dashboard with real-time numeric values and a scrolling time-series plot.

```bash
python test_gui.py
```

## Files

| File              | Description                                          |
|-------------------|------------------------------------------------------|
| `tmag5170.py`     | Python SPI driver (CRC, register read/write, config) |
| `test_console.py` | Console test script                                  |
| `test_gui.py`     | Tkinter live monitoring GUI                          |
| `Arduino-TMAG5170/` | Original Arduino C++ library (submodule)           |
