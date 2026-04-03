"""
TMAG5170 Python driver for Raspberry Pi via spidev.
Ported from the Arduino-TMAG5170 C++ library.
"""

import spidev
import struct

# Register offsets
DEVICE_CONFIG = 0x00
SENSOR_CONFIG = 0x01
SYSTEM_CONFIG = 0x02
ALERT_CONFIG = 0x03
X_THRX_CONFIG = 0x04
Y_THRX_CONFIG = 0x05
Z_THRX_CONFIG = 0x06
T_THRX_CONFIG = 0x07
CONV_STATUS = 0x08
X_CH_RESULT = 0x09
Y_CH_RESULT = 0x0A
Z_CH_RESULT = 0x0B
TEMP_RESULT = 0x0C
AFE_STATUS = 0x0D
SYS_STATUS = 0x0E
TEST_CONFIG = 0x0F
OSC_MONITOR = 0x10
MAG_GAIN_CONFIG = 0x11
ANGLE_RESULT = 0x13
MAGNITUDE_RESULT = 0x14

READ_REG = 0x80
START_CONVERSION = 0x10

# DEVICE_CONFIG
CONV_AVG_1x = 0x0000
CONV_AVG_2x = 0x1000
CONV_AVG_4x = 0x2000
CONV_AVG_8x = 0x3000
CONV_AVG_16x = 0x4000
CONV_AVG_32x = 0x5000

CONV_AVG_MASK = 0x7000
OPERATING_MODE_MASK = 0x70
MAG_CH_EN_MASK = 0x03C0
X_RANGE_MASK = 0x0003
Y_RANGE_MASK = 0x000C
Z_RANGE_MASK = 0x0030
ANGLE_EN_MASK = 0xC000

OPERATING_MODE_ConfigurationMode = 0x00
OPERATING_MODE_StandbyMode = 0x10
OPERATING_MODE_ActiveMeasureMode = 0x20
OPERATING_MODE_ActiveTriggerMode = 0x30
OPERATING_MODE_WakeupAndSleepMode = 0x40
OPERATING_MODE_SleepMode = 0x50
OPERATING_MODE_DeepsleepMode = 0x60

# Range defines (A1 variant)
X_RANGE_50mT = 0x0
X_RANGE_25mT = 0x1
X_RANGE_100mT = 0x2
Y_RANGE_50mT = 0x0
Y_RANGE_25mT = 0x4
Y_RANGE_100mT = 0x8
Z_RANGE_50mT = 0x0
Z_RANGE_25mT = 0x10
Z_RANGE_100mT = 0x20

# Range defines (A2 variant)
X_RANGE_150mT = 0x0
X_RANGE_75mT = 0x1
X_RANGE_300mT = 0x2
Y_RANGE_150mT = 0x0
Y_RANGE_75mT = 0x4
Y_RANGE_300mT = 0x8
Z_RANGE_150mT = 0x0
Z_RANGE_75mT = 0x10
Z_RANGE_300mT = 0x20

# Alert config
RSLT_ALRT_Asserted = 0x100

VERSION_A1 = 0
VERSION_A2 = 1
VERSION_ERROR = 3

# DEVICE_CONFIG temperature bits
T_CH_EN_MASK = 0x000C   # bits 3:2
T_CH_EN_ENABLED = 0x0008  # enable temp channel, T_RATE = same as other sensors

# Temperature conversion constants (TMAG5170 datasheet)
_TEMP_TSENS_T0 = 25.0    # °C reference temperature
_TEMP_TADC_T0 = 17508    # ADC code at 25 °C (typical)
_TEMP_TADC_RES = 60.1    # LSB / °C (typical)

# Range coefficient lookup: (version, range_code) -> mT full-scale
_RANGE_COEFF = {
    # X axis (bits 1:0)
    (VERSION_A1, 0x0): 50.0,
    (VERSION_A1, 0x1): 25.0,
    (VERSION_A1, 0x2): 100.0,
    (VERSION_A2, 0x0): 150.0,
    (VERSION_A2, 0x1): 75.0,
    (VERSION_A2, 0x2): 300.0,
}


class TMAG5170:
    def __init__(self, bus=0, device=0, speed_hz=1000000):
        self.spi = spidev.SpiDev()
        self.bus = bus
        self.device = device
        self.speed_hz = speed_hz
        self.version = VERSION_ERROR
        self.magnetic_coeff = [0.0, 0.0, 0.0]
        self.error_stat = 0

        self.registers = [
            0x0000, 0x0000, 0x0000, 0x0000,
            0x7D83, 0x7D83, 0x7D83, 0x6732,
            0x0000, 0x0000, 0x0000, 0x0000,
            0x0000, 0x8000, 0x0000, 0x8000,
            0x0000, 0x0000, 0x0000, 0x0000,
            0x0000,
        ]

    def open(self):
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = self.speed_hz
        self.spi.mode = 0b00  # SPI mode 0 (CPOL=0, CPHA=0)
        self.spi.bits_per_word = 8

    def close(self):
        self.spi.close()

    @staticmethod
    def generate_crc(data):
        """Generate 4-bit CRC. Input data should have lower 4 bits clear."""
        crc = 0xF
        for i in range(32):
            inv = ((data >> 31) & 1) ^ ((crc >> 3) & 1)
            poly = (inv << 1) | inv
            crc = ((crc << 1) ^ poly) & 0xF
            data = (data << 1) & 0xFFFFFFFF
        return crc

    @staticmethod
    def check_crc(frame):
        """Returns True if CRC is valid."""
        calc = TMAG5170.generate_crc(frame & 0xFFFFFFF0)
        return calc == (frame & 0xF)

    def exchange_frame(self, frame):
        """Send a 32-bit SPI frame, return the 32-bit response."""
        tx = list(frame.to_bytes(4, byteorder='big'))
        rx = self.spi.xfer2(tx)
        received = int.from_bytes(rx, byteorder='big')

        # Update ERROR_STAT from first byte and upper nibble of last byte
        self.error_stat = (rx[0] << 4) | ((rx[3] & 0xF0) >> 4)
        return received

    def read_register(self, offset, start_conversion=False):
        """Read a 16-bit register. Retries until CRC is valid."""
        frame = (offset | READ_REG) << 24
        if start_conversion:
            frame |= START_CONVERSION
        frame |= self.generate_crc(frame)

        for _ in range(10):
            received = self.exchange_frame(frame)
            if self.check_crc(received):
                reg_val = (received >> 8) & 0xFFFF
                if offset < len(self.registers):
                    self.registers[offset] = reg_val
                return reg_val
        raise RuntimeError(f"CRC check failed after 10 retries reading register 0x{offset:02X}")

    def write_register(self, offset, start_conversion=False):
        """Write the cached register value to the device. Retries until CRC is valid."""
        reg_val = self.registers[offset]
        frame = (offset << 24) | (reg_val << 8)
        if start_conversion:
            frame |= START_CONVERSION
        frame |= self.generate_crc(frame)

        for _ in range(10):
            received = self.exchange_frame(frame)
            if self.check_crc(received):
                return
        raise RuntimeError(f"CRC check failed after 10 retries writing register 0x{offset:02X}")

    def init(self):
        """Initialize the sensor. Returns the detected version."""
        # Read AFE_STATUS twice; CFG_RESET bit should clear by second read
        self.read_register(AFE_STATUS)
        afe = self.read_register(AFE_STATUS)
        if afe & 0x8000:
            self.version = VERSION_ERROR
            return self.version

        test = self.read_register(TEST_CONFIG)
        ver_bits = (test & 0x0030) >> 4

        if ver_bits == 0x0:
            self.version = VERSION_A1
            self.magnetic_coeff = [50.0 / 32768.0] * 3
        elif ver_bits == 0x1:
            self.version = VERSION_A2
            self.magnetic_coeff = [150.0 / 32768.0] * 3
        else:
            self.version = VERSION_ERROR
            self.magnetic_coeff = [0.0, 0.0, 0.0]

        return self.version

    def set_operating_mode(self, mode):
        self.registers[DEVICE_CONFIG] = (self.registers[DEVICE_CONFIG] & ~OPERATING_MODE_MASK) | mode
        self.write_register(DEVICE_CONFIG)

    def set_conversion_average(self, avg):
        self.registers[DEVICE_CONFIG] = (self.registers[DEVICE_CONFIG] & ~CONV_AVG_MASK) | avg
        self.write_register(DEVICE_CONFIG)

    def enable_magnetic_channel(self, x=True, y=True, z=True):
        val = self.registers[SENSOR_CONFIG] & ~MAG_CH_EN_MASK
        if x:
            val |= 0x0040
        if y:
            val |= 0x0080
        if z:
            val |= 0x0100
        self.registers[SENSOR_CONFIG] = val
        self.write_register(SENSOR_CONFIG)

    def set_magnetic_range(self, x_range, y_range, z_range):
        self.registers[SENSOR_CONFIG] &= ~(X_RANGE_MASK | Y_RANGE_MASK | Z_RANGE_MASK)
        self.registers[SENSOR_CONFIG] |= x_range | y_range | z_range
        self.write_register(SENSOR_CONFIG)

        # Update coefficients based on range and version
        for i, rng in enumerate([x_range & X_RANGE_MASK,
                                  (y_range & Y_RANGE_MASK) >> 2,
                                  (z_range & Z_RANGE_MASK) >> 4]):
            key = (self.version, rng)
            if key in _RANGE_COEFF:
                self.magnetic_coeff[i] = _RANGE_COEFF[key] / 32768.0

    def enable_alert_output(self, enable=True):
        if enable:
            self.registers[ALERT_CONFIG] |= RSLT_ALRT_Asserted
        else:
            self.registers[ALERT_CONFIG] &= ~RSLT_ALRT_Asserted
        self.write_register(ALERT_CONFIG)

    def enable_temperature_channel(self, enable=True):
        """Enable the on-chip temperature sensor (T_RATE = same as other channels)."""
        if enable:
            self.registers[DEVICE_CONFIG] = (
                (self.registers[DEVICE_CONFIG] & ~T_CH_EN_MASK) | T_CH_EN_ENABLED
            )
        else:
            self.registers[DEVICE_CONFIG] &= ~T_CH_EN_MASK
        self.write_register(DEVICE_CONFIG)

    def read_temperature(self):
        """Read die temperature in °C using the datasheet conversion formula."""
        raw = self.read_register(TEMP_RESULT)
        return _TEMP_TSENS_T0 + (raw - _TEMP_TADC_T0) / _TEMP_TADC_RES

    def _read_axis_raw(self, reg, start_conversion=False):
        val = self.read_register(reg, start_conversion)
        return struct.unpack('>h', struct.pack('>H', val))[0]

    def _read_axis_mt(self, reg, coeff_idx, start_conversion=False):
        raw = self._read_axis_raw(reg, start_conversion)
        return raw * self.magnetic_coeff[coeff_idx]

    def read_x(self, start_conversion=False):
        """Read X-axis magnetic field in mT."""
        return self._read_axis_mt(X_CH_RESULT, 0, start_conversion)

    def read_y(self, start_conversion=False):
        """Read Y-axis magnetic field in mT."""
        return self._read_axis_mt(Y_CH_RESULT, 1, start_conversion)

    def read_z(self, start_conversion=False):
        """Read Z-axis magnetic field in mT."""
        return self._read_axis_mt(Z_CH_RESULT, 2, start_conversion)

    def read_xyz(self):
        """Read all three axes. Triggers a new conversion on the last read."""
        x = self.read_x()
        y = self.read_y()
        z = self.read_z(start_conversion=True)
        return x, y, z