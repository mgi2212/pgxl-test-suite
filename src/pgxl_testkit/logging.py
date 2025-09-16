
import logging
from rich.logging import RichHandler
def setup_logging(level: str = "INFO"):
    logging.basicConfig(level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
    return logging.getLogger("pgxl_testkit")
