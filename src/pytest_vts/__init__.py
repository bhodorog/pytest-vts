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
def vts_recorder(request):
    """create a VTS recorder in an undefined state"""
    param = getattr(request, "param", {})
    if param and not isinstance(param, dict):
        raise Exception("pytest-vts configuration error! Currently you can"
                        " configure pytest-vts's fixtures with dicts objects")
    rec = Recorder(request, param.get("basedir"), param.get("cassette_name"))
    return rec


@pytest.fixture
def vts(request, vts_recorder):
    """transform a recorder into a fixture by applying setup/teardown
    phases. Invokation of setup() flips the fixture in one of the available
    statest: recording or playing"""
    param = getattr(request, "param", {})
    if param and not isinstance(param, dict):
        raise Exception("pytest-vts configuration error! Currently you can"
                        " configure pytest-vts's fixtures with dicts objects")
    vts_recorder.setup(**param)
    request.addfinalizer(vts_recorder.teardown)
    global recorder
    recorder = vts_recorder
    return vts_recorder
