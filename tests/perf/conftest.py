import pytest


def pytest_addoption(parser):
    parser.addoption("--perf", action="store_true", help="run performance tests")


def pytest_collection_modifyitems(config, items):
    if getattr(config.option, "perf", False):
        return
    skip_perf = pytest.mark.skip(reason="add --perf to run performance tests")
    for item in items:
        if "tests/perf/" in str(item.fspath):
            item.add_marker(skip_perf)
