import re
from pathlib import Path

FILENAME_RE = re.compile(r"^(?P<student>.+)_bai(?P<bai_num>\d+)\.py$", re.IGNORECASE)


def parse_filename(filename: str):
    """Trả về (student_id, bai_num) hoặc None nếu không khớp quy ước."""
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    return m.group("student"), int(m.group("bai_num"))


def group_by_bai(saved_files: list):
    """Trả về (matched: dict[int, list[Path]], unmatched: list[Path])."""
    matched, unmatched = {}, []
    for f in saved_files:
        parsed = parse_filename(f.name)
        if parsed is None:
            unmatched.append(f)
        else:
            _, bai_num = parsed
            matched.setdefault(bai_num, []).append(f)
    return matched, unmatched
