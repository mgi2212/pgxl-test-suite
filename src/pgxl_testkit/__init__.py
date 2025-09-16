# Lightweight package init: avoid eager imports that can fail at console start.
__all__ = ["PGXL", "FlexRadio"]

def __getattr__(name):
    if name == "PGXL":
        from .devices.pgxl import PGXL as _PGXL
        return _PGXL
    if name == "FlexRadio":
        from .devices.flex import FlexRadio as _FlexRadio
        return _FlexRadio
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")