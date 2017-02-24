import shlex
import subprocess

import pytest
import pkg_resources

import pytest_vts


@pytest.fixture
def git_describe():
    cmd = shlex.split("git describe --tags --long --match='v*'")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    described = out.decode().strip("\n")
    reversed_described = described[::-1]
    rev_gitref, rev_no_of_commits, rev_tag = reversed_described.split("-", 2)
    tag = rev_tag[::-1]
    no_of_commits = rev_no_of_commits[::-1]
    return tag, no_of_commits


def test_version_needs_bumping(git_describe):
    last_prod_tag, no_of_commits = git_describe
    pv = pkg_resources.parse_version
    err_msg_prefix = "Bump the version following PEP440 rules"
    err_msg = ("{}: bondi.__version__({}) should be > than last prod tag "
               "({})").format(err_msg_prefix,
                              pytest_vts.__version__, last_prod_tag)

    version_greater_than_tag = pv(pytest_vts.__version__) > pv(last_prod_tag)
    no_newer_commits_over_tag = no_of_commits == "0"
    assert (version_greater_than_tag or no_newer_commits_over_tag), "{}: {}".format(err_msg, "")

