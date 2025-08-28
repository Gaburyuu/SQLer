import pytest


def pytest_addoption(parser):
    parser.addoption("--perf", action="store_true", help="run performance tests")


from pathlib import Path


def pytest_collection_modifyitems(config, items):
    if getattr(config.option, "perf", False):
        return
    skip_perf = pytest.mark.skip(reason="add --perf to run performance tests")
    for item in items:
        parts = Path(str(item.fspath)).parts
        if "perf" in parts:
            item.add_marker(skip_perf)
