import shlex
import subprocess

import pytest
import pkg_resources

import pytest_vts


@pytest.fixture
def last_prod_tag():
    cmd = shlex.split("git describe --tags --abbrev=0 --match='v*'")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return out.decode().strip("\n")


def test_version_needs_bumping(last_prod_tag):
    pv = pkg_resources.parse_version
    err_msg = ("Bump the version following PEP440 rules")
    assert pv(pytest_vts.__version__) > pv(last_prod_tag), err_msg


