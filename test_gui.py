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
import queue
import math
import base64
from collections import deque
from tmag5170 import (
    TMAG5170,
    CONV_AVG_1x, CONV_AVG_2x, CONV_AVG_4x, CONV_AVG_8x, CONV_AVG_16x, CONV_AVG_32x,
    X_RANGE_50mT, X_RANGE_25mT, X_RANGE_100mT,
    Y_RANGE_50mT, Y_RANGE_25mT, Y_RANGE_100mT,
    Z_RANGE_50mT, Z_RANGE_25mT, Z_RANGE_100mT,
    X_RANGE_150mT, X_RANGE_75mT, X_RANGE_300mT,
    Y_RANGE_150mT, Y_RANGE_75mT, Y_RANGE_300mT,
    Z_RANGE_150mT, Z_RANGE_75mT, Z_RANGE_300mT,
    VERSION_A1, VERSION_A2, VERSION_ERROR,
)

_ICON_B64 = (
    "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"
    "AAAAAElFTkSuQmCC"
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
    """Background thread that continuously reads the sensor.

    Commands sent via set_* methods are queued and applied between samples.
    """

    # Default range codes for A2 (300 mT full scale)
    _DEFAULT_AVG = CONV_AVG_32x
    _DEFAULT_RANGE_A1 = (X_RANGE_100mT, Y_RANGE_100mT, Z_RANGE_100mT)
    _DEFAULT_RANGE_A2 = (X_RANGE_300mT, Y_RANGE_300mT, Z_RANGE_300mT)

    def __init__(self, bus=0, device=0, speed_hz=1000000):
        super().__init__(daemon=True)
        self.bus = bus
        self.device = device
        self.speed_hz = speed_hz
        self.bx = 0.0
        self.by = 0.0
        self.bz = 0.0
        self.temperature = None   # None until first read
        self.version = VERSION_ERROR
        self.connected = False
        self.error_msg = ""
        self.running = True
        self.sample_interval_s = SAMPLE_INTERVAL_S
        self.lock = threading.Lock()
        self._cmd_queue = queue.Queue()
        self._temp_interval = 1.0   # seconds between temperature reads
        self._last_temp_time = 0.0

    # ---- thread-safe setters called from the GUI ----

    def set_conversion_average(self, avg_const):
        self._cmd_queue.put(("avg", avg_const))

    def set_range(self, x_range, y_range, z_range):
        self._cmd_queue.put(("range", x_range, y_range, z_range))

    def set_sample_interval(self, interval_s):
        self._cmd_queue.put(("interval", interval_s))

    # ---- internal helpers ----

    def _apply_commands(self, sensor):
        while not self._cmd_queue.empty():
            try:
                cmd = self._cmd_queue.get_nowait()
            except queue.Empty:
                break
            if cmd[0] == "avg":
                sensor.set_conversion_average(cmd[1])
            elif cmd[0] == "range":
                sensor.set_magnetic_range(cmd[1], cmd[2], cmd[3])
            elif cmd[0] == "interval":
                with self.lock:
                    self.sample_interval_s = cmd[1]

    def run(self):
        sensor = None
        try:
            sensor = TMAG5170(self.bus, self.device, self.speed_hz)
            sensor.open()
            version = sensor.init()
            if version == VERSION_ERROR:
                with self.lock:
                    self.error_msg = "Sensor init failed - check wiring"
                return

            default_range = (self._DEFAULT_RANGE_A1 if version == VERSION_A1
                             else self._DEFAULT_RANGE_A2)
            sensor.set_conversion_average(self._DEFAULT_AVG)
            sensor.enable_magnetic_channel(x=True, y=True, z=True)
            sensor.set_magnetic_range(*default_range)
            sensor.enable_temperature_channel(True)

            with self.lock:
                self.connected = True
                self.version = version
                version_names = {VERSION_A1: "A1", VERSION_A2: "A2"}
                self.error_msg = f"Connected (TMAG5170-{version_names.get(version, '?')})"

            while self.running:
                self._apply_commands(sensor)
                bx, by, bz = sensor.read_xyz()

                now = time.monotonic()
                temp = None
                if now - self._last_temp_time >= self._temp_interval:
                    temp = sensor.read_temperature()
                    self._last_temp_time = now

                with self.lock:
                    self.bx, self.by, self.bz = bx, by, bz
                    if temp is not None:
                        self.temperature = temp
                    interval = self.sample_interval_s

                time.sleep(interval)

        except Exception as e:
            with self.lock:
                self.error_msg = str(e) or f"Error: {type(e).__name__}"
                self.connected = False
        finally:
            if sensor is not None:
                try:
                    sensor.close()
                except Exception:
                    pass

    def get_values(self):
        with self.lock:
            return (self.bx, self.by, self.bz,
                    self.temperature, self.version,
                    self.connected, self.error_msg)

    def stop(self):
        self.running = False


class TMAG5170App:
    # Conversion averaging options: label -> driver constant
    _AVG_OPTIONS = {
        "1x":  CONV_AVG_1x,
        "2x":  CONV_AVG_2x,
        "4x":  CONV_AVG_4x,
        "8x":  CONV_AVG_8x,
        "16x": CONV_AVG_16x,
        "32x": CONV_AVG_32x,
    }

    # Range options per version: label -> (x_range, y_range, z_range)
    _RANGE_OPTIONS_A1 = {
        "25 mT":  (X_RANGE_25mT,  Y_RANGE_25mT,  Z_RANGE_25mT),
        "50 mT":  (X_RANGE_50mT,  Y_RANGE_50mT,  Z_RANGE_50mT),
        "100 mT": (X_RANGE_100mT, Y_RANGE_100mT, Z_RANGE_100mT),
    }
    _RANGE_OPTIONS_A2 = {
        "75 mT":  (X_RANGE_75mT,  Y_RANGE_75mT,  Z_RANGE_75mT),
        "150 mT": (X_RANGE_150mT, Y_RANGE_150mT, Z_RANGE_150mT),
        "300 mT": (X_RANGE_300mT, Y_RANGE_300mT, Z_RANGE_300mT),
    }

    # Refresh rate options: label -> sample interval in seconds
    _RATE_OPTIONS = {
        "1 Hz":   1.0,
        "2 Hz":   0.5,
        "5 Hz":   0.2,
        "10 Hz":  0.1,
        "20 Hz":  0.05,
        "50 Hz":  0.02,
        "100 Hz": 0.01,
    }

    def __init__(self, root):
        self.root = root
        self.root.title("TMAG5170 Magnetic Field Monitor")
        self.root.configure(bg=WINDOW_BG)
        self.root.geometry("1000x520")
        self.root.minsize(700, 400)

        self.history_x = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.history_y = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.history_z = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.max_range = 50.0
        self._current_b = (0.0, 0.0, 0.0)

        # Track detected version so range options can be populated after connect
        self._version_populated = False

        # Calibration state
        self._calibrating = False
        self._cal_samples = []
        self._cal_target_samples = 100
        self._offset = (0.0, 0.0, 0.0)

        self._build_ui()
        self.sensor_thread = SensorThread()
        self.sensor_thread.start()
        self._update()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ---- Status bar (top) ----
        self.status_var = tk.StringVar(value="Connecting...")
        status = tk.Label(self.root, textvariable=self.status_var,
                        bg=WINDOW_BG, fg=LABEL_FG,
                        font=("Consolas", 10), anchor="w")
        status.pack(fill="x", padx=10, pady=(8, 0))

        # ---- Main horizontal container ----
        content_frame = tk.Frame(self.root, bg=WINDOW_BG)
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ---- LEFT SIDE (create FIRST) ----
        left_frame = tk.Frame(content_frame, bg=WINDOW_BG)
        left_frame.pack(side="left", fill="both", expand=True)

        # ---- Value display (NOW it's safe to use left_frame) ----
        val_frame = tk.Frame(left_frame, bg=WINDOW_BG)
        val_frame.pack(fill="x", pady=8)

        self.value_labels = {}
        for i, (axis, color) in enumerate(COLORS.items()):
            lbl = tk.Label(val_frame, text=f"B{axis.upper()}:",
                        bg=WINDOW_BG, fg=color,
                        font=("Consolas", 14, "bold"))
            lbl.grid(row=0, column=i * 2, padx=(0, 4))

            val = tk.Label(val_frame, text="  0.000 mT",
                        bg=WINDOW_BG, fg=TEXT_FG,
                        font=("Consolas", 14),
                        width=12, anchor="e")
            val.grid(row=0, column=i * 2 + 1, padx=(0, 20))
            self.value_labels[axis] = val

        # ---- Plot canvas ----
        self.canvas = tk.Canvas(left_frame, bg=PLOT_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # ---- RIGHT PANEL ----
        self._build_control_panel(content_frame)

    def _build_control_panel(self, parent):
        panel = tk.Frame(parent, bg=WINDOW_BG, width=180)
        panel.pack(side="right", fill="y", padx=(8, 0))
        panel.pack_propagate(False)

        def section(text):
            tk.Label(panel, text=text, bg=WINDOW_BG, fg=LABEL_FG,
                     font=("Consolas", 9, "bold")).pack(anchor="w", pady=(10, 2))

        # ---- Calibrate ----
        section("CALIBRATE")
        calibrate_button = tk.Button(panel, text="Calibrate", bg=WINDOW_BG, fg=TEXT_FG,
                             font=("Consolas", 9), relief="raised", bd=1, command=self._calibrate_zero_field)
        calibrate_button.pack(anchor="w")

        # ---- Temperature ----
        section("TEMPERATURE")
        temp_row = tk.Frame(panel, bg=WINDOW_BG)
        temp_row.pack(anchor="w")
        tk.Label(temp_row, text="Die: ", bg=WINDOW_BG, fg=LABEL_FG,
                 font=("Consolas", 9)).pack(side="left")
        self.temp_label = tk.Label(temp_row, text="-- °C", bg=WINDOW_BG, fg=TEXT_FG,
                                   font=("Consolas", 11, "bold"), width=9, anchor="e")
        self.temp_label.pack(side="left")

        # ---- Sensitivity (range) ----
        section("SENSITIVITY")
        self.range_var = tk.StringVar(value="300 mT")
        self.range_combo = ttk.Combobox(panel, textvariable=self.range_var,
                                        state="disabled", width=10,
                                        font=("Consolas", 9))
        self.range_combo.pack(anchor="w")
        self.range_combo.bind("<<ComboboxSelected>>", self._on_range_changed)

        # ---- Conversion averaging ----
        section("CONV AVERAGING")
        self.avg_var = tk.StringVar(value="32x")
        avg_combo = ttk.Combobox(panel, textvariable=self.avg_var,
                                 values=list(self._AVG_OPTIONS.keys()),
                                 state="readonly", width=10,
                                 font=("Consolas", 9))
        avg_combo.pack(anchor="w")
        avg_combo.bind("<<ComboboxSelected>>", self._on_avg_changed)

        # ---- Refresh rate ----
        section("REFRESH RATE")
        self.rate_var = tk.StringVar(value="20 Hz")
        rate_combo = ttk.Combobox(panel, textvariable=self.rate_var,
                                  values=list(self._RATE_OPTIONS.keys()),
                                  state="readonly", width=10,
                                  font=("Consolas", 9))
        rate_combo.pack(anchor="w")
        rate_combo.bind("<<ComboboxSelected>>", self._on_rate_changed)

        # ---- Vector display ----
        section("FIELD VECTOR")
        self.vec_canvas = tk.Canvas(panel, bg=PLOT_BG, highlightthickness=0,
                                    width=160, height=150)
        self.vec_canvas.pack(anchor="w", pady=(2, 6))

    # ------------------------------------------------------------------
    # Control callbacks
    # ------------------------------------------------------------------

    def _on_range_changed(self, _=None):
        version = self.sensor_thread.version
        options = (self._RANGE_OPTIONS_A1 if version == VERSION_A1
                   else self._RANGE_OPTIONS_A2)
        key = self.range_var.get()
        if key in options:
            self.sensor_thread.set_range(*options[key])

    def _on_avg_changed(self, _=None):
        key = self.avg_var.get()
        if key in self._AVG_OPTIONS:
            self.sensor_thread.set_conversion_average(self._AVG_OPTIONS[key])

    def _on_rate_changed(self, _=None):
        key = self.rate_var.get()
        if key in self._RATE_OPTIONS:
            self.sensor_thread.set_sample_interval(self._RATE_OPTIONS[key])

    # ------------------------------------------------------------------
    # Calibration logic
    # ------------------------------------------------------------------

    def _calibrate_zero_field(self):
        """Start collecting samples to compute zero-field offset."""
        if self._calibrating:
            return  # already running

        self._calibrating = True
        self._cal_samples = []
        self.status_var.set("Calibrating... keep sensor still")


    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------

    def _update(self):
        bx, by, bz, temperature, version, connected, msg = self.sensor_thread.get_values()

        # Apply calibration logic
        if self._calibrating:
            self._cal_samples.append((bx, by, bz))

            n = len(self._cal_samples)
            total = self._cal_target_samples

            # Live progress feedback
            self.status_var.set(f"Calibrating... {n}/{total} (keep sensor still)")
            self.calibrate_button.config(text=f"Calibrating... {n}/{total}",bg="#ff0000",fg="#000000")

            if n >= total:
                avg_x = sum(s[0] for s in self._cal_samples) / n
                avg_y = sum(s[1] for s in self._cal_samples) / n
                avg_z = sum(s[2] for s in self._cal_samples) / n

                self._offset = (avg_x, avg_y, avg_z)
                self._calibrating = False
                self.status_var.set("Calibration complete")
                self.calibrate_button.config(text="Calibrate",bg=WINDOW_BG,fg=TEXT_FG)

        self.status_var.set(msg if msg else "Connecting...")

        if connected:
            # Populate range dropdown once version is known
            if not self._version_populated:
                options = (self._RANGE_OPTIONS_A1 if version == VERSION_A1
                           else self._RANGE_OPTIONS_A2)
                keys = list(options.keys())
                self.range_combo.config(values=keys, state="readonly")
                # Select the highest range as default
                default = keys[-1]
                self.range_var.set(default)
                self._version_populated = True

            # Subtract offset
            bx_corr = bx - self._offset[0]
            by_corr = by - self._offset[1]
            bz_corr = bz - self._offset[2]

            self.history_x.append(bx_corr)
            self.history_y.append(by_corr)
            self.history_z.append(bz_corr)
            self._current_b = (bx_corr, by_corr, bz_corr)

            self.value_labels["x"].config(text=f"{bx_corr:>8.3f} mT")
            self.value_labels["y"].config(text=f"{by_corr:>8.3f} mT")
            self.value_labels["z"].config(text=f"{bz_corr:>8.3f} mT")

            if temperature is not None:
                self.temp_label.config(text=f"{temperature:>5.1f} °C")

            self._draw_plot()
            self._draw_vector()

        self.root.after(UPDATE_INTERVAL_MS, self._update)

    # ------------------------------------------------------------------
    # Plot rendering
    # ------------------------------------------------------------------

    def _draw_plot(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        margin_l, margin_r, margin_t, margin_b = 60, 10, 10, 25
        pw = w - margin_l - margin_r
        ph = h - margin_t - margin_b

        all_vals = list(self.history_x) + list(self.history_y) + list(self.history_z)
        peak = max(abs(v) for v in all_vals) if all_vals else 1.0
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

        num_gridlines = 5
        for i in range(num_gridlines + 1):
            frac = i / num_gridlines
            val = y_range * (1 - 2 * frac)
            y = margin_t + frac * ph
            self.canvas.create_line(margin_l, y, w - margin_r, y, fill="#444444", dash=(2, 4))
            self.canvas.create_text(margin_l - 5, y, text=f"{val:+.1f}", anchor="e",
                                    fill=LABEL_FG, font=("Consolas", 8))

        y0 = val_to_y(0)
        self.canvas.create_line(margin_l, y0, w - margin_r, y0, fill="#666666")

        self.canvas.create_text(10, h / 2, text="mT", anchor="w",
                                fill=LABEL_FG, font=("Consolas", 9))

        for data, color in [(self.history_x, COLORS["x"]),
                             (self.history_y, COLORS["y"]),
                             (self.history_z, COLORS["z"])]:
            points = []
            for i, val in enumerate(data):
                points.append(idx_to_x(i))
                points.append(val_to_y(val))
            if len(points) >= 4:
                self.canvas.create_line(points, fill=color, width=2, smooth=True)

        lx = w - margin_r - 100
        for i, (axis, color) in enumerate(COLORS.items()):
            ly = margin_t + 5 + i * 16
            self.canvas.create_line(lx, ly + 6, lx + 20, ly + 6, fill=color, width=2)
            self.canvas.create_text(lx + 25, ly + 6, text=f"B{axis.upper()}", anchor="w",
                                    fill=color, font=("Consolas", 9, "bold"))


    def _draw_vector(self):
        """Draw an isometric 3-D vector indicator on the side-panel canvas."""
        vc = self.vec_canvas
        vc.delete("all")
        w = vc.winfo_width()
        h = vc.winfo_height()
        if w < 10 or h < 10:
            return

        # Reserve bottom strip for magnitude label
        LABEL_H = 14
        SIZE = min(w, h - LABEL_H)
        cx = w / 2
        cy = (h - LABEL_H) / 2

        # Standard isometric projection:
        #   X  → right-down  ( cos30,  sin30)
        #   Y  → left-down   (-cos30,  sin30)
        #   Z  → straight up (0, -1)
        s = SIZE / 2
        c30 = math.sqrt(3) / 2
        s30 = 0.5

        def iso(x3, y3, z3):
            px = (x3 * c30 - y3 * c30) * s
            py = (x3 * s30 + y3 * s30 - z3) * s
            return cx + px, cy + py

        origin = iso(0, 0, 0)
        axis_len = 0.55

        # Unit-cube wireframe
        for p1, p2 in [
            (iso(0,0,0), iso(1,0,0)), (iso(0,0,0), iso(0,1,0)), (iso(0,0,0), iso(0,0,1)),
            (iso(1,0,0), iso(1,1,0)), (iso(0,1,0), iso(1,1,0)),
            (iso(1,0,0), iso(1,0,1)), (iso(0,0,1), iso(1,0,1)),
            (iso(0,1,0), iso(0,1,1)), (iso(0,0,1), iso(0,1,1)),
            (iso(1,1,0), iso(1,1,1)), (iso(1,0,1), iso(1,1,1)), (iso(0,1,1), iso(1,1,1)),
        ]:
            vc.create_line(p1[0], p1[1], p2[0], p2[1], fill="#2a2a2a", width=1)

        # Coordinate axes + labels
        for axis, tip3 in [("x", (axis_len,0,0)), ("y", (0,axis_len,0)), ("z", (0,0,axis_len))]:
            tip = iso(*tip3)
            color = COLORS[axis]
            vc.create_line(origin[0], origin[1], tip[0], tip[1], fill=color, width=2)
            dx, dy = tip[0] - origin[0], tip[1] - origin[1]
            n = math.hypot(dx, dy) or 1
            vc.create_text(tip[0] + dx/n*8, tip[1] + dy/n*8,
                           text=axis.upper(), fill=color, font=("Consolas", 7, "bold"))

        # Scale B vector so the longest component equals axis_len
        bx, by, bz = self._current_b
        mag = math.sqrt(bx**2 + by**2 + bz**2)
        peak = max(abs(bx), abs(by), abs(bz), 1e-9)
        scale = axis_len / peak
        vx, vy, vz = bx * scale, by * scale, bz * scale
        tip_v = iso(vx, vy, vz)

        # Dashed projections onto the three axis planes
        for proj in (iso(vx, vy, 0), iso(vx, 0, vz), iso(0, vy, vz)):
            vc.create_line(tip_v[0], tip_v[1], proj[0], proj[1],
                           fill="#555555", dash=(2, 3), width=1)

        # Arrow shaft
        vc.create_line(origin[0], origin[1], tip_v[0], tip_v[1], fill="#ffffff", width=2)

        # Arrowhead
        dx, dy = tip_v[0] - origin[0], tip_v[1] - origin[1]
        n = math.hypot(dx, dy) or 1
        ux, uy = dx/n, dy/n
        px, py = -uy, ux
        ah, aw = 7, 3
        vc.create_polygon([
            tip_v[0], tip_v[1],
            tip_v[0] - ux*ah + px*aw, tip_v[1] - uy*ah + py*aw,
            tip_v[0] - ux*ah - px*aw, tip_v[1] - uy*ah - py*aw,
        ], fill="#ffffff", outline="")

        # Magnitude label
        vc.create_text(cx, h - LABEL_H + 2, text=f"|B| {mag:.1f} mT",
                       fill=LABEL_FG, font=("Consolas", 8), anchor="n")

    def on_close(self):
        self.sensor_thread.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root._icon = tk.PhotoImage(data=base64.b64decode(_ICON_B64))
        root.iconphoto(True, root._icon)
    except Exception:
        pass
    app = TMAG5170App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
