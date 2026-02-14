"""
Traffic-Mind – Arduino Serial Bridge
Manages Python ↔ Arduino communication for physical LEDs & IR sensors.
"""

import time


class ArduinoBridge:
    """
    Serial link to Arduino traffic-light hardware.

    Protocol (Python → Arduino):
        '0'  = Phase NS Green, EW Red
        '1'  = Phase EW Green, NS Red
        '2'  = All Yellow
        '3'  = All Red
        '9'  = Request sensor data

    Arduino → Python (on request '9'):
        "N:{val},S:{val},E:{val},W:{val}\\n"
    """

    def __init__(self, port: str, baud_rate: int = 9600):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_conn = None
        self.hardware_available = False
        self.hardware_enabled = False

        try:
            import serial
            self.serial_conn = serial.Serial(port, baud_rate, timeout=1)
            time.sleep(2)  # wait for Arduino reset
            self.hardware_available = True
            self.hardware_enabled = True
            print(f"✅ Arduino connected on {port}")
        except Exception as e:
            print(f"⚠️  Arduino not available ({e}). Running software-only.")

    # ── send phase ────────────────────────
    def send_phase(self, phase_id: int):
        if not self.hardware_available or self.serial_conn is None:
            return
        try:
            self.serial_conn.write(str(phase_id).encode())
            time.sleep(0.05)
        except Exception:
            self._handle_disconnect()

    # ── read IR sensors ───────────────────
    def read_sensors(self) -> dict | None:
        if not self.hardware_available or self.serial_conn is None:
            return None
        try:
            self.serial_conn.write(b"9")
            time.sleep(0.1)
            line = self.serial_conn.readline().decode().strip()
            if not line:
                return None
            # Parse "N:5,S:3,E:8,W:2"
            result = {}
            for part in line.split(","):
                key, val = part.split(":")
                mapping = {"N": 0, "S": 1, "E": 2, "W": 3}
                if key in mapping:
                    result[mapping[key]] = int(val)
            return result
        except Exception:
            return None

    # ── sync with simulation ──────────────
    def sync_with_simulation(self, lights: dict):
        """Map current traffic-light states to Arduino phase command."""
        if not self.hardware_enabled:
            return
        from simulation.traffic_light import TrafficLightState
        from config.settings import Direction

        ns_green = lights[Direction.NORTH].is_green()
        ew_green = lights[Direction.EAST].is_green()
        ns_yellow = lights[Direction.NORTH].is_yellow()

        if ns_yellow or lights[Direction.EAST].is_yellow():
            self.send_phase(2)
        elif ns_green:
            self.send_phase(0)
        elif ew_green:
            self.send_phase(1)
        else:
            self.send_phase(3)

    # ── connection helpers ────────────────
    def _handle_disconnect(self):
        print("⚠️  Arduino disconnected.")
        self.hardware_available = False
        try:
            if self.serial_conn:
                self.serial_conn.close()
        except Exception:
            pass
        self.serial_conn = None

    def is_connected(self) -> bool:
        return self.hardware_available and self.serial_conn is not None

    def close(self):
        if self.serial_conn:
            try:
                self.send_phase(3)  # all red on exit
                self.serial_conn.close()
            except Exception:
                pass
            print("Arduino connection closed.")
