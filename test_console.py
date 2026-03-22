"""
Console test script for TMAG5170 on Raspberry Pi.
Reads X, Y, Z magnetic field and prints to console at ~1 Hz.

Wiring (Raspberry Pi SPI0, CE0):
  SCLK -> GPIO 11 (pin 23)
  MOSI -> GPIO 10 (pin 19)
  MISO -> GPIO 9  (pin 21)
  CS   -> GPIO 8  (pin 24) [CE0]
  VCC  -> 3.3V
  GND  -> GND

Make sure SPI is enabled: sudo raspi-config -> Interface Options -> SPI -> Enable
Install spidev: pip install spidev
"""

import time
from tmag5170 import (
    TMAG5170, CONV_AVG_32x,
    X_RANGE_300mT, Y_RANGE_300mT, Z_RANGE_300mT,
    VERSION_A1, VERSION_A2, VERSION_ERROR,
)


def main():
    sensor = TMAG5170(bus=0, device=0, speed_hz=1000000)
    sensor.open()

    try:
        version = sensor.init()
        version_names = {VERSION_A1: "A1", VERSION_A2: "A2", VERSION_ERROR: "ERROR"}
        print(f"TMAG5170 detected, version: {version_names.get(version, 'UNKNOWN')}")

        if version == VERSION_ERROR:
            print("ERROR: Could not identify sensor. Check wiring and SPI config.")
            return

        sensor.set_conversion_average(CONV_AVG_32x)
        sensor.enable_magnetic_channel(x=True, y=True, z=True)
        sensor.set_magnetic_range(X_RANGE_300mT, Y_RANGE_300mT, Z_RANGE_300mT)

        print("Reading magnetic field (Ctrl+C to stop)...\n")
        print(f"{'Bx (mT)':>10}  {'By (mT)':>10}  {'Bz (mT)':>10}")
        print("-" * 36)

        while True:
            bx, by, bz = sensor.read_xyz()
            print(f"{bx:>10.3f}  {by:>10.3f}  {bz:>10.3f}")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sensor.close()


if __name__ == "__main__":
    main()