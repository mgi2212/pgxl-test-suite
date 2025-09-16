from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple
import socket, math

@dataclass
class RigolVNA:
    host: str
    port: int = 5025
    timeout: float = 3.0
    _sock: Optional[socket.socket] = None
    _rxbuf: bytes = b""

    # ---------- connect / io ----------
    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(self.timeout)

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def write(self, scpi: str) -> None:
        if not self._sock:
            raise RuntimeError("RigolVNA not connected")
        self._sock.sendall((scpi.rstrip() + "\n").encode("ascii"))

    def query(self, scpi: str) -> str:
        self.write(scpi)
        return self._readline()

    def _readline(self) -> str:
        if not self._sock:
            raise RuntimeError("RigolVNA not connected")
        data = b""
        while True:
            chunk = self._sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in chunk:
                break
        return data.decode(errors="ignore").strip()

    # ---------- basic ops ----------
    def idn(self) -> str:
        return self.query("*IDN?")

    def preset(self) -> None:
        # safe preset + stop continuous triggering
        self.write(":SYST:PRES")
        self.write(":INIT:CONT OFF")

    def select_s11(self) -> None:
        # create/activate a trace measuring S11 (names vary; use TR1)
        # CALC:PAR:DEF vs CALC:PAR:DEF: use common form
        self.write(":CALC:PAR:DEL:ALL")
        self.write(":CALC:PAR:DEF 'TR1', S11")
        self.write(":CALC:PAR:SEL 'TR1'")

    def setup_sweep(self, start_hz: float, stop_hz: float, points: int) -> None:
        self.write(f":SENS:FREQ:STAR {start_hz}")
        self.write(f":SENS:FREQ:STOP {stop_hz}")
        self.write(f":SENS:SWE:POIN {int(points)}")
        self.write(":SENS:BAND:AUTO ON")  # decent default
        self.write(":CALC:FORM SDAT")     # prefer complex data if available

    def single_trigger(self) -> None:
        # single acquisition, wait complete
        self.write(":INIT:IMM")
        self.write("*WAI")

    def fetch_s11(self) -> Tuple[List[float], List[float]]:
        """
        Return (freqs_Hz, s11_dB).
        Tries complex SDAT first; falls back to formatted FDATA (already in dB if FORM LOGM).
        """
        # Try complex data (Re,Im interleaved)
        try:
            self.write(":CALC:DATA:SDAT?")
            raw = self._readline()
            parts = [float(x) for x in raw.split(",")]
            if len(parts) >= 2:
                # need frequencies, too
                freqs = self._freq_axis()
                reim_pairs = list(zip(parts[::2], parts[1::2]))
                mag = [math.hypot(r, i) for (r, i) in reim_pairs]
                s11_db = [20.0 * math.log10(m) if m > 0 else -200.0 for m in mag]
                # protect length mismatch
                n = min(len(freqs), len(s11_db))
                return freqs[:n], s11_db[:n]
        except Exception:
            pass

        # Fallback: formatted magnitude data
        # Ensure LOGM format, then query formatted data
        self.write(":CALC:FORM LOGM")
        self.write(":CALC:DATA:FDAT?")
        raw = self._readline()
        vals = [float(x) for x in raw.split(",") if x.strip()]
        freqs = self._freq_axis()
        n = min(len(freqs), len(vals))
        return freqs[:n], vals[:n]

    def _freq_axis(self) -> List[float]:
        start = float(self.query(":SENS:FREQ:STAR?"))
        stop  = float(self.query(":SENS:FREQ:STOP?"))
        pts   = int(float(self.query(":SENS:SWE:POIN?")))
        if pts <= 1:
            return [ (start + stop) / 2.0 ]
        step = (stop - start) / (pts - 1)
        return [ start + i * step for i in range(pts) ]

    # ---------- convenience ----------
    def sweep_s11(self, start_hz: float, stop_hz: float, points: int) -> Tuple[List[float], List[float]]:
        self.preset()
        self.select_s11()
        self.setup_sweep(start_hz, stop_hz, points)
        self.single_trigger()
        return self.fetch_s11()

    def save_s1p(self, path: str, start_hz: float, stop_hz: float, points: int) -> None:
        freqs, s11_db = self.sweep_s11(start_hz, stop_hz, points)
        # Touchstone S1P: Hz, dB, angle (we’ll write 0 deg since we only fetched mag;
        # if SDAT succeeded we could compute angle — left simple for now).
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("# Hz S DB R 50\n")
            for fHz, dB in zip(freqs, s11_db):
                f.write(f"{int(fHz)} {dB:.3f} 0.0\n")
