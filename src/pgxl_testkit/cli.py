
from typing import Optional
import typer
from .config import load_config, AppConfig
from .runners.runner import TestRunner
from .reporters.junit import JUnitReporter
from .reporters.console import ConsoleReporter
from .reporters.html_pdf import HTMLPDFReporter

app = typer.Typer(add_completion=False, help="PGXL Testkit - modular tools for testing PGXL amplifiers")

@app.command()
def run(
    suite: str = typer.Argument(..., help="Test suite to run, e.g., lpf_sweep"),
    config: str = typer.Option("examples/config.yaml", "--config", "-c", help="Path to config YAML"),
    output_dir: str = typer.Option("artifacts", "--out", "-o", help="Directory for logs and reports"),
    list_tests: bool = typer.Option(False, "--list", help="List tests without running"),
    junit: Optional[str] = typer.Option(None, "--junit", help="Write JUnit XML to this path"),
    html: Optional[str] = typer.Option(None, "--html", help="Write HTML report to this path"),
    pdf: Optional[str] = typer.Option(None, "--pdf", help="Write PDF report to this path"),
):
    cfg: AppConfig = load_config(config)
    runner = TestRunner(cfg, output_dir)

    if list_tests:
        tests = runner.discover(suite)
        for t in tests:
            typer.echo(t.id)
        raise typer.Exit(code=0)

    result = runner.run(suite)
    ConsoleReporter().emit(result)
    if junit: JUnitReporter(path=junit).emit(result)
    if html or pdf: HTMLPDFReporter(html or "artifacts/report.html", pdf).emit(result)
    typer.echo(f"Done. {result.passed} passed, {result.failed} failed, {result.skipped} skipped.")
    raise typer.Exit(code=0 if result.failed == 0 else 1)

@app.command()
def menu(config: str = typer.Option("examples/config.yaml", "--config", "-c", help="Path to config YAML")):
    cfg: AppConfig = load_config(config)
    runner = TestRunner(cfg)
    while True:
        typer.echo("\nPGXL Testkit - Menu")
        typer.echo(" 1) LPF Sweep (requires direct LPF->VNA connection)")
        typer.echo(" 2) Burn-in (2 hours)")
        typer.echo(" 3) Gain per Band")
        typer.echo(" 4) Drain Current (AB/AAB)")
        typer.echo(" 5) Drain Voltage (AB/AAB)")
        typer.echo(" 6) Linearity & Harmonics (two-tone)")
        typer.echo(" 8) Full Acceptance (2-6)")
        typer.echo(" 9) Generate HTML report for last suite")
        typer.echo(" 0) Exit")
        choice = typer.prompt(">", default="0")
        if choice == "1":
            result = runner.run("lpf_sweep"); ConsoleReporter().emit(result)
        elif choice == "2":
            result = runner.run("burn_in"); ConsoleReporter().emit(result)
        elif choice == "3":
            result = runner.run("gain_band"); ConsoleReporter().emit(result)
        elif choice == "4":
            result = runner.run("drain_current"); ConsoleReporter().emit(result)
        elif choice == "5":
            result = runner.run("drain_voltage"); ConsoleReporter().emit(result)
        elif choice == "6":
            result = runner.run("linearity_harmonics"); ConsoleReporter().emit(result)
        elif choice == "8":
            for s in ["burn_in","gain_band","drain_current","drain_voltage","linearity_harmonics"]:
                result = runner.run(s); ConsoleReporter().emit(result)
        elif choice == "9":
            # naive: generate report for last run of each suite
            for s in ["lpf_sweep","burn_in","gain_band","drain_current","drain_voltage","linearity_harmonics"]:
                result = runner.run(s)  # re-run to produce a report; swap for artifact scan if desired
                HTMLPDFReporter(f"artifacts/{s}_report.html", f"artifacts/{s}.pdf").emit(result)
            typer.echo("Reports written in artifacts/*.html and *.pdf")
        elif choice == "0":
            raise typer.Exit(code=0)
        else:
            typer.echo("Unknown selection.")
