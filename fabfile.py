import os
from os.path import join
import sys

from fabric.api import *
from fabric.colors import red, green, yellow
from fabric.contrib.console import confirm

PROJECT_PATH = os.path.dirname(env.real_fabfile)


def build_docs():
    with lcd(PROJECT_PATH + "/doc"):
        local("make html")
    if confirm(
        yellow("Do you want to open index.html (Mac only)?"),
        default=False,
    ):
        with lcd(PROJECT_PATH + "/doc/_build/html"):
            local("open index.html")


def release():
    sys.path.append(PROJECT_PATH + "/src")
    from bundlewrap import VERSION_STRING
    from bundlewrap.utils import get_file_contents

    setup_py_content = get_file_contents(join(PROJECT_PATH, "setup.py"))
    if "version=\"{}\"".format(VERSION_STRING) not in setup_py_content:
        print(red("Error: bundlewrap.VERSION_STRING does not match setup.py"))
        sys.exit(1)

    changelog_content = get_file_contents(join(PROJECT_PATH, "CHANGELOG.rst"))
    if "{}\n{}".format(VERSION_STRING, "=" * len(VERSION_STRING)) not in changelog_content:
        print(red(
            "Error: no changelog entry for for {}".format(VERSION_STRING)
        ))
        sys.exit(1)

    if confirm(
        "Do you want to release BundleWrap {}?".format(VERSION_STRING),
        default=False,
    ):
        with lcd(PROJECT_PATH):
            local("python setup.py sdist upload")
            local("python setup.py bdist_wheel upload")
            local("rm -r build")

    print("")
    print("Three more steps remain:")
    print("1. Create the release on GitHub, copying the CHANGELOG entries")
    print("2. Activate building docs for the new version on ReadTheDocs")
    print("3. Announce the release on Twitter")


def run_pylint(ignore_warnings=True):
    env.warn_only = True
    pylint_installed = local("which pylint")
    if not pylint_installed.succeeded:
        abort(red("pylint not in PATH"))
    pylint_options = "--ignore=migrations "
    pylint_options += "--rcfile=../pylint.rc "
    if ignore_warnings is True:
        pylint_options += "-E "
    with lcd(PROJECT_PATH + "/src"):
        pylint = local("pylint " + pylint_options + " bundlewrap")
    if pylint.succeeded:
        print(green("pylint found no problems"))
    else:
        abort(red("pylint found problems"))
    env.warn_only = False


def run_tests(coverage=True):
    sys.path.append(PROJECT_PATH + "/src")
    os.environ['BWCOLORS'] = "0"
    with lcd(PROJECT_PATH + "/tests"):
        if coverage:
            local(
                "nosetests "
                "--with-cov --cov bundlewrap --cov-config .coveragerc 2>&1"
            )
            local("coverage combine")
            local("mv .coverage ..")
        else:
            local("nosetests")


def submit_coverage():
    local("coveralls")
