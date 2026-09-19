from grader.ast_checker import check_structure
from grader.runner import grade_one


def test_student_stdout(request, student_file, test_case, case_index, bai_label, function_name):
    __tracebackhide__ = True
    result = grade_one(student_file, test_case, case_index, bai_label, function_name)
    request.node.user_properties.append(("grade_result", result.to_dict()))
    assert result.passed, result.short_message


def test_student_structure(request, student_file, structural_rules, bai_label):
    __tracebackhide__ = True
    source = student_file.read_text(encoding="utf-8", errors="replace")
    ok, violations = check_structure(
        source,
        structural_rules.get("required_constructs"),
        structural_rules.get("forbidden_constructs"),
        structural_rules.get("forbidden_imports"),
        structural_rules.get("forbidden_calls"),
    )
    request.node.user_properties.append(("structure_result", {
        "student_name": student_file.stem,
        "student_file": student_file.name,
        "bai_label": bai_label,
        "ok": ok,
        "violations": violations,
    }))
    assert ok, "; ".join(violations)
