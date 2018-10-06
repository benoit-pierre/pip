import compileall
import io
import os
import shutil
import subprocess
import sys
from distutils.sysconfig import get_python_lib

import pytest
import six
from setuptools.wheel import Wheel

import pip._internal
from tests.lib import DATA_DIR, SRC_DIR, TestData
from tests.lib.local_repos import local_checkout
from tests.lib.path import Path
from tests.lib.scripttest import PipTestEnvironment
from tests.lib.venv import VirtualEnvironment


def pytest_addoption(parser):
    parser.addoption(
        "--keep-tmpdir", action="store_true",
        default=False, help="keep temporary test directories"
    )


def pytest_collection_modifyitems(items):
    for item in items:
        if not hasattr(item, 'module'):  # e.g.: DoctestTextfile
            continue

        # Mark network tests as flaky
        if item.get_marker('network') is not None and "CI" in os.environ:
            item.add_marker(pytest.mark.flaky(reruns=3))

        module_path = os.path.relpath(
            item.module.__file__,
            os.path.commonprefix([__file__, item.module.__file__]),
        )

        module_root_dir = module_path.split(os.pathsep)[0]
        if (module_root_dir.startswith("functional") or
                module_root_dir.startswith("integration") or
                module_root_dir.startswith("lib")):
            item.add_marker(pytest.mark.integration)
        elif module_root_dir.startswith("unit"):
            item.add_marker(pytest.mark.unit)

            # We don't want to allow using the script resource if this is a
            # unit test, as unit tests should not need all that heavy lifting
            if set(getattr(item, "funcargnames", [])) & {"script"}:
                raise RuntimeError(
                    "Cannot use the ``script`` funcarg in a unit test: "
                    "(filename = {}, item = {})".format(module_path, item)
                )
        else:
            raise RuntimeError(
                "Unknown test type (filename = {})".format(module_path)
            )


@pytest.yield_fixture
def tmpdir(request, tmpdir):
    """
    Return a temporary directory path object which is unique to each test
    function invocation, created as a sub directory of the base temporary
    directory. The returned object is a ``tests.lib.path.Path`` object.

    This uses the built-in tmpdir fixture from pytest itself but modified
    to return our typical path object instead of py.path.local as well as
    deleting the temporary directories at the end of each test case.
    """
    assert tmpdir.isdir()
    yield Path(str(tmpdir))
    # Clear out the temporary directory after the test has finished using it.
    # This should prevent us from needing a multiple gigabyte temporary
    # directory while running the tests.
    if not request.config.getoption("--keep-tmpdir"):
        tmpdir.remove(ignore_errors=True)


@pytest.fixture(autouse=True)
def isolate(tmpdir):
    """
    Isolate our tests so that things like global configuration files and the
    like do not affect our test results.

    We use an autouse function scoped fixture because we want to ensure that
    every test has it's own isolated home directory.
    """

    # TODO: Figure out how to isolate from *system* level configuration files
    #       as well as user level configuration files.

    # Create a directory to use as our home location.
    home_dir = os.path.join(str(tmpdir), "home")
    os.makedirs(home_dir)

    # Create a directory to use as a fake root
    fake_root = os.path.join(str(tmpdir), "fake-root")
    os.makedirs(fake_root)

    if sys.platform == 'win32':
        # Note: this will only take effect in subprocesses...
        home_drive, home_path = os.path.splitdrive(home_dir)
        os.environ.update({
            'USERPROFILE': home_dir,
            'HOMEDRIVE': home_drive,
            'HOMEPATH': home_path,
        })
        for env_var, sub_path in (
            ('APPDATA', 'AppData/Roaming'),
            ('LOCALAPPDATA', 'AppData/Local'),
        ):
            path = os.path.join(home_dir, *sub_path.split('/'))
            os.environ[env_var] = path
            os.makedirs(path)
    else:
        # Set our home directory to our temporary directory, this should force
        # all of our relative configuration files to be read from here instead
        # of the user's actual $HOME directory.
        os.environ["HOME"] = home_dir
        # Isolate ourselves from XDG directories
        os.environ["XDG_DATA_HOME"] = os.path.join(home_dir, ".local", "share")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(home_dir, ".config")
        os.environ["XDG_CACHE_HOME"] = os.path.join(home_dir, ".cache")
        os.environ["XDG_RUNTIME_DIR"] = os.path.join(home_dir, ".runtime")
        os.environ["XDG_DATA_DIRS"] = ":".join([
            os.path.join(fake_root, "usr", "local", "share"),
            os.path.join(fake_root, "usr", "share"),
        ])
        os.environ["XDG_CONFIG_DIRS"] = os.path.join(fake_root, "etc", "xdg")

    # Configure git, because without an author name/email git will complain
    # and cause test failures.
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    os.environ["GIT_AUTHOR_NAME"] = "pip"
    os.environ["GIT_AUTHOR_EMAIL"] = "pypa-dev@googlegroups.com"

    # We want to disable the version check from running in the tests
    os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "true"

    # Make sure tests don't share a requirements tracker.
    os.environ.pop('PIP_REQ_TRACKER', None)

    # FIXME: Windows...
    os.makedirs(os.path.join(home_dir, ".config", "git"))
    with open(os.path.join(home_dir, ".config", "git", "config"), "wb") as fp:
        fp.write(
            b"[user]\n\tname = pip\n\temail = pypa-dev@googlegroups.com\n"
        )


@pytest.fixture(scope='session')
def pip_src(tmpdir_factory):
    pip_src = Path(str(tmpdir_factory.mktemp('pip_src'))).join('pip_src')
    # Copy over our source tree so that each use is self contained
    shutil.copytree(
        SRC_DIR,
        pip_src.abspath,
        ignore=shutil.ignore_patterns(
            "*.pyc", "__pycache__", "contrib", "docs", "tasks", "*.txt",
            "tests", "pip.egg-info", "build", "dist", ".tox", ".git",
        ),
    )
    subprocess.check_call((sys.executable, 'setup.py', '-q', 'egg_info'),
                          cwd=pip_src)
    assert compileall.compile_dir(str(pip_src), quiet=1, force=True)
    return pip_src


def _common_wheel_editable_install(tmpdir_factory, common_wheels, package):
    wheel_candidates = list(common_wheels.glob('%s-*.whl' % package))
    assert len(wheel_candidates) == 1, wheel_candidates
    install_dir = Path(str(tmpdir_factory.mktemp(package))) / 'install'
    Wheel(wheel_candidates[0]).install_as_egg(install_dir)
    (install_dir / 'EGG-INFO').rename(install_dir / '%s.egg-info' % package)
    return install_dir


@pytest.fixture(scope='session')
def setuptools_install(tmpdir_factory, common_wheels):
    return _common_wheel_editable_install(tmpdir_factory,
                                          common_wheels,
                                          'setuptools')


@pytest.fixture(scope='session')
def wheel_install(tmpdir_factory, common_wheels):
    return _common_wheel_editable_install(tmpdir_factory,
                                          common_wheels,
                                          'wheel')


@pytest.yield_fixture(scope='session')
def virtualenv_template(tmpdir_factory, pip_src,
                        setuptools_install, common_wheels):

    # Create the virtual environment
    tmpdir = Path(str(tmpdir_factory.mktemp('virtualenv')))
    venv = VirtualEnvironment.create(tmpdir.join("venv_orig"))

    # Fix `site.py`.
    site_py = venv.lib / 'site.py'
    with open(site_py) as fp:
        site_contents = fp.read()
    for pattern, replace in (
        (
            # Ensure enabling user site does not result in adding
            # the real site-packages' directory to `sys.path`.
            (
                '\ndef virtual_addsitepackages(known_paths):\n'
            ),
            (
                '\ndef virtual_addsitepackages(known_paths):\n'
                '    return known_paths\n'
            ),
        ),
        (
            # Fix sites ordering: user site must be added before system site.
            (
                '\n    paths_in_sys = addsitepackages(paths_in_sys)'
                '\n    paths_in_sys = addusersitepackages(paths_in_sys)\n'
            ),
            (
                '\n    paths_in_sys = addusersitepackages(paths_in_sys)'
                '\n    paths_in_sys = addsitepackages(paths_in_sys)\n'
            ),
        ),
    ):
        assert pattern in site_contents
        site_contents = site_contents.replace(pattern, replace)
    with open(site_py, 'w') as fp:
        fp.write(site_contents)
    # Make sure bytecode is up-to-date too.
    assert compileall.compile_file(str(site_py), quiet=1, force=True)

    # Enable user site.
    (venv.lib / "no-global-site-packages.txt").rm()

    # Install setuptools/pip.
    site_packages = Path(get_python_lib(prefix=venv.location))
    with open(site_packages / 'easy-install.pth', 'w') as fp:
        fp.write(str(pip_src / 'src') + '\n' +
                 str(setuptools_install) + '\n')
    with open(site_packages / 'pip.egg-link', 'w') as fp:
        fp.write(str(pip_src / 'src') + '\n..')
    with open(site_packages / 'setuptools.egg-link', 'w') as fp:
        fp.write(str(setuptools_install) + '\n.')

    # Drop (non-relocatable) launchers.
    for exe in os.listdir(venv.bin):
        if not exe.startswith('python'):
            (venv.bin / exe).remove()

    # Create pip launcher.
    launcher_script = '; '.join((
        "import sys",
        "from pip._internal import main",
        "sys.argv[0] = 'pip'",
        "sys.exit(main())",
    ))
    if sys.platform == 'win32':
        with open(venv.bin / 'pip.bat', 'w') as fp:
            fp.write('python.exe -c %r %*' % launcher_script)
    else:
        with open(venv.bin / 'pip', 'w') as fp:
            fp.write('#!/bin/sh\nexec python -c %r "$@"' % launcher_script)
        os.chmod(venv.bin / 'pip', 0o700)

    # Rename original virtualenv directory to make sure
    # it's not reused by mistake from one of the copies.
    venv_template = tmpdir / "venv_template"
    os.rename(venv.location, venv_template)
    yield venv_template
    tmpdir.rmtree(noerrors=True)


@pytest.yield_fixture
def virtualenv(virtualenv_template, tmpdir, isolate):
    """
    Return a virtual environment which is unique to each test function
    invocation created inside of a sub directory of the test function's
    temporary directory. The returned object is a
    ``tests.lib.venv.VirtualEnvironment`` object.
    """
    venv_location = tmpdir.join("workspace", "venv")
    yield VirtualEnvironment.create(venv_location, virtualenv_template)
    venv_location.rmtree(noerrors=True)


@pytest.fixture
def with_wheel(virtualenv, wheel_install):
    site_packages = Path(get_python_lib(prefix=virtualenv.location))
    with open(site_packages / 'easy-install.pth', 'a') as fp:
        fp.write(str(wheel_install) + '\n')
    with open(site_packages / 'wheel.egg-link', 'w') as fp:
        fp.write(str(wheel_install) + '\n.')


@pytest.fixture
def script(tmpdir, virtualenv):
    """
    Return a PipTestEnvironment which is unique to each test function and
    will execute all commands inside of the unique virtual environment for this
    test function. The returned object is a
    ``tests.lib.scripttest.PipTestEnvironment``.
    """
    return PipTestEnvironment(
        # The base location for our test environment
        tmpdir.join("workspace"),

        # Tell the Test Environment where our virtualenv is located
        virtualenv=virtualenv.location,

        # Do not ignore hidden files, they need to be checked as well
        ignore_hidden=False,

        # We are starting with an already empty directory
        start_clear=False,

        # We want to ensure no temporary files are left behind, so the
        # PipTestEnvironment needs to capture and assert against temp
        capture_temp=True,
        assert_no_temp=True,
    )


@pytest.fixture(scope="session")
def common_wheels():
    """Provide a directory with latest setuptools and wheel wheels"""
    return DATA_DIR.join('common_wheels')


@pytest.fixture
def data(tmpdir):
    return TestData.copy(tmpdir.join("data"))


class InMemoryPipResult(object):
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


class InMemoryPip(object):
    def pip(self, *args):
        orig_stdout = sys.stdout
        if six.PY3:
            stdout = io.StringIO()
        else:
            stdout = io.BytesIO()
        sys.stdout = stdout
        try:
            returncode = pip._internal.main(list(args))
        except SystemExit as e:
            returncode = e.code or 0
        finally:
            sys.stdout = orig_stdout
        return InMemoryPipResult(returncode, stdout.getvalue())


@pytest.fixture
def in_memory_pip():
    return InMemoryPip()


@pytest.fixture(scope="session")
def pip_test_package_clone(tmpdir_factory):
    return local_checkout(
        'git+https://github.com/pypa/pip-test-package.git',
        Path(str(tmpdir_factory.mktemp('pip-test-package.git')))
    )
