
# PGXL Test Suite - Full Starter

Menu-driven tools for PGXL verification with Siglent/Rigol VNA support, burn-in, gain, drain V/I, and linearity/harmonics. Generates HTML/PDF reports.

## Install
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .
```

## Run
```bash
pgxl-test menu
# or
pgxl-test run lpf_sweep -c examples/config.yaml --html artifacts/lpf.html --pdf artifacts/lpf.pdf
```

## Notes
- Drivers run in **simulation** by default if no VISA resource is provided or `pyvisa` is missing. Set `PGXL_SIMULATE=0` and configure `vna.visa.resource` to talk to real gear.
- Replace TODO sections in `devices/pgxl.py`, `devices/flex.py`, and instrument drivers with your live SCPI/API.
