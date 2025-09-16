from dataclasses import dataclass
from typing import Optional
import socket, time

@dataclass
class FlexRadio:
    host: str
    port: int = 4992
    _connected: bool = False

    # internal
    _sock: Optional[socket.socket] = None
    _seq: int = 0
    _rxbuf: str = ""

    # --- connection ---
    def connect(self, timeout: float = 5.0) -> None:
        """Open a TCP connection to the FlexRadio SmartSDR TCP port."""
        self._sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self._sock.settimeout(0.5)
        self._connected = True
        self._seq = 0
        self._rxbuf = ""
        # Optional: turn off band persistence so we can freely drive slice params
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

    # --- low-level counted I/O ---
    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _read_lines(self) -> list[str]:
        """Pull whatever is available from the socket into _rxbuf and return complete lines."""
        if not self._sock:
            return []
        try:
            data = self._sock.recv(4096)
            if not data:
                return []
            self._rxbuf += data.decode("utf-8", errors="ignore")
        except socket.timeout:
            pass
        except Exception:
            return []
        lines = []
        while "\n" in self._rxbuf:
            line, self._rxbuf = self._rxbuf.split("\n", 1)
            lines.append(line.strip())
        return lines

    def _send_counted(self, body: str, expect_response: bool = True, timeout: float = 1.0) -> Optional[str]:
        """
        Send 'C<n>|{body}\\n' and, if expect_response, wait for 'R<n>|...' and return that line.
        Unsolicited 'S...' lines are ignored while waiting for the match.
        """
        if not self._connected or not self._sock:
            raise RuntimeError("FlexRadio is not connected.")
        seq = self._next_seq()
        wire = f"C{seq}|{body}\n"
        self._sock.sendall(wire.encode("utf-8"))
        if not expect_response:
            return None

        deadline = time.time() + timeout
        wanted_prefix = f"R{seq}|"
        # scan existing buffered lines first
        for line in self._read_lines():
            if line.startswith(wanted_prefix):
                return line
        # then poll until timeout
        while time.time() < deadline:
            for line in self._read_lines():
                if line.startswith(wanted_prefix):
                    return line
            time.sleep(0.01)
        raise TimeoutError(f"No response for sequence {seq} (body='{body}')")

    # --- helpers ---
    @staticmethod
    def _mhz(f: float) -> str:
        return f"{f:.6f}"

    @staticmethod
    def _band_center_mhz(band_m: int) -> float:
        """Reasonable band centers (MHz) for common HF/6m allocations."""
        centers = {
            160: 1.900, 80: 3.750, 60: 5.358, 40: 7.150, 30: 10.125,
            20: 14.175, 17: 18.118, 15: 21.225, 12: 24.940, 10: 28.850, 6: 50.500
        }
        if band_m not in centers:
            raise ValueError(f"Unsupported band: {band_m} m")
        return centers[band_m]

    # --- high-level API ---
    def set_mode(self, mode: str) -> None:  # 'CW','USB','AM','FM', etc.
        """
        Set the operating mode on TX slice 0.
        Common modes: CW, USB, LSB, AM, FM, DIGU, DIGL, SAM, NFM.
        """
        m = mode.strip().upper()
        self._send_counted(f"slice s 0 mode={m}")

    def set_band(self, band_m: int) -> None:
        """
        Tune TX slice 0 to the center of the requested band (MHz).
        Uses a simple band->center lookup; adjust as needed for your region.
        """
        ctr = self._band_center_mhz(band_m)
        # Ensure slice 0 is TX and tune it
        self._send_counted("slice s 0 tx=1", expect_response=False)
        self._send_counted(f"slice t 0 {self._mhz(ctr)}")

    def set_drive_w(self, watts: float) -> None:
        """
        Set RF drive power. SmartSDR expects percent (0-100), but this helper
        treats the provided value as watts on a 100 W radio and clamps 0..100.
        Applies to both rfpower and tunepower for consistency.
        """
        pct = int(max(0.0, min(100.0, watts)))
        self._send_counted(f"transmit set rfpower={pct}", expect_response=False)
        self._send_counted(f"transmit set tunepower={pct}", expect_response=False)

    def key_carrier_on(self) -> None:
        """Enable TUNE carrier (continuous carrier for measurements)."""
        self._send_counted("transmit tune on", expect_response=False)

    def key_carrier_off(self) -> None:
        """Disable TUNE carrier."""
        self._send_counted("transmit tune off", expect_response=False)

    def set_two_tone(self, enabled: bool) -> None:
        """
        Enable/disable internal two-tone generator if available in your firmware.
        If your radio uses a different knob for this feature, adjust the command.
        """
        val = "on" if enabled else "off"
        # Some firmware may use 'transmit two_tone on|off' or 'transmit set two_tone=1|0'.
        # Try the first, fall back to the second silently.
        try:
            self._send_counted(f"transmit two_tone {val}", expect_response=False)
        except Exception:
            self._send_counted(f"transmit set two_tone={'1' if enabled else '0'}", expect_response=False)
