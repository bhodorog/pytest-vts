import pytest

from .vts import Recorder
from .version import __version__  # noqa

recorder = None


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    # rep.when can be either of: "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture
def vts(request, basedir=None, cassette_name=None):
    """defines a VTS recorder fixture which automatically records/playback http
    stubbed requests during a unittest"""
    args, kwargs = [], {}
    param = getattr(request, "param", None)
    if isinstance(param, dict):
        kwargs = param
    elif any((isinstance(param, col_klass)
              for col_klass in [list, tuple])):
        args = param
    elif param:
        args = [param]
    else:
        args = [basedir, cassette_name]
    rec = Recorder(request, *args, **kwargs)
    rec.setup()
    request.addfinalizer(rec.teardown)
    global recorder
    recorder = rec
    return rec
