from __future__ import annotations
import json
import time
from typing import Optional
import typer

# Lazy import PGXL inside functions; only import Flex here
from .devices.flex import FlexRadio

app = typer.Typer(help="PGXL & FlexRadio device controls")

pgxl_app = typer.Typer(help="Control the Power Genius XL amplifier")
flex_app = typer.Typer(help="Control the FlexRadio via TCP (SmartSDR)")

app.add_typer(pgxl_app, name="pgxl")
app.add_typer(flex_app, name="flex")

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
