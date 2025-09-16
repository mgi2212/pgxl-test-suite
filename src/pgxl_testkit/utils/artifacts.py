
import pathlib, datetime, json
def new_run_dir(suite: str) -> pathlib.Path:
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    p = pathlib.Path('artifacts') / suite / ts
    p.mkdir(parents=True, exist_ok=True)
    return p
def write_context(outdir: pathlib.Path, context: dict) -> None:
    (outdir / 'context.json').write_text(json.dumps(context, indent=2))
