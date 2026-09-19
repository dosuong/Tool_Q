class GraderPlugin:
    """Truyền vào pytest.main(plugins=[...]).

    Sinh test động theo (file học sinh x test case output) và
    (file học sinh x luật cấu trúc), rồi gom kết quả structured qua
    hook pytest_runtest_logreport để hiển thị trên UI Streamlit.
    """

    def __init__(self, output_cases, structure_cases):
        # output_cases: list[{"student_file","test_case","case_index","bai_label","function_name","case_id"}]
        # structure_cases: list[{"student_file","structural_rules","bai_label","case_id"}]
        self.output_cases = output_cases
        self.structure_cases = structure_cases
        self.output_results = []
        self.structure_results = []
        self._progress_cb = None

    def set_progress_callback(self, cb):
        self._progress_cb = cb

    def pytest_generate_tests(self, metafunc):
        names = set(metafunc.fixturenames)
        if {"student_file", "test_case", "case_index", "bai_label", "function_name"} <= names:
            metafunc.parametrize(
                "student_file,test_case,case_index,bai_label,function_name",
                [
                    (c["student_file"], c["test_case"], c["case_index"], c["bai_label"], c["function_name"])
                    for c in self.output_cases
                ],
                ids=[c["case_id"] for c in self.output_cases],
            )
        elif {"student_file", "structural_rules", "bai_label"} <= names:
            metafunc.parametrize(
                "student_file,structural_rules,bai_label",
                [(c["student_file"], c["structural_rules"], c["bai_label"]) for c in self.structure_cases],
                ids=[c["case_id"] for c in self.structure_cases],
            )

    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            return
        props = dict(report.user_properties)
        changed = False
        if "grade_result" in props:
            self.output_results.append(props["grade_result"])
            changed = True
        if "structure_result" in props:
            self.structure_results.append(props["structure_result"])
            changed = True
        if changed and self._progress_cb:
            total = len(self.output_cases) + len(self.structure_cases)
            done = len(self.output_results) + len(self.structure_results)
            self._progress_cb(done, total)
