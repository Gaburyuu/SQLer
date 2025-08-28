# Perf tests are controlled via the `perf` marker (see pytest.ini).
# Enable optimistic write retries under contention just for perf runs.
import os


def pytest_configure(config):
    os.environ["SQLER_RETRY_ON_STALE"] = "1"
    os.environ["SQLER_QUERY_INCLUDE_VERSION"] = "1"
    os.environ["SQLER_JIT_VERSION"] = "1"
