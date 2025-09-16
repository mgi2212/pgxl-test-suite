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

    # ---------- connection ----------
    def connect(self, timeout: float = 5.0) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self._sock.settimeout(0.5)
        self._seq = 0
        self._rxbuf = ""
        self._connected = True
        # optional convenience
        try:
            self._send_counted("radio set band_persistence_enabled=0", expect_response=False)
        except Exception:
            pass

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
        """
        TX: C<n>|{body}\\n
        Wait for: R<n>|...
        Ignores unsolicited S-lines while waiting.
        """
        if not (self._connected and self._sock):
            raise RuntimeError("FlexRadio is not connected.")
        seq = self._next_seq()
        wire = f"C{seq}|{body}\n"
        self._sock.sendall(wire.encode("utf-8"))
        if not expect_response:
            return None

        want = f"R{seq}|"
        deadline = time.time() + timeout

        # buffered first
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

    # ---------- high-level API ----------
    def set_mode(self, mode: str) -> None:  # CW, USB, AM, FM, etc.
        m = mode.strip().upper()
        self._send_counted(f"slice s 0 mode={m}")

    def set_band(self, band_m: int) -> None:
        ctr = self._band_center_mhz(band_m)
        self._send_counted("slice s 0 tx=1", expect_response=False)
        self._send_counted(f"slice t 0 {self._mhz(ctr)}")

    def set_drive_w(self, watts: float) -> None:
        pct = int(max(0.0, min(100.0, watts)))
        self._send_counted(f"transmit set rfpower={pct}", expect_response=False)
        self._send_counted(f"transmit set tunepower={pct}", expect_response=False)

    def key_carrier_on(self) -> None:
        self._send_counted("transmit tune on", expect_response=False)

    def key_carrier_off(self) -> None:
        self._send_counted("transmit tune off", expect_response=False)

    def set_two_tone(self, enabled: bool) -> None:
        val = "on" if enabled else "off"
        try:
            self._send_counted(f"transmit two_tone {val}", expect_response=False)
        except Exception:
            self._send_counted(f"transmit set two_tone={'1' if enabled else '0'}", expect_response=False)
