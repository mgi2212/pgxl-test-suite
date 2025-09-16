
import csv, pathlib
from ..runners.runner import TestCase, TestCaseResult
from ..config import AppConfig
from ..instruments.siglent import SiglentSVA
from ..instruments.rigol import RigolVNA
from ..utils.techcheck import checklist_confirm
from ..utils.artifacts import new_run_dir, write_context
from ..utils.plots import line_plot

def _connect_vna(cfg: AppConfig):
    v = cfg.vna.vendor.lower()
    if v == 'siglent':
        vna = SiglentSVA(cfg.vna.visa.resource, cfg.vna.visa.timeout_ms)
    else:
        vna = RigolVNA(cfg.vna.visa.resource, cfg.vna.visa.timeout_ms)
    vna.connect()
    return vna

def lpf_s21_sweep(cfg: AppConfig, res: TestCaseResult) -> None:
    ok = checklist_confirm(
        intro=(
            "\nLPF S21 Sweep - Tech Checklist\n"
            "This test requires a direct connection of the PGXL LPF module to the VNA.\n"
            "PGXL RF path must NOT be used for this measurement.\n"
        ),
        items=[
            "PGXL is in STANDBY and exciter RF is OFF.",
            "Disconnect PGXL RF IN/OUT. Remove any coax jumpers to the amplifier path.",
            "Connect VNA Port 1 to LPF INPUT (amp-side).",
            "Connect VNA Port 2 to LPF OUTPUT (antenna-side).",
            "Perform a 2-port calibration (SOLT or fixture cal) across the sweep band.",
            "Verify 50-ohm terminations and attenuators as needed to protect the VNA.",
        ],
    )
    if not ok:
        res.failed = 1; res.logs.append("Aborted: checklist not confirmed."); return

    vna = _connect_vna(cfg)
    start_hz, stop_hz, points = 1e6, 150e6, 801
    freqs, s21 = vna.sweep_s21(start_hz, stop_hz, points)

    outdir = new_run_dir("lpf_sweep")
    with (outdir / "lpf_s21.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["freq_hz", "s21_db"])
        for fz, il in zip(freqs, s21): w.writerow([int(fz), il])
    plot_path = outdir / "lpf_s21.png"
    line_plot(freqs, s21, "LPF S21 (insertion loss)", "Frequency (Hz)", "S21 (dB)", plot_path.as_posix())
    write_context(outdir, {"suite": "lpf_sweep", "start_hz": start_hz, "stop_hz": stop_hz, "points": points})

    passband_ok = all(il <= 0.5 for fz, il in zip(freqs, s21) if fz <= 60e6)
    stopband_ok = all(il <= -35.0 for fz, il in zip(freqs, s21) if fz >= 100e6)
    if passband_ok and stopband_ok:
        res.logs.append(f"LPF S21 sweep PASS.")
    else:
        res.failed = 1; res.logs.append(f"LPF S21 sweep FAIL (passband_ok={passband_ok}, stopband_ok={stopband_ok}).")

def discover():
    return [ TestCase("lpf_sweep.s21", lpf_s21_sweep) ]
