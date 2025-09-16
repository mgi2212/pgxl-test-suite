
import csv
from ..runners.runner import TestCase, TestCaseResult
from ..config import AppConfig
from ..devices.pgxl import PGXL
from ..devices.flex import FlexRadio
from ..utils.artifacts import new_run_dir, write_context
from ..utils.plots import bar_plot

def gain_sweep(cfg: AppConfig, res: TestCaseResult) -> None:
    outdir = new_run_dir("gain_band")
    pg = PGXL(cfg.pgxl.host, cfg.pgxl.port, cfg.pgxl.model); pg.connect()
    fx = FlexRadio(cfg.flex.host, cfg.flex.port) if cfg.flex else None
    if fx: fx.connect()

    drive_levels = [5.0, 10.0, 20.0]  # W
    rows = []
    for b in cfg.bands_m:
        if fx: fx.set_band(b); fx.set_mode("CW")
        for d in drive_levels:
            if fx: fx.set_drive_w(d)
            tel = pg.telemetry()
            pout = tel.get("PoutW", 0.0)
            # Gain in dB: 10*log10(Pout/Pin)
            import math
            gdb = 10*math.log10(max(pout,1e-3)/max(d,1e-3))
            rows.append([b, d, pout, gdb])

    with (outdir / "gain.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["band_m","drive_w","pout_w","gain_db"]); w.writerows(rows)

    # Simple chart: average gain per band at 10 W
    bands = sorted(set(r[0] for r in rows))
    avg_gain = []
    for b in bands:
        g = [r[3] for r in rows if r[0]==b and r[1]==10.0]
        avg_gain.append(sum(g)/len(g) if g else 0.0)
    bar_plot([str(b) for b in bands], avg_gain, "Average Gain @10W", "Band (m)", "Gain (dB)", (outdir/"gain_bar.png").as_posix())
    write_context(outdir, {"suite":"gain_band","drive_levels":drive_levels,"bands":bands})
    res.logs.append("Gain per band computed (stub Pout if simulation).")

def discover():
    return [ TestCase("gain.per_band", gain_sweep) ]
