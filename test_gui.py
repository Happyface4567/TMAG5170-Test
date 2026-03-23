"""
Tkinter GUI for live TMAG5170 magnetic field visualization on Raspberry Pi.

Shows real-time X, Y, Z magnetic field values with bar indicators
and a scrolling time-series plot.

Usage: python test_gui.py
"""

import tkinter as tk
from tkinter import ttk
import time
import threading
import sys
import os
from collections import deque
from tmag5170 import (
    TMAG5170, CONV_AVG_32x,
    X_RANGE_300mT, Y_RANGE_300mT, Z_RANGE_300mT,
    VERSION_A1, VERSION_A2, VERSION_ERROR,
)

HISTORY_LEN = 200
UPDATE_INTERVAL_MS = 100  # GUI refresh rate
SAMPLE_INTERVAL_S = 0.05  # sensor polling rate

COLORS = {"x": "#e74c3c", "y": "#2ecc71", "z": "#3498db"}
PLOT_BG = "#1e1e1e"
WINDOW_BG = "#2d2d2d"
TEXT_FG = "#ecf0f1"
LABEL_FG = "#95a5a6"


class SensorThread(threading.Thread):
    """Background thread that continuously reads the sensor."""

    def __init__(self, bus=0, device=0, speed_hz=1000000):
        super().__init__(daemon=True)
        self.bus = bus
        self.device = device
        self.speed_hz = speed_hz
        self.bx = 0.0
        self.by = 0.0
        self.bz = 0.0
        self.connected = False
        self.error_msg = ""
        self.running = True
        self.lock = threading.Lock()

    def run(self):
        sensor = TMAG5170(self.bus, self.device, self.speed_hz)
        try:
            sensor.open()
            version = sensor.init()
            if version == VERSION_ERROR:
                with self.lock:
                    self.error_msg = "Sensor init failed - check wiring"
                return

            sensor.set_conversion_average(CONV_AVG_32x)
            sensor.enable_magnetic_channel(x=True, y=True, z=True)
            sensor.set_magnetic_range(X_RANGE_300mT, Y_RANGE_300mT, Z_RANGE_300mT)

            with self.lock:
                self.connected = True
                version_names = {VERSION_A1: "A1", VERSION_A2: "A2"}
                self.error_msg = f"Connected (TMAG5170-{version_names.get(version, '?')})"

            while self.running:
                bx, by, bz = sensor.read_xyz()
                with self.lock:
                    self.bx, self.by, self.bz = bx, by, bz
                time.sleep(SAMPLE_INTERVAL_S)

        except Exception as e:
            with self.lock:
                self.error_msg = str(e)
                self.connected = False
        finally:
            try:
                sensor.close()
            except Exception:
                pass

    def get_values(self):
        with self.lock:
            return self.bx, self.by, self.bz, self.connected, self.error_msg

    def stop(self):
        self.running = False


class TMAG5170App:
    def __init__(self, root):
        self.root = root
        self.root.title("TMAG5170 Magnetic Field Monitor")
        self.root.configure(bg=WINDOW_BG)
        self.root.geometry("800x520")
        self.root.minsize(600, 400)

        self.history_x = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.history_y = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.history_z = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.max_range = 50.0  # auto-scales

        self._build_ui()
        self.sensor_thread = SensorThread()
        self.sensor_thread.start()
        self._update()

    def _build_ui(self):
        # Status bar
        self.status_var = tk.StringVar(value="Connecting...")
        status = tk.Label(self.root, textvariable=self.status_var, bg=WINDOW_BG,
                          fg=LABEL_FG, font=("Consolas", 10), anchor="w")
        status.pack(fill="x", padx=10, pady=(8, 0))

        # Value display frame
        val_frame = tk.Frame(self.root, bg=WINDOW_BG)
        val_frame.pack(fill="x", padx=10, pady=8)

        self.value_labels = {}
        for i, (axis, color) in enumerate(COLORS.items()):
            lbl = tk.Label(val_frame, text=f"B{axis.upper()}:", bg=WINDOW_BG,
                           fg=color, font=("Consolas", 14, "bold"))
            lbl.grid(row=0, column=i * 2, padx=(0, 4))

            val = tk.Label(val_frame, text="  0.000 mT", bg=WINDOW_BG,
                           fg=TEXT_FG, font=("Consolas", 14), width=12, anchor="e")
            val.grid(row=0, column=i * 2 + 1, padx=(0, 20))
            self.value_labels[axis] = val

        val_frame.columnconfigure(5, weight=1)

        # Canvas for the plot
        self.canvas = tk.Canvas(self.root, bg=PLOT_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _update(self):
        bx, by, bz, connected, msg = self.sensor_thread.get_values()
        self.status_var.set(msg if msg else "Connecting...")

        if connected:
            self.history_x.append(bx)
            self.history_y.append(by)
            self.history_z.append(bz)

            self.value_labels["x"].config(text=f"{bx:>8.3f} mT")
            self.value_labels["y"].config(text=f"{by:>8.3f} mT")
            self.value_labels["z"].config(text=f"{bz:>8.3f} mT")

            self._draw_plot()

        self.root.after(UPDATE_INTERVAL_MS, self._update)

    def _draw_plot(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        margin_l, margin_r, margin_t, margin_b = 60, 10, 10, 25
        pw = w - margin_l - margin_r
        ph = h - margin_t - margin_b

        # Auto-scale Y axis
        all_vals = list(self.history_x) + list(self.history_y) + list(self.history_z)
        peak = max(abs(v) for v in all_vals) if all_vals else 1.0
        # Smooth scale changes
        target = max(peak * 1.2, 1.0)
        if target > self.max_range:
            self.max_range = target
        else:
            self.max_range += (target - self.max_range) * 0.05

        y_range = self.max_range

        def val_to_y(val):
            return margin_t + ph / 2 - (val / y_range) * (ph / 2)

        def idx_to_x(idx):
            return margin_l + (idx / (HISTORY_LEN - 1)) * pw

        # Grid lines
        num_gridlines = 5
        for i in range(num_gridlines + 1):
            frac = i / num_gridlines
            val = y_range * (1 - 2 * frac)
            y = margin_t + frac * ph
            self.canvas.create_line(margin_l, y, w - margin_r, y, fill="#444444", dash=(2, 4))
            self.canvas.create_text(margin_l - 5, y, text=f"{val:+.1f}", anchor="e",
                                    fill=LABEL_FG, font=("Consolas", 8))

        # Zero line
        y0 = val_to_y(0)
        self.canvas.create_line(margin_l, y0, w - margin_r, y0, fill="#666666")

        # Axis label
        self.canvas.create_text(10, h / 2, text="mT", anchor="w",
                                fill=LABEL_FG, font=("Consolas", 9))

        # Plot traces
        for data, color in [(self.history_x, COLORS["x"]),
                             (self.history_y, COLORS["y"]),
                             (self.history_z, COLORS["z"])]:
            points = []
            for i, val in enumerate(data):
                points.append(idx_to_x(i))
                points.append(val_to_y(val))
            if len(points) >= 4:
                self.canvas.create_line(points, fill=color, width=2, smooth=True)

        # Legend
        lx = w - margin_r - 100
        for i, (axis, color) in enumerate(COLORS.items()):
            ly = margin_t + 5 + i * 16
            self.canvas.create_line(lx, ly + 6, lx + 20, ly + 6, fill=color, width=2)
            self.canvas.create_text(lx + 25, ly + 6, text=f"B{axis.upper()}", anchor="w",
                                    fill=color, font=("Consolas", 9, "bold"))

    def on_close(self):
        self.sensor_thread.stop()
        self.root.destroy()


def _resource_path(filename):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def main():
    root = tk.Tk()
    try:
        icon = tk.PhotoImage(file=_resource_path("Magnet-Icon.png"))
        root.iconphoto(True, icon)
    except Exception:
        pass
    app = TMAG5170App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
