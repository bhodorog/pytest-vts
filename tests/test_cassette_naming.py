import pytest
import tempfile
from pytest_vts.logic.machine import class_function_name


@pytest.mark.parametrize(
    "vts",
    [{"basedir": tempfile.gettempdir(), "cassette_name": "expected_name"}, ],
    indirect=["vts"],
    ids=["kwargs"])
def test_vts_custom_name(vts):
    assert vts.cassette_name == "expected_name"
    assert vts._cass_dir == tempfile.gettempdir()


def test_method(vts):
    assert test_method.__name__ in vts.cassette_name


@pytest.mark.parametrize("vts", [{"cassette_name": class_function_name}], indirect=["vts"])
class TestNamespace(object):
    def test_method(self, vts):
        assert self.__class__.__name__ in vts.cassette_name
        assert self.test_method.__name__ in vts.cassette_name

    @pytest.mark.parametrize("one", map(str, range(3)))
    def test_parametrize(self, vts, one):
        assert self.__class__.__name__ in vts.cassette_name
        assert self.test_parametrize.__name__ in vts.cassette_name
        assert one in vts.cassette_name


@pytest.mark.parametrize("one", map(str, range(3)))
def test_method_parametrize(vts, one):
    assert test_method_parametrize.__name__ in vts.cassette_name
    assert one in vts.cassette_name


@pytest.mark.parametrize("one", map(str, range(3)))
@pytest.mark.parametrize("vts", [{"cassette_name": class_function_name}], indirect=["vts"])
class TestParametrize(object):
    def test_method(self, vts, one):
        assert self.__class__.__name__ in vts.cassette_name
        assert test_method.__name__ in vts.cassette_name
        assert one in vts.cassette_name
