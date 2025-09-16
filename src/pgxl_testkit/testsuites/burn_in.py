
import time, csv
from ..runners.runner import TestCase, TestCaseResult
from ..config import AppConfig
from ..devices.pgxl import PGXL
from ..devices.flex import FlexRadio
from ..utils.artifacts import new_run_dir, write_context
from ..utils.plots import line_plot

def burn_in_2h(cfg: AppConfig, res: TestCaseResult) -> None:
    outdir = new_run_dir("burn_in")
    pg = PGXL(cfg.pgxl.host, cfg.pgxl.port, cfg.pgxl.model); pg.connect()
    fx = None
    if cfg.flex: fx = FlexRadio(cfg.flex.host, cfg.flex.port); fx.connect()

    # Setup (stub): operate, key carrier
    pg.operate()
    if fx:
        fx.set_mode("CW"); fx.set_drive_w(10.0); fx.key_carrier_on()

    t0 = time.time()
    duration_s = 2*60*60  # 2 hours
    interval_s = 5
    rows = []
    try:
        while time.time() - t0 < duration_s:
            tel = pg.telemetry()
            t = int(time.time() - t0)
            rows.append([t, tel.get("PA_TempC"), tel.get("PS_TempC"), tel.get("Vd"), tel.get("Id"), tel.get("SWR"), tel.get("PoutW")])
            time.sleep(interval_s)
    finally:
        if fx: fx.key_carrier_off()

    with (outdir / "telemetry.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["t_sec","pa_temp_c","ps_temp_c","vd_v","id_a","swr","pout_w"]); w.writerows(rows)

    # Plots
    if rows:
        t = [r[0] for r in rows]
        line_plot(t, [r[1] for r in rows], "PA Temp vs Time", "t (s)", "Temp (C)", (outdir/"pa_temp.png").as_posix())
        line_plot(t, [r[3] for r in rows], "Drain Voltage vs Time", "t (s)", "Vd (V)", (outdir/"vd.png").as_posix())
        line_plot(t, [r[4] for r in rows], "Drain Current vs Time", "t (s)", "Id (A)", (outdir/"id.png").as_posix())
    write_context(outdir, {"suite":"burn_in","interval_s":interval_s,"duration_s":duration_s})
    res.logs.append("Burn-in completed (stub data if simulation).")

def discover():
    return [ TestCase("burn_in.2h", burn_in_2h) ]
