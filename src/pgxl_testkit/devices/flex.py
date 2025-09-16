from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
import socket, time

@dataclass
class FlexRadio:
    host: str
    port: int = 4992
    _sock: Optional[socket.socket] = None
    _seq: int = 0
    _rxbuf: str = ""
    _connected: bool = False
    _last_band_persistence: Optional[bool] = None

    # ---------- connection ----------
    def connect(self, timeout: float = 5.0, prime_window: float = 0.6, subscribe: bool = True) -> None:
        """Open TCP, absorb the initial S-dump, optionally subscribe for radio updates."""
        self._sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self._sock.settimeout(0.1)
        self._seq = 0
        self._rxbuf = ""
        self._connected = True
        self._prime_after_connect(prime_window)
        if subscribe:
            try:
                self._send_counted("sub radio all", expect_response=True, timeout=1.0)
            except Exception:
                pass
            # brief read to catch a fresh radio line (may include band_persistence_enabled)
            end = time.time() + 0.25
            while time.time() < end:
                self._scan_for_band_persistence(self._read_lines())
                time.sleep(0.01)

    def _prime_after_connect(self, prime_window: float) -> None:
        if not self._sock:
            return
        deadline = time.time() + prime_window
        while time.time() < deadline:
            lines = self._read_lines()
            if lines:
                self._scan_for_band_persistence(lines)
            else:
                time.sleep(0.02)

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None
        self._connected = False
        self._rxbuf = ""

    # ---------- low-level counted I/O ----------
    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _read_lines(self) -> List[str]:
        if not self._sock:
            return []
        try:
            chunk = self._sock.recv(4096)
            if not chunk:
                return []
            self._rxbuf += chunk.decode("utf-8", errors="ignore")
        except socket.timeout:
            pass
        except Exception:
            return []
        lines: List[str] = []
        while "\n" in self._rxbuf:
            line, self._rxbuf = self._rxbuf.split("\n", 1)
            lines.append(line.strip())
        return lines

    def _send_counted(self, body: str, expect_response: bool = True, timeout: float = 1.5) -> Optional[str]:
        if not (self._connected and self._sock):
            raise RuntimeError("FlexRadio is not connected.")
        seq = self._next_seq()
        wire = f"C{seq}|{body}\n"
        self._sock.sendall(wire.encode("utf-8"))
        if not expect_response:
            return None

        want = f"R{seq}|"
        deadline = time.time() + timeout

        for line in self._read_lines():
            if line.startswith(want):
                return line

        while time.time() < deadline:
            for line in self._read_lines():
                if line.startswith(want):
                    return line
            time.sleep(0.01)
        raise TimeoutError(f"No response for sequence {seq} (body='{body}')")

    # ---------- helpers ----------
    @staticmethod
    def _mhz(f: float) -> str:
        return f"{f:.6f}"

    @staticmethod
    def _band_center_mhz(band_m: int) -> float:
        centers = {
            160: 1.900, 80: 3.750, 60: 5.358, 40: 7.150, 30: 10.125,
            20: 14.175, 17: 18.118, 15: 21.225, 12: 24.940, 10: 28.850, 6: 50.500
        }
        if band_m not in centers:
            raise ValueError(f"Unsupported band: {band_m} m")
        return centers[band_m]

    # ---------- band persistence ----------
    def _scan_for_band_persistence(self, lines: List[str]) -> None:
        for line in lines:
            if "band_persistence_enabled=" in line:
                try:
                    val = line.split("band_persistence_enabled=", 1)[1].split()[0]
                    self._last_band_persistence = (val.strip() in ("1", "true", "True"))
                except Exception:
                    pass

    def get_band_persistence_cached(self) -> Optional[bool]:
        """Return last-seen band persistence state (None if not yet reported)."""
        return self._last_band_persistence

    def set_band_persistence(self, enabled: bool) -> None:
        self._send_counted(f"radio set band_persistence_enabled={1 if enabled else 0}", expect_response=False)
        self._last_band_persistence = bool(enabled)

    # ---------- high-level API ----------
    def set_mode(self, mode: str) -> None:
        m = mode.strip().upper()
        self._send_counted(f"slice s 0 mode={m}")

    def set_frequency_mhz(self, f_mhz: float) -> None:
        self._send_counted("slice s 0 tx=1", expect_response=False)
        self._send_counted(f"slice t 0 {self._mhz(f_mhz)}")

    def set_band(self, band_m: int) -> None:
        ctr = self._band_center_mhz(band_m)
        self.set_frequency_mhz(ctr)

    def set_rf_power_pct(self, pct: int) -> None:
        pct = int(max(0, min(100, pct)))
        self._send_counted(f"transmit set rfpower={pct}", expect_response=False)

    def set_tune_power_pct(self, pct: int) -> None:
        pct = int(max(0, min(100, pct)))
        self._send_counted(f"transmit set tunepower={pct}", expect_response=False)

    def set_drive_w(self, watts: float) -> None:
        pct = int(max(0.0, min(100.0, watts)))
        self.set_rf_power_pct(pct)
        self.set_tune_power_pct(pct)

    def key_carrier_on(self, wait_ack: bool = True) -> Optional[str]:
        return self._send_counted("transmit tune on", expect_response=wait_ack)

    def key_carrier_off(self, wait_ack: bool = True) -> Optional[str]:
        return self._send_counted("transmit tune off", expect_response=wait_ack)

    def set_two_tone(self, enabled: bool) -> None:
        mode = "two_tone" if enabled else "single_tone"
        self._send_counted(f"transmit set tune_mode={mode}", expect_response=False)
