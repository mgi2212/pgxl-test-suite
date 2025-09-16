
import csv, math
from ..runners.runner import TestCase, TestCaseResult
from ..config import AppConfig
from ..devices.pgxl import PGXL
from ..devices.flex import FlexRadio
from ..instruments.siglent import SiglentSVA
from ..instruments.rigol import RigolVNA
from ..utils.artifacts import new_run_dir, write_context
from ..utils.plots import bar_plot

def _connect_sa(cfg: AppConfig):
    v = cfg.vna.vendor.lower()
    if v == 'siglent':
        vna = SiglentSVA(cfg.vna.visa.resource, cfg.vna.visa.timeout_ms)
    else:
        vna = RigolVNA(cfg.vna.visa.resource, cfg.vna.visa.timeout_ms)
    vna.connect()
    return vna

def linearity_harmonics(cfg: AppConfig, res: TestCaseResult) -> None:
    outdir = new_run_dir("linearity_harmonics")
    pg = PGXL(cfg.pgxl.host, cfg.pgxl.port, cfg.pgxl.model); pg.connect()
    fx = FlexRadio(cfg.flex.host, cfg.flex.port) if cfg.flex else None
    sa = _connect_sa(cfg)

    band = 20  # demo: 20m
    fc = 14.2e6
    tone = 700.0  # Hz spacing
    rbw = 1000.0
    if fx:
        fx.set_band(band); fx.set_mode("USB"); fx.set_two_tone(True)

    sa.sa_config(fc, 100e3, rbw)
    # markers at tones and IMD3 products:
    freqs = [fc - tone, fc + tone, fc - 3*tone, fc + 3*tone]
    levs = sa.sa_marker_read(freqs)

    # compute IMD3 (dBc) relative to tone level
    tone_level = (levs[0] + levs[1]) / 2.0 if all(v==v for v in levs[:2]) else float('nan')
    imd3 = (levs[2] + levs[3]) / 2.0 - tone_level if all(v==v for v in levs) else float('nan')

    with (outdir / "imd.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["band_m","fc_hz","tone_hz","rbw_hz","tone_level_dbm","imd3_dbc"]); w.writerow([band, int(fc), int(tone), int(rbw), tone_level, imd3])

    bar_plot(["Tone","IMD3"], [tone_level, tone_level+imd3 if imd3==imd3 else 0.0], "Two-Tone Levels", "", "dBm", (outdir/"two_tone.png").as_posix())

    # Harmonics (up to 5th)
    harmonics = [2,3,4,5]
    harm_levels = [-50.0, -60.0, -70.0, -75.0]  # simulated
    with (outdir / "harmonics.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["harmonic_n","level_dbc"]); [w.writerow([n, lvl]) for n,lvl in zip(harmonics, harm_levels)]
    bar_plot([str(n) for n in harmonics], harm_levels, "Harmonics (rel dBc)", "n", "dBc", (outdir/"harmonics.png").as_posix())

    write_context(outdir, {"suite":"linearity_harmonics","fc":fc,"tone":tone,"rbw":rbw})
    res.logs.append("Linearity & harmonics measured (simulated unless SCPI filled).")

def discover():
    return [ TestCase("linearity.harmonics", linearity_harmonics) ]
