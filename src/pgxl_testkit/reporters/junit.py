
from ..runners.runner import SuiteResult
import xml.etree.ElementTree as ET
class JUnitReporter:
    def __init__(self, path: str): self.path = path
    def emit(self, result: SuiteResult) -> None:
        testsuite = ET.Element("testsuite", name=result.suite, tests=str(len(result.cases)),
                               failures=str(result.failed), skipped=str(result.skipped))
        for c in result.cases:
            tc = ET.SubElement(testsuite, "testcase", name=c.id)
            if c.failed:
                failure = ET.SubElement(tc, "failure", message="failed")
                failure.text = "\n".join(c.logs)
            if c.skipped:
                ET.SubElement(tc, "skipped")
        ET.ElementTree(testsuite).write(self.path, encoding="utf-8", xml_declaration=True)
