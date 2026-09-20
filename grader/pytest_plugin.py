class GraderPlugin:
    """Truyền vào pytest.main(plugins=[...]) — CHỈ lo gom kết quả structured qua hook
    pytest_runtest_logreport để hiển thị trên UI Streamlit.

    Việc sinh test động (pytest_generate_tests) nằm ở grader/conftest.py, KHÔNG còn
    ở đây — vì khi chạy song song bằng pytest-xdist, plugin truyền qua `plugins=`
    chỉ tồn tại trong tiến trình chính, không tới được các worker process, trong khi
    conftest.py thì mọi worker đều tự nạp được.
    """

    def __init__(self, total_cases: int = 0):
        self.total_cases = total_cases
        self.output_results = []
        self.structure_results = []
        self._progress_cb = None

    def set_progress_callback(self, cb):
        self._progress_cb = cb

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
            done = len(self.output_results) + len(self.structure_results)
            self._progress_cb(done, self.total_cases)
