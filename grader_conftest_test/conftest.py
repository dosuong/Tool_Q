
import os, json
def pytest_generate_tests(metafunc):
    if "val" in metafunc.fixturenames:
        path = os.environ.get("TEST_VAL_FILE")
        data = json.loads(open(path).read())
        metafunc.parametrize("val", data)
