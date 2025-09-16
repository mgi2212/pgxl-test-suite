    `from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import socket

@dataclass
class PGXL:
    host: str
    port: int = 9008  # PGXL TCP port
    model: str = "PGXL"
    _sock: Optional[socket.socket] = None
    _tx_id: int = 0
    firmware_version: Optional[str] = None

    # ---------- connection ----------
    def connect(self) -> None:
        """Open TCP socket and read the banner/firmware line."""
        self._sock = socket.create_connection((self.host, self.port), timeout=5)
        banner = self._recv_line(1024)
        self.firmware_version = banner or None
        self._tx_id = 0  # reset counter on (re)connect

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    # ---------- helpers ----------
    def _next_tx_id(self) -> int:
        self._tx_id += 1
        return self._tx_id

    def _recv_line(self, bufsize: int = 4096) -> str:
        if not self._sock:
            raise RuntimeError("Not connected to PGXL.")
        data = self._sock.recv(bufsize).decode(errors="replace")
        return data.strip()

    def _send_counted(self, body: str) -> str:
        """
        Send:  C<n>|{body}\r\n
        Expect: R<n>|<status>|<payload>
        Returns the raw reply string.
        """
        if not self._sock:
            raise RuntimeError("Not connected to PGXL.")
        tx = self._next_tx_id()
        wire = f"C{tx}|{body}\r\n"
        self._sock.sendall(wire.encode())
        reply = self._recv_line()
        if not reply.startswith("R"):
            raise ValueError(f"Malformed response (no 'R'): {reply!r}")
        # Verify echoed counter
        bar = reply.find("|")
        if bar == -1:
            raise ValueError(f"Malformed response (no '|'): {reply!r}")
        echoed = reply[1:bar]
        try:
            echoed_id = int(echoed, 10)
        except Exception as e:
            raise ValueError(f"Bad response counter: {reply!r}") from e
        if echoed_id != tx:
            raise RuntimeError(f"Counter mismatch (sent {tx}, got {echoed_id}). Reply: {reply!r}")
        return reply

    @staticmethod
    def _parse_keyvals(reply: str) -> Tuple[str, Dict[str, str]]:
        """Parse R<n>|<status>|k=v k=v ... -> (status, dict)."""
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
        """Place amp in STANDBY (operate=0)."""
        self._send_counted("operate=0")

    def operate(self) -> None:
        """Place amp in OPERATE (operate=1)."""
        self._send_counted("operate=1")

    def set_mode(self, mode: str) -> None:
        """
        Set bias mode: 'AB' or 'AAB'.
        Maps to status keys like biasA=RADIO_AB / RADIO_AAB.
        """
        m = mode.strip().upper()
        if m not in ("AB", "AAB"):
            raise ValueError("mode must be 'AB' or 'AAB'")
        # Apply to both A/B paths
        self._send_counted(f"setup biasA=RADIO_{m} biasB=RADIO_{m}")

    # ---------- telemetry ----------
    def telemetry(self) -> Dict[str, Any]:
        """
        Query status and normalize a few common fields while returning the full KV blob.
        Returns keys:
          Vd, Id, SWR, PoutW, PA_TempC, PS_TempC, Fan, Faults, raw
        """
        reply = self._send_counted("status")
        _, kv = self._parse_keyvals(reply)

        def fget(key: str) -> Optional[float]:
            try:
                return float(kv[key])
            except Exception:
                return None

        # Map a handful of common fields (names based on observed status keys)
        vd = fget("vdd")
        idc = fget("id")
        pout = fget("fwd")  # forward power
        swr = fget("swr")
        pa_temp = fget("hltemp") or fget("temp")   # use hltemp if present
        ps_temp = fget("temp")

        return {
            "Vd": vd,
            "Id": idc,
            "SWR": swr,
            "PoutW": pout,
            "PA_TempC": pa_temp,
            "PS_TempC": ps_temp,
            "Fan": kv.get("fanmode"),
            "Faults": [],  # populate from a future 'faults' query if available
            "raw": kv,
        }

    # Optional convenience
    def get_info(self) -> Dict[str, str]:
        """Return amplifier info dict (serial, version, etc.)."""
        reply = self._send_counted("info")
        _, kv = self._parse_keyvals(reply)
        return kv
