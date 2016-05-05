import pytest

from .vts import Recorder


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    # rep.when can be either of: "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture
def vts(request):
    """defines a VTS recorder fixture which automatically records/playback http
    stubbed requests during a unittest"""
    rec = Recorder(request)
    rec.setup()
    request.addfinalizer(rec.teardown)
    return rec
