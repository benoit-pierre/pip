from __future__ import with_statement

import logging
import os
import sys
import textwrap
from os.path import join, normpath

import pretend
import pytest

from pip._internal.req.constructors import install_req_from_line
from tests.lib import (
    assert_all_changes, assert_distributions_installed,
    create_basic_wheel_for_package, create_test_package_with_setup, need_svn,
)
from tests.lib.local_repos import local_checkout


def test_basic_uninstall(script):
    """
    Test basic install and uninstall.

    """
    pkg_path = create_basic_wheel_for_package(script.scratch_path,
                                              'pkg', '0.2')
    result = script.pip_install_local(pkg_path)
    assert_distributions_installed(script, 'pkg-0.2'), str(result)

    result = script.pip('uninstall', 'pkg', '-y')
    assert_distributions_installed(script), str(result)


def test_basic_uninstall_distutils(script):
    """
    Test basic install and uninstall.

    """
    script.scratch_path.join("distutils_install").mkdir()
    pkg_path = script.scratch_path / 'distutils_install'
    pkg_path.join("setup.py").write(textwrap.dedent("""
        from distutils.core import setup
        setup(
            name='distutils-install',
            version='0.1',
        )
    """))
    result = script.run('python', pkg_path / 'setup.py', 'install')
    assert_distributions_installed(
        script, 'distutils-install-0.1'), str(result)
    result = script.pip('uninstall', 'distutils_install', '-y',
                        expect_stderr=True, expect_error=True)
    assert (
        "Cannot uninstall 'distutils-install'. It is a distutils installed "
        "project and thus we cannot accurately determine which files belong "
        "to it which would lead to only a partial uninstall."
    ) in result.stderr


@pytest.mark.network
def test_basic_uninstall_with_scripts(script):
    """
    Uninstall an easy_installed package with scripts.

    """
    result = script.easy_install('PyLogo', expect_stderr=True)
    easy_install_pth = script.site_packages / 'easy-install.pth'
    pylogo = sys.platform == 'win32' and 'pylogo' or 'PyLogo'
    assert(pylogo in result.files_updated[easy_install_pth].bytes)
    result2 = script.pip('uninstall', 'pylogo', '-y')
    assert_all_changes(
        result,
        result2,
        [script.venv / 'build', 'cache', easy_install_pth],
    )


def test_uninstall_easy_install_after_import(script):
    """
    Uninstall an easy_installed package after it's been imported

    """
    pkg = create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.2')
    result = script.easy_install(pkg)
    assert_distributions_installed(script, 'pkg-0.2'), str(result)
    del script.environ["PYTHONDONTWRITEBYTECODE"]
    script.run('python', '-c', "import pkg")
    result = script.pip('uninstall', 'pkg', '-y')
    assert_distributions_installed(script), str(result)


def test_uninstall_trailing_newline(script):
    """
    Uninstall behaves appropriately if easy-install.pth
    lacks a trailing newline

    """
    foo_pkg = create_basic_wheel_for_package(script.scratch_path, 'foo', '0.2')
    bar_pkg = create_basic_wheel_for_package(script.scratch_path, 'bar', '3.0')

    result = script.easy_install(foo_pkg, bar_pkg)
    assert_distributions_installed(script, 'foo-0.2 bar-3.0'), str(result)

    # Trim trailing newline from easy-install.pth.
    easy_install_pth = script.site_packages_path / 'easy-install.pth'
    pth_before = easy_install_pth.read_text()
    easy_install_pth.write(pth_before.rstrip())

    # Uninstall initools.
    result = script.pip('uninstall', 'foo', '-y')
    assert_distributions_installed(script, 'bar-3.0'), str(result)

    pth_after = easy_install_pth.read_text()

    # Verify that only initools is removed.
    before_without_initools = [
        line for line in pth_before.splitlines()
        if 'foo' not in line
    ]
    lines_after = pth_after.splitlines()

    assert lines_after == before_without_initools


@pytest.mark.network
def test_basic_uninstall_namespace_package(script):
    """
    Uninstall a distribution with a namespace package without clobbering
    the namespace and everything in it.

    """
    result = script.pip('install', 'pd.requires==0.0.3', expect_error=True)
    assert join(script.site_packages, 'pd') in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('uninstall', 'pd.find', '-y', expect_error=True)
    assert join(script.site_packages, 'pd') not in result2.files_deleted, (
        sorted(result2.files_deleted.keys())
    )
    assert join(script.site_packages, 'pd', 'find') in result2.files_deleted, (
        sorted(result2.files_deleted.keys())
    )


def test_uninstall_overlapping_package(script, data):
    """
    Uninstalling a distribution that adds modules to a pre-existing package
    should only remove those added modules, not the rest of the existing
    package.

    See: GitHub issue #355 (pip uninstall removes things it didn't install)
    """
    parent_pkg = data.packages.join("parent-0.1.tar.gz")
    child_pkg = data.packages.join("child-0.1.tar.gz")

    result1 = script.pip('install', parent_pkg, expect_error=False)
    assert join(script.site_packages, 'parent') in result1.files_created, (
        sorted(result1.files_created.keys())
    )
    result2 = script.pip('install', child_pkg, expect_error=False)
    assert join(script.site_packages, 'child') in result2.files_created, (
        sorted(result2.files_created.keys())
    )
    assert normpath(
        join(script.site_packages, 'parent/plugins/child_plugin.py')
    ) in result2.files_created, sorted(result2.files_created.keys())
    # The import forces the generation of __pycache__ if the version of python
    #  supports it
    script.run('python', '-c', "import parent.plugins.child_plugin, child")
    result3 = script.pip('uninstall', '-y', 'child', expect_error=False)
    assert join(script.site_packages, 'child') in result3.files_deleted, (
        sorted(result3.files_created.keys())
    )
    assert normpath(
        join(script.site_packages, 'parent/plugins/child_plugin.py')
    ) in result3.files_deleted, sorted(result3.files_deleted.keys())
    assert join(script.site_packages, 'parent') not in result3.files_deleted, (
        sorted(result3.files_deleted.keys())
    )
    # Additional check: uninstalling 'child' should return things to the
    # previous state, without unintended side effects.
    assert_all_changes(result2, result3, [])


@pytest.mark.parametrize("console_scripts",
                         ["test_ = distutils_install",
                          "test_:test_ = distutils_install"])
def test_uninstall_entry_point(script, console_scripts):
    """
    Test uninstall package with two or more entry points in the same section,
    whose name contain a colon.
    """
    pkg_name = 'ep_install'
    pkg_path = create_test_package_with_setup(
        script,
        name=pkg_name,
        version='0.1',
        entry_points={"console_scripts": [console_scripts, ],
                      "pip_test.ep":
                      ["ep:name1 = distutils_install",
                       "ep:name2 = distutils_install"]
                      }
    )
    script_name = script.bin_path.join(console_scripts.split('=')[0].strip())
    if sys.platform == 'win32':
        script_name += '.exe'

    result = script.pip('install', pkg_path)
    assert script_name.exists, str(result)
    assert_distributions_installed(script, 'ep-install-0.1'), str(result)

    result = script.pip('uninstall', 'ep_install', '-y')
    assert not script_name.exists, str(result)
    assert_distributions_installed(script), str(result)


def test_uninstall_gui_scripts(script):
    """
    Make sure that uninstall removes gui scripts
    """
    pkg_name = "gui_pkg"
    pkg_path = create_test_package_with_setup(
        script,
        name=pkg_name,
        version='0.1',
        entry_points={"gui_scripts": ["test_ = distutils_install", ], }
    )
    script_name = script.bin_path.join('test_')
    if sys.platform == 'win32':
        script_name += '.exe'
    script.pip('install', pkg_path)
    assert script_name.exists
    script.pip('uninstall', pkg_name, '-y')
    assert not script_name.exists


@pytest.mark.network
def test_uninstall_console_scripts(script):
    """
    Test uninstalling a package with more files (console_script entry points,
    extra directories).
    """
    args = ['install']
    args.append('discover')
    result = script.pip(*args, **{"expect_error": True})
    assert script.bin / 'discover' + script.exe in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('uninstall', 'discover', '-y', expect_error=True)
    assert_all_changes(result, result2, [script.venv / 'build', 'cache'])


@pytest.mark.network
def test_uninstall_easy_installed_console_scripts(script):
    """
    Test uninstalling package with console_scripts that is easy_installed.
    """
    result = script.easy_install('discover', expect_error=True)
    assert script.bin / 'discover' + script.exe in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('uninstall', 'discover', '-y')
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'build',
            'cache',
            script.site_packages / 'easy-install.pth',
        ]
    )


@pytest.mark.network
@need_svn
def test_uninstall_editable_from_svn(script, tmpdir):
    """
    Test uninstalling an editable installation from svn.
    """
    result = script.pip(
        'install', '-e',
        '%s#egg=initools' % local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache"),
        ),
    )
    result.assert_installed('INITools')
    result2 = script.pip('uninstall', '-y', 'initools')
    assert (script.venv / 'src' / 'initools' in result2.files_after)
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'src',
            script.venv / 'build',
            script.site_packages / 'easy-install.pth'
        ],
    )


@pytest.mark.network
def test_uninstall_editable_with_source_outside_venv(
        script, tmpdir, pip_test_package_clone):
    """
    Test uninstalling editable install from existing source outside the venv.

    """
    checkout = tmpdir.join('checkout')
    script.run('git', 'clone', '-q',
               pip_test_package_clone.split('+', 1)[1],
               checkout)
    result1 = script.pip('install', '-e', checkout)
    assert join(
        script.site_packages, 'pip-test-package.egg-link'
    ) in result1.files_created, list(result1.files_created.keys())
    result2 = script.pip('uninstall', '-y',
                         'pip-test-package', expect_error=True)
    assert_all_changes(
        result1,
        result2,
        [script.venv / 'build', script.site_packages / 'easy-install.pth'],
    )


@pytest.mark.network
@need_svn
def test_uninstall_from_reqs_file(script, tmpdir):
    """
    Test uninstall from a requirements file.

    """
    script.scratch_path.join("test-req.txt").write(
        textwrap.dedent("""
            -e %s#egg=initools
            # and something else to test out:
            PyLogo<0.4
        """) %
        local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache")
        )
    )
    result = script.pip('install', '-r', 'test-req.txt')
    script.scratch_path.join("test-req.txt").write(
        textwrap.dedent("""
            # -f, -i, and --extra-index-url should all be ignored by uninstall
            -f http://www.example.com
            -i http://www.example.com
            --extra-index-url http://www.example.com

            -e %s#egg=initools
            # and something else to test out:
            PyLogo<0.4
        """) %
        local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache")
        )
    )
    result2 = script.pip('uninstall', '-r', 'test-req.txt', '-y')
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'build',
            script.venv / 'src',
            script.scratch / 'test-req.txt',
            script.site_packages / 'easy-install.pth',
        ],
    )


def test_uninstallpathset_no_paths(caplog):
    """
    Test UninstallPathSet logs notification when there are no paths to
    uninstall
    """
    from pip._internal.req.req_uninstall import UninstallPathSet
    from pkg_resources import get_distribution

    caplog.set_level(logging.INFO)

    test_dist = get_distribution('pip')
    uninstall_set = UninstallPathSet(test_dist)
    uninstall_set.remove()  # with no files added to set

    assert (
        "Can't uninstall 'pip'. No files were found to uninstall."
        in caplog.text
    )


def test_uninstall_non_local_distutils(caplog, monkeypatch, tmpdir):
    einfo = tmpdir.join("thing-1.0.egg-info")
    with open(einfo, "wb"):
        pass

    dist = pretend.stub(
        key="thing",
        project_name="thing",
        egg_info=einfo,
        location=einfo,
        _provider=pretend.stub(),
    )
    get_dist = pretend.call_recorder(lambda x: dist)
    monkeypatch.setattr("pip._vendor.pkg_resources.get_distribution", get_dist)

    req = install_req_from_line("thing")
    req.uninstall()

    assert os.path.exists(einfo)


def test_uninstall_wheel(script, data):
    """
    Test uninstalling a wheel
    """
    package = data.packages.join("simple.dist-0.1-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index')
    dist_info_folder = script.site_packages / 'simple.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created
    result2 = script.pip('uninstall', 'simple.dist', '-y')
    assert_all_changes(result, result2, [])


def test_uninstall_setuptools_develop_install(script, data):
    """Try uninstall after setup.py develop followed of setup.py install"""

    pkg_path = data.src.join("FSPkg")
    pkg_egg_link = script.site_packages / 'FSPkg.egg-link'

    result = script.run('python', 'setup.py', 'develop',
                        expect_stderr=True, cwd=pkg_path)
    assert pkg_egg_link in result.files_created, str(result)
    assert_distributions_installed(script, 'FSPkg-0.1.dev0'), str(result)

    result = script.run('python', 'setup.py', 'install',
                        expect_stderr=True, cwd=pkg_path)
    assert_distributions_installed(script, '''
                                   FSPkg-0.1.dev0
                                   FSPkg-0.1.dev0
                                   '''), str(result)

    # Uninstall both develop and install
    result = script.pip('uninstall', 'FSPkg', '-y')
    assert pkg_egg_link not in result.files_deleted, str(result)
    assert_distributions_installed(script, 'FSPkg-0.1.dev0'), str(result)

    result = script.pip('uninstall', 'FSPkg', '-y')
    assert pkg_egg_link in result.files_deleted, str(result)
    assert_distributions_installed(script), str(result)


def test_uninstall_editable_and_pip_install(script, data):
    """Try uninstall after pip install -e after pip install"""

    pkg_path = data.src.join("FSPkg")
    pkg_egg_link = script.site_packages / 'FSPkg.egg-link'

    result = script.pip('install', '-e', pkg_path)
    assert pkg_egg_link in result.files_created, str(result)
    assert_distributions_installed(script, 'FSPkg-0.1.dev0'), str(result)

    # ensure both are installed with --ignore-installed:
    script.pip('install', '--ignore-installed', pkg_path)
    assert_distributions_installed(script, '''
                                   FSPkg-0.1.dev0
                                   FSPkg-0.1.dev0
                                   '''), str(result)

    # Uninstall both develop and install
    result = script.pip('uninstall', 'FSPkg', '-y')
    assert pkg_egg_link not in result.files_deleted, str(result)
    assert_distributions_installed(script, 'FSPkg-0.1.dev0'), str(result)

    result = script.pip('uninstall', 'FSPkg', '-y')
    assert pkg_egg_link in result.files_deleted, str(result)
    assert_distributions_installed(script), str(result)


def test_uninstall_ignores_missing_packages(script):
    """Uninstall of a non existent package prints a warning and exits cleanly
    """
    result = script.pip(
        'uninstall', '-y', 'non-existent-pkg', expect_stderr=True,
    )

    assert "Skipping non-existent-pkg as it is not installed." in result.stderr
    assert result.returncode == 0, "Expected clean exit"


def test_uninstall_ignores_missing_packages_and_uninstalls_rest(script):
    script.pip_install_local('simplewheel')
    result = script.pip(
        'uninstall', '-y', 'non-existent-pkg', 'simplewheel',
        expect_stderr=True,
    )

    assert "Skipping non-existent-pkg as it is not installed." in result.stderr
    assert "Successfully uninstalled simple" in result.stdout
    assert result.returncode == 0, "Expected clean exit"
