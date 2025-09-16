from __future__ import annotations
import json
import time
from typing import Optional
import typer
from .devices.flex import FlexRadio

# LAZY import Rigol inside commands (to avoid import issues when not installed on a box)
# Lazy import PGXL inside functions; only import Flex here
from .devices.flex import FlexRadio

app = typer.Typer(help="PGXL & FlexRadio device controls")

rigol_app = typer.Typer(help="Control Rigol VNA via SCPI/TCP")
pgxl_app = typer.Typer(help="Control the Power Genius XL amplifier")
flex_app = typer.Typer(help="Control the FlexRadio via TCP (SmartSDR)")

app.add_typer(rigol_app, name="rigol")
app.add_typer(pgxl_app, name="pgxl")
app.add_typer(flex_app, name="flex")

# ---------- Rigol (lazy import inside each command) ----------
@rigol_app.command("idn")
def rigol_idn(
    host: str = typer.Option(..., "--host", help="Rigol VNA host/IP"),
    port: int = typer.Option(5025, "--port", help="SCPI TCP port"),
):
    from .devices.rigol import RigolVNA
    v = RigolVNA(host, port)
    v.connect()
    try:
        typer.echo(v.idn())
    finally:
        v.disconnect()

@rigol_app.command("s11")
def rigol_s11(
    host: str = typer.Option(..., "--host"),
    port: int = typer.Option(5025, "--port"),
    start_mhz: float = typer.Option(1.0, "--start-mhz"),
    stop_mhz: float = typer.Option(70.0, "--stop-mhz"),
    points: int = typer.Option(401, "--points"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON instead of table"),
):
    from .devices.rigol import RigolVNA
    v = RigolVNA(host, port); v.connect()
    try:
        freqs, s11_db = v.sweep_s11(start_mhz*1e6, stop_mhz*1e6, points)
    finally:
        v.disconnect()
    if json_out:
        import json
        typer.echo(json.dumps({"freq_hz": freqs, "s11_db": s11_db}))
    else:
        typer.echo(f"{'Freq (MHz)':>12}  {'S11 (dB)':>10}")
        for fHz, dB in zip(freqs, s11_db):
            typer.echo(f"{fHz/1e6:12.6f}  {dB:10.3f}")

@rigol_app.command("save-s1p")
def rigol_save_s1p(
    host: str = typer.Option(..., "--host"),
    port: int = typer.Option(5025, "--port"),
    start_mhz: float = typer.Option(1.0, "--start-mhz"),
    stop_mhz: float = typer.Option(70.0, "--stop-mhz"),
    points: int = typer.Option(401, "--points"),
    out: str = typer.Option("rigol_s11.s1p", "--out", help="Output Touchstone .s1p path"),
):
    from .devices.rigol import RigolVNA
    v = RigolVNA(host, port); v.connect()
    try:
        v.save_s1p(out, start_mhz*1e6, stop_mhz*1e6, points)
    finally:
        v.disconnect()
    typer.echo(f"Saved: {out}")

# ---------- PGXL (lazy import inside each command) ----------
@pgxl_app.command("status")
def pgxl_status(
    amp_host: str = typer.Option(..., "--amp-host", help="PGXL IP"),
    amp_port: int = typer.Option(9008, "--amp-port", help="PGXL TCP port")
):
    from .devices.pgxl import PGXL
    amp = PGXL(amp_host, amp_port)
    amp.connect()
    data = amp.telemetry()
    amp.disconnect()
    typer.echo(json.dumps(data, indent=2))

@pgxl_app.command("operate")
def pgxl_operate(
    amp_host: str = typer.Option(..., "--amp-host"),
    amp_port: int = typer.Option(9008, "--amp-port")
):
    from .devices.pgxl import PGXL
    amp = PGXL(amp_host, amp_port)
    amp.connect()
    amp.operate()
    amp.disconnect()
    typer.echo("PGXL set to OPERATE")

@pgxl_app.command("standby")
def pgxl_standby(
    amp_host: str = typer.Option(..., "--amp-host"),
    amp_port: int = typer.Option(9008, "--amp-port")
):
    from .devices.pgxl import PGXL
    amp = PGXL(amp_host, amp_port)
    amp.connect()
    amp.standby()
    amp.disconnect()
    typer.echo("PGXL set to STANDBY")

@pgxl_app.command("bias")
def pgxl_bias(
    mode: str = typer.Argument(..., help="AB or AAB"),
    amp_host: str = typer.Option(..., "--amp-host"),
    amp_port: int = typer.Option(9008, "--amp-port")
):
    from .devices.pgxl import PGXL
    amp = PGXL(amp_host, amp_port)
    amp.connect()
    amp.set_mode(mode)
    amp.disconnect()
    typer.echo(f"PGXL bias set to {mode.upper()}")

@pgxl_app.command("band")
def pgxl_band(
    band_m: str = typer.Argument(..., help="160, 80, 60, 40, 30, 20, 17, 15, 12, 10, 6"),
    amp_host: str = typer.Option(..., "--amp-host"),
    amp_port: int = typer.Option(9008, "--amp-port")
):
    from .devices.pgxl import PGXL
    amp = PGXL(amp_host, amp_port)
    amp.connect()
    amp.set_band(band_m)
    amp.disconnect()
    typer.echo(f"PGXL bandA set to {band_m}m")

# ---------- FlexRadio ----------
@flex_app.command("mode")
def flex_mode(
    mode: str = typer.Argument(..., help="CW, USB, LSB, AM, FM, DIGU, DIGL, etc."),
    flex_host: str = typer.Option(..., "--flex-host", help="FlexRadio IP"),
    flex_port: int = typer.Option(4992, "--flex-port")
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    try:
        r.set_mode(mode)
    finally:
        r.disconnect()
    typer.echo(f"FlexRadio mode set to {mode.upper()}")

@flex_app.command("freq")
def flex_freq(
    freq_mhz: float = typer.Argument(..., help="Frequency in MHz, e.g. 14.200"),
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port"),
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    try:
        r.set_frequency_mhz(freq_mhz)
    finally:
        r.disconnect()
    typer.echo(f"FlexRadio tuned slice 0 to {freq_mhz:.6f} MHz")

@flex_app.command("rfpower")
def flex_rfpower(
    pct: int = typer.Argument(..., help="RF power percent 0-100"),
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port"),
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    try:
        r.set_rf_power_pct(pct)
    finally:
        r.disconnect()
    typer.echo(f"FlexRadio RF power set to {pct}%")

@flex_app.command("tunepower")
def flex_tunepower(
    pct: int = typer.Argument(..., help="TUNE power percent 0-100"),
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port"),
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    try:
        r.set_tune_power_pct(pct)
    finally:
        r.disconnect()
    typer.echo(f"FlexRadio TUNE power set to {pct}%")

@flex_app.command("drive")
def flex_drive(
    watts: float = typer.Argument(..., help="Convenience: sets BOTH rfpower & tunepower to this percent 0-100"),
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port"),
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    try:
        r.set_drive_w(watts)
    finally:
        r.disconnect()
    typer.echo(f"FlexRadio rfpower & tunepower set ~= {int(watts)}%")

@flex_app.command("tune-on")
def flex_tune_on(
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port")
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    try:
        r.key_carrier_on()
    finally:
        r.disconnect()
    typer.echo("FlexRadio TUNE on")

@flex_app.command("tune-off")
def flex_tune_off(
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port")
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    try:
        r.key_carrier_off()
    finally:
        r.disconnect()
    typer.echo("FlexRadio TUNE off")
    
# ---------- Top-level sweep (Flex + optional PGXL) ----------
DEFAULT_BANDS = [
    ("160m", 1.800, 2.000),
    ("80m",  3.500, 4.000),
    ("60m",  5.3515, 5.3665),  # adjust for your region if needed
    ("40m",  7.000, 7.300),
    ("30m", 10.100, 10.150),
    ("20m", 14.000, 14.350),
    ("17m", 18.068, 18.168),
    ("15m", 21.000, 21.450),
    ("12m", 24.890, 24.990),
    ("10m", 28.000, 29.700),
    ("6m",  50.000, 54.000),
]
_BANDMAP = {name: (lo, hi) for name, lo, hi in DEFAULT_BANDS}

def _band_points(lo_mhz: float, hi_mhz: float, points: int, offset_khz: float) -> list[float]:
    pad = max(0.0, offset_khz) / 1000.0
    a = lo_mhz + pad
    b = hi_mhz - pad
    if a > b:
        raise typer.BadParameter(f"Offset {offset_khz} kHz too large for band {lo_mhz}-{hi_mhz} MHz")
    if points <= 1:
        return [ (a + b) / 2.0 ]
    step = (b - a) / (points - 1)
    return [ a + i * step for i in range(points) ]

@app.command("sweep")
def sweep(
    # Devices
    flex_host: str = typer.Option(..., "--flex-host", help="FlexRadio IP"),
    flex_port: int = typer.Option(4992, "--flex-port"),
    amp_host: Optional[str] = typer.Option(None, "--amp-host", help="PGXL IP (optional)"),
    amp_port: int = typer.Option(9008, "--amp-port"),
    amp_operate: bool = typer.Option(True, "--amp-operate/--no-amp-operate", help="Set PGXL to OPERATE during sweep"),
    # Bands / points
    band: Optional[list[str]] = typer.Option(
        None, "--band", "-b",
        help="Band names (repeatable). Defaults to all: 160m,80m,60m,40m,30m,20m,17m,15m,12m,10m,6m"
    ),
    points: int = typer.Option(3, "--points", min=1, help="Points per band (evenly spaced between edges)"),
    offset_khz: float = typer.Option(5.0, "--offset-khz", help="Pad from each band edge"),
    # Operating
    mode: Optional[str] = typer.Option(None, "--mode", help="CW, USB, LSB, AM, FM, DIGU, DIGL, ..."),
    rfpower: Optional[int] = typer.Option(10, "--rfpower", help="RF power percent 0-100 (None = leave)"),
    tunepower: Optional[int] = typer.Option(10, "--tunepower", help="TUNE power percent 0-100 (None = leave)"),
    two_tone: Optional[bool] = typer.Option(None, "--two-tone/--no-two-tone", help="Two-tone (SSB IMD) vs single-tone"),
    tx: float = typer.Option(10.0, "--tx", help="TX duration per point (s)"),
    settle: float = typer.Option(0.5, "--settle", help="Pause after tuning before TUNE on (s)"),
    idle: float = typer.Option(5.0, "--idle", help="Idle between points (s)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don’t transmit; just print the plan"),
):
    # Resolve selected bands
    bands = band or [name for name, _, _ in DEFAULT_BANDS]
    missing = [b for b in bands if b not in _BANDMAP]
    if missing:
        raise typer.BadParameter(f"Unknown band(s): {', '.join(missing)}")
    plan: dict[str, list[float]] = {
        b: _band_points(*_BANDMAP[b], points=points, offset_khz=offset_khz) for b in bands
    }

    # Print plan
    typer.echo("Sweep plan:")
    for b in bands:
        freqs = "  ".join(f"{f:.6f}" for f in plan[b])
        typer.echo(f"  {b}: {freqs}")

    if dry_run:
        typer.echo("Dry-run complete.")
        return

    # Connect devices
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    amp = None
    if amp_host:
        from .devices.pgxl import PGXL  # lazy import
        amp = PGXL(amp_host, amp_port)
        amp.connect()
        if amp_operate:
            amp.operate()

    # Apply radio settings up front
    try:
        eff_mode = mode.strip().upper() if mode else None
        if eff_mode:
            r.set_mode(eff_mode)
        if rfpower is not None:
            r.set_rf_power_pct(int(rfpower))
        if tunepower is not None:
            r.set_tune_power_pct(int(tunepower))
        if two_tone is not None:
            allowed_two_tone = {"USB", "LSB", "DIGU", "DIGL", "SAM"}
            if two_tone and eff_mode and eff_mode not in allowed_two_tone:
                typer.echo(f"Two-tone not valid in {eff_mode}; using single-tone.")
                r.set_two_tone(False)
            else:
                r.set_two_tone(two_tone)

        # Execute sweep
        for b in bands:
            lo, hi = _BANDMAP[b]
            ctr = (lo + hi) / 2.0
            typer.echo(f"\n--- {b} ({lo:.3f}-{hi:.3f} MHz, center {ctr:.3f}) ---")
            for idx, f in enumerate(plan[b], start=1):
                typer.echo(f"[{b}] {idx}/{len(plan[b])}  tune {f:.6f} MHz")
                r.set_frequency_mhz(f)
                time.sleep(settle)
                r.key_carrier_on()
                time.sleep(tx)
                r.key_carrier_off()
                time.sleep(idle)
    finally:
        # Return amp to STANDBY if we set OPERATE
        if amp:
            try:
                if amp_operate:
                    amp.standby()
            finally:
                amp.disconnect()
        r.disconnect()

    typer.echo("\nSweep complete.")

@flex_app.command("batch")
def flex_batch(
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port"),
    mode: Optional[str] = typer.Option(None, "--mode", help="CW, USB, LSB, AM, FM, DIGU, DIGL, ..."),
    band: Optional[int] = typer.Option(None, "--band", help="160,80,60,40,30,20,17,15,12,10,6"),
    freq: Optional[float] = typer.Option(None, "--freq", help="Exact frequency in MHz; overrides --band"),
    rfpower: Optional[int] = typer.Option(None, "--rfpower", help="RF power percent 0-100"),
    tunepower: Optional[int] = typer.Option(None, "--tunepower", help="TUNE power percent 0-100"),
    two_tone: Optional[bool] = typer.Option(None, "--two-tone/--no-two-tone", help="Enable/disable two-tone"),
    tune_on: bool = typer.Option(False, "--tune-on", help="Enable TUNE at end"),
    tune_off: bool = typer.Option(False, "--tune-off", help="Disable TUNE at end"),
    hold: float = typer.Option(0.0, "--hold", help="Keep connection open. Seconds (>0) or -1 to hold until Ctrl-C."),
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()
    tune_was_on = False
    try:
        eff_mode = mode.strip().upper() if mode else None
        if eff_mode is not None:
            r.set_mode(eff_mode)

        if freq is not None:
            r.set_frequency_mhz(freq)
        elif band is not None:
            r.set_band(band)

        if rfpower is not None:
            r.set_rf_power_pct(rfpower)
        if tunepower is not None:
            r.set_tune_power_pct(tunepower)

        if two_tone is not None:
            allowed_two_tone = {"USB", "LSB", "DIGU", "DIGL", "SAM"}
            if two_tone and eff_mode and eff_mode not in allowed_two_tone:
                typer.echo(f"Two-tone not valid in {eff_mode}; using single-tone.")
                r.set_two_tone(False)
            else:
                r.set_two_tone(two_tone)

        if tune_on and tune_off:
            typer.echo("Ignoring --tune-off because --tune-on also set.")
            tune_off = False

        if tune_on:
            ack = r.key_carrier_on()
            tune_was_on = True
            typer.echo(ack or "TUNE on")
        elif tune_off:
            ack = r.key_carrier_off()
            typer.echo(ack or "TUNE off")

        if hold < 0:
            typer.echo("Holding connection until Ctrl-C…")
            try:
                while True:
                    time.sleep(1.0)
            except KeyboardInterrupt:
                if tune_was_on:
                    ack = r.key_carrier_off()
                    typer.echo(ack or "TUNE off (on exit)")
        elif hold > 0:
            typer.echo(f"Holding connection for {hold:.1f}s…")
            time.sleep(hold)
            if tune_was_on:
                ack = r.key_carrier_off()
                typer.echo(ack or "TUNE off (after hold)")
        else:
            if tune_on:
                typer.echo("Note: TUNE drops when the client disconnects. Use --hold to keep it on.")

    finally:
        r.disconnect()
    typer.echo("Batch complete.")

if __name__ == "__main__":
    app()

@flex_app.command("persist")
def flex_persist(
    on: bool = typer.Option(False, "--on", help="Enable band persistence"),
    off: bool = typer.Option(False, "--off", help="Disable band persistence"),
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port"),
):
    if on and off:
        typer.echo("Choose either --on or --off, not both.")
        raise typer.Exit(2)
    if not on and not off:
        typer.echo("Specify one: --on or --off")
        raise typer.Exit(2)

    r = FlexRadio(flex_host, flex_port)
    r.connect()  # connect() already disables if disable_band_persistence=True
    try:
        r.set_band_persistence(on and not off)
        typer.echo(f"Band persistence {'ENABLED' if on and not off else 'DISABLED'}.")
    finally:
        r.disconnect()


@flex_app.command("persist")
def flex_persist(
    on: bool = typer.Option(False, "--on", help="Enable band persistence (persists across reboots)"),
    off: bool = typer.Option(False, "--off", help="Disable band persistence (persists across reboots)"),
    status: bool = typer.Option(False, "--status", help="Show last-seen band persistence state"),
    flex_host: str = typer.Option(..., "--flex-host"),
    flex_port: int = typer.Option(4992, "--flex-port"),
):
    r = FlexRadio(flex_host, flex_port)
    r.connect()  # connect no longer changes persistence
    try:
        if status and not (on or off):
            val = r.get_band_persistence_cached()
            if val is None:
                typer.echo("Band persistence: unknown (radio did not report yet).")
            else:
                typer.echo(f"Band persistence: {'ENABLED' if val else 'DISABLED'}")
            return
        if on and off:
            typer.echo("Choose either --on or --off (not both)."); raise typer.Exit(2)
        if on:
            r.set_band_persistence(True);  typer.echo("Band persistence ENABLED.")
        elif off:
            r.set_band_persistence(False); typer.echo("Band persistence DISABLED.")
        else:
            typer.echo("Specify one: --on  |  --off  |  --status"); raise typer.Exit(2)
    finally:
        r.disconnect()

