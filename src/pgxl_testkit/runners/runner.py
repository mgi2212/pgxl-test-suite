
from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any
import importlib
from ..config import AppConfig
from ..logging import setup_logging

@dataclass
class TestCaseResult:
    id: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)

@dataclass
class SuiteResult:
    suite: str
    cases: List[TestCaseResult]
    @property
    def passed(self) -> int: return sum(c.passed for c in self.cases)
    @property
    def failed(self) -> int: return sum(c.failed for c in self.cases)
    @property
    def skipped(self) -> int: return sum(c.skipped for c in self.cases)

class TestRunner:
    def __init__(self, cfg: AppConfig, out_dir: str = "artifacts"):
        self.cfg = cfg
        self.out_dir = out_dir
        self.log = setup_logging()

    def _load_suite_module(self, suite: str):
        return importlib.import_module(f"pgxl_testkit.testsuites.{suite}")

    def discover(self, suite: str) -> List["TestCase"]:
        mod = self._load_suite_module(suite)
        return getattr(mod, "discover")()

    def run(self, suite: str) -> SuiteResult:
        mod = self._load_suite_module(suite)
        test_cases: List[TestCase] = getattr(mod, "discover")()
        results: List[TestCaseResult] = []
        for tc in test_cases:
            res = TestCaseResult(id=tc.id)
            try:
                tc.run(self.cfg, res)
                if res.failed == 0 and res.skipped == 0:
                    res.passed = 1
            except Exception as e:
                res.failed = 1
                res.logs.append(f"Error: {e!r}")
            results.append(res)
        return SuiteResult(suite=suite, cases=results)

class TestCase:
    def __init__(self, id: str, func: Callable[[AppConfig, TestCaseResult], None]):
        self.id = id
        self.func = func
    def run(self, cfg: AppConfig, res: TestCaseResult):
        return self.func(cfg, res)
