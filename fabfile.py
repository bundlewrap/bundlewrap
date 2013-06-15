import os
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
        pylint = local("pylint " + pylint_options + " blockwart")
    if pylint.succeeded:
        print(green("pylint found no problems"))
    else:
        abort(red("pylint found problems"))
    env.warn_only = False


def run_tests(coverage=True):
    sys.path.append(PROJECT_PATH + "/src")
    with lcd(PROJECT_PATH + "/tests"):
        if coverage:
            local(
                "nosetests "
                "--with-cov --cov blockwart --cov-config ../.coveragerc"
            )
        else:
            local("nosetests")


def shell():
    os.environ['PYTHONPATH'] = PROJECT_PATH + "/src"
    local("python")


def submit_coverage():
    with lcd(PROJECT_PATH + "/tests"):
        local("coveralls")
