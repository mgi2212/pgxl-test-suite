from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, List
import socket, time

@dataclass
class PGXL:
    host: str
    port: int = 9008
    _sock: Optional[socket.socket] = None
    _seq: int = 0
    _rxbuf: str = ""
    banner: Optional[str] = None

    # ---------- connection ----------
    def connect(self, timeout: float = 5.0) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self._sock.settimeout(0.5)
        self._seq = 0
        self._rxbuf = ""
        # Read initial banner/firmware line if present (non-fatal if absent)
        try:
            data = self._sock.recv(1024)
            if data:
                self.banner = data.decode(errors="replace").strip()
        except Exception:
            self.banner = None

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

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
        TX: C<n>|{body}\n
        Wait for matching: R<n>|...
        """
        if not self._sock:
            raise RuntimeError("Not connected to PGXL.")
        seq = self._next_seq()
        wire = f"C{seq}|{body}\n"
        self._sock.sendall(wire.encode("utf-8"))
        if not expect_response:
            return None

        wanted = f"R{seq}|"
        deadline = time.time() + timeout

        # check buffered first
        for line in self._read_lines():
            if line.startswith(wanted):
                return line

        # poll until timeout
        while time.time() < deadline:
            for line in self._read_lines():
                if line.startswith(wanted):
                    return line
            time.sleep(0.01)

        raise TimeoutError(f"No response for sequence {seq} (body='{body}')")

    @staticmethod
    def _parse_kv(reply: str) -> Tuple[str, Dict[str, str]]:
        # R<n>|<status>|k=v k=v ...
        parts = reply.split("|", 2)
        if len(parts) < 3:
            raise ValueError(f"Unexpected response format: {reply!r}")
        status = parts[1]
        kv_blob = parts[2].strip()
        kv: Dict[str, str] = {}
        if kv_blob:
            for item in kv_blob.split():
                if "=" in item:
                    k, v = item.split("=", 1)
                    kv[k] = v
        return status, kv

    # ---------- high-level controls ----------
    def standby(self) -> None:
        self._send_counted("operate=0", expect_response=False)

    def operate(self) -> None:
        self._send_counted("operate=1", expect_response=False)

    def set_mode(self, mode: str) -> None:
        # mode: 'AB' or 'AAB'
        m = mode.strip().upper()
        if m not in ("AB", "AAB"):
            raise ValueError("mode must be 'AB' or 'AAB'")
        self._send_counted(f"setup biasA=RADIO_{m} biasB=RADIO_{m}", expect_response=False)

    def set_band(self, band_m: str | int) -> None:
        b = str(band_m)
        self._send_counted(f"setup bandA={b}")

    def telemetry(self) -> Dict[str, Any]:
        reply = self._send_counted("status")
        _, kv = self._parse_kv(reply)

        def fget(k: str) -> Optional[float]:
            try:
                return float(kv[k])
            except Exception:
                return None

        return {
            "Vd": fget("vdd"),
            "Id": fget("id"),
            "SWR": fget("swr"),
            "PoutW": fget("fwd"),
            "PA_TempC": fget("hltemp") or fget("temp"),
            "PS_TempC": fget("temp"),
            "Fan": kv.get("fanmode"),
            "raw": kv,
        }

    def faults(self) -> list[str]:
        # Placeholder until a faults query is defined
        return []
