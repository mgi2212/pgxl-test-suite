
import csv
from ..runners.runner import TestCase, TestCaseResult
from ..config import AppConfig
from ..devices.pgxl import PGXL
from ..devices.flex import FlexRadio
from ..utils.artifacts import new_run_dir, write_context
from ..utils.plots import bar_plot

def drain_current(cfg: AppConfig, res: TestCaseResult) -> None:
    outdir = new_run_dir("drain_current")
    pg = PGXL(cfg.pgxl.host, cfg.pgxl.port, cfg.pgxl.model); pg.connect()
    fx = FlexRadio(cfg.flex.host, cfg.flex.port) if cfg.flex else None
    if fx: fx.connect()

    modes = ["AB","AAB"]
    rows = []
    for b in cfg.bands_m:
        if fx: fx.set_band(b); fx.set_mode("CW"); fx.set_drive_w(10.0)
        for m in modes:
            pg.set_mode(m)
            tel = pg.telemetry()
            rows.append([b, m, tel.get("Id", 0.0)])

    with (outdir / "drain_current.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["band_m","mode","id_a"]); w.writerows(rows)

    # Chart per mode
    bands = sorted(set(r[0] for r in rows))
    for m in modes:
        vals = [r[2] for r in rows if r[1]==m]
        bar_plot([str(b) for b in bands], vals, f"Drain Current {m}", "Band (m)", "Id (A)", (outdir / f"id_{m}.png").as_posix())
    write_context(outdir, {"suite":"drain_current","modes":modes})
    res.logs.append("Drain current recorded (simulation if no live PGXL).")

def discover():
    return [ TestCase("drain.current_per_band_mode", drain_current) ]
