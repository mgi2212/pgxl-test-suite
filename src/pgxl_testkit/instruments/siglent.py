
from typing import Tuple, List
import os, math
try:
    import pyvisa
except Exception:
    pyvisa = None

class SiglentSVA:
    def __init__(self, resource: str|None=None, timeout_ms: int = 5000):
        self.resource = resource
        self.timeout_ms = timeout_ms
        self.rm = None
        self.inst = None
        self.sim = bool(os.environ.get("PGXL_SIMULATE", "1") == "1" or not resource or pyvisa is None)

    def connect(self) -> None:
        if self.sim: return
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(self.resource)
        self.inst.timeout = self.timeout_ms

    def close(self) -> None:
        if self.inst: self.inst.close()
        if self.rm: self.rm.close()

    def sweep_s11(self, start_hz: float, stop_hz: float, points: int = 201) -> Tuple[List[float], List[float]]:
        freqs = [start_hz + i*(stop_hz-start_hz)/(points-1) for i in range(points)]
        if self.sim:
            s11 = [-20.0 + 1.5*math.sin(2*math.pi*(f-1e6)/40e6) for f in freqs]
            return freqs, s11
        # TODO: real SCPI for S11 (SNA) measurement
        # Placeholder: return simulated
        s11 = [-20.0 for _ in freqs]
        return freqs, s11

    def sweep_s21(self, start_hz: float, stop_hz: float, points: int = 201) -> Tuple[List[float], List[float]]:
        freqs = [start_hz + i*(stop_hz-start_hz)/(points-1) for i in range(points)]
        if self.sim:
            knee = 60e6
            s21 = [0.1 if f <= knee else -40.0 - 20.0*math.log10((f-knee+1)/1e6) for f in freqs]
            return freqs, s21
        # TODO: real SCPI to configure 2-port S21 and fetch trace
        s21 = [0.0 for _ in freqs]
        return freqs, s21

    # Spectrum helpers
    def sa_config(self, center_hz: float, span_hz: float, rbw_hz: float, vbw_hz: float|None=None) -> None:
        if self.sim: return
        # TODO: set SA mode, center/span/RBW/VBW
        pass

    def sa_marker_read(self, freqs: List[float]) -> List[float]:
        if self.sim:
            # Simulate tones at fc±700 Hz: center at 14.2 MHz
            vals = [-10.0 for _ in freqs]
            return vals
        # TODO: place markers and read dBm values
        return [float('nan') for _ in freqs]

    def screenshot(self, path: str) -> None:
        if self.sim:
            return
        # TODO: fetch BMP/PNG screen
        pass
