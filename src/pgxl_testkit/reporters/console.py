
from ..runners.runner import SuiteResult
class ConsoleReporter:
    def emit(self, result: SuiteResult) -> None:
        print(f"Suite: {result.suite}")
        for c in result.cases:
            status = "PASS" if c.failed == 0 and c.skipped == 0 else ("SKIP" if c.skipped else "FAIL")
            print(f" - {c.id}: {status}")
