from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class TestCase:
    input: str = ""
    expected_output: str = ""
    timeout: float = 5.0
    note: str = ""
    ignore_trailing_whitespace: bool = True
    call_args: Optional[list] = None
    call_kwargs: Optional[dict] = None
    expected_return: Any = None


@dataclass
class GradeResult:
    student_name: str
    student_file: str
    bai_label: str
    case_index: int
    case_note: str = ""
    passed: bool = False
    timed_out: bool = False
    crashed: bool = False
    returncode: Optional[int] = None
    stdin_given: str = ""
    expected_output: str = ""
    actual_output: str = ""
    diff_summary: str = ""
    error_type: str = ""
    error_line: Optional[int] = None
    error_message: str = ""
    raw_stderr: str = ""
    short_message: str = ""
    mode_used: str = "program"

    def to_dict(self):
        return asdict(self)


@dataclass
class StructureResult:
    student_name: str
    student_file: str
    bai_label: str
    ok: bool
    violations: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
