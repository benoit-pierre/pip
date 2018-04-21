import distutils
import glob
import os
import sys

import pytest

from tests.lib.path import Path


def test_install_from_future_wheel_version(script, data):
    """
    Test installing a future wheel
    """
    from tests.lib import TestFailure

    package = data.packages.join("futurewheel-3.0-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index', expect_error=True)
    with pytest.raises(TestFailure):
        result.assert_installed('futurewheel', without_egg_link=True,
                                editable=False)

    package = data.packages.join("futurewheel-1.9-py2.py3-none-any.whl")
    result = script.pip(
        'install', package, '--no-index', expect_error=False,
        expect_stderr=True,
    )
    result.assert_installed('futurewheel', without_egg_link=True,
                            editable=False)


def test_install_from_broken_wheel(script, data):
    """
    Test that installing a broken wheel fails properly
    """
    from tests.lib import TestFailure
    package = data.packages.join("brokenwheel-1.0-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index', expect_error=True)
    with pytest.raises(TestFailure):
        result.assert_installed('futurewheel', without_egg_link=True,
                                editable=False)


def test_basic_install_from_wheel(script, data):
    """
    Test installing from a wheel (that has a script)
    """
    result = script.pip(
        'install', 'has.script==1.0', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )
    dist_info_folder = script.site_packages / 'has.script-1.0.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)
    script_file = script.bin / 'script.py'
    assert script_file in result.files_created


def test_basic_install_from_wheel_with_extras(script, data):
    """
    Test installing from a wheel with extras.
    """
    result = script.pip(
        'install', 'complex-dist[simple]', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )
    dist_info_folder = script.site_packages / 'complex_dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)
    dist_info_folder = script.site_packages / 'simple.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)


def test_basic_install_from_wheel_file(script, data):
    """
    Test installing directly from a wheel file.
    """
    package = data.packages.join("simple.dist-0.1-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index', expect_error=False)
    dist_info_folder = script.site_packages / 'simple.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)
    installer = dist_info_folder / 'INSTALLER'
    assert installer in result.files_created, (dist_info_folder,
                                               result.files_created,
                                               result.stdout)
    with open(script.base_path / installer, 'rb') as installer_file:
        installer_details = installer_file.read()
        assert installer_details == b'pip\n'
    installer_temp = dist_info_folder / 'INSTALLER.pip'
    assert installer_temp not in result.files_created, (dist_info_folder,
                                                        result.files_created,
                                                        result.stdout)


# header installs are broke in pypy virtualenvs
# https://github.com/pypa/virtualenv/issues/510
@pytest.mark.skipif("hasattr(sys, 'pypy_version_info')")
def test_install_from_wheel_with_headers(script, data):
    """
    Test installing from a wheel file with headers
    """
    package = data.packages.join("headers.dist-0.1-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index', expect_error=False)
    dist_info_folder = script.site_packages / 'headers.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)


@pytest.mark.network
def test_install_wheel_with_target(script, data, wheel_installed):
    """
    Test installing a wheel using pip install --target
    """
    target_dir = script.scratch_path / 'target'
    result = script.pip(
        'install', 'simple.dist==0.1', '-t', target_dir,
        '--no-index', '--find-links=' + data.find_links,
    )
    assert Path('scratch') / 'target' / 'simpledist' in result.files_created, (
        str(result)
    )


@pytest.mark.network
def test_install_wheel_with_target_and_data_files(script, data, wheel_installed):
    """
    Test for issue #4092. It will be checked that a data_files specification in
    setup.py is handled correctly when a wheel is installed with the --target
    option.

    The setup() for the wheel 'prjwithdatafile-1.0-py2.py3-none-any.whl' is as
    follows ::

        setup(
            name='prjwithdatafile',
            version='1.0',
            packages=['prjwithdatafile'],
            data_files=[
                (r'packages1', ['prjwithdatafile/README.txt']),
                (r'packages2', ['prjwithdatafile/README.txt'])
            ]
        )
    """
    target_dir = script.scratch_path / 'prjwithdatafile'
    package = data.packages.join("prjwithdatafile-1.0-py2.py3-none-any.whl")
    result = script.pip('install', package,
                        '-t', target_dir,
                        '--no-index',
                        expect_error=False)

    assert (Path('scratch') / 'prjwithdatafile' / 'packages1' / 'README.txt'
            in result.files_created), str(result)
    assert (Path('scratch') / 'prjwithdatafile' / 'packages2' / 'README.txt'
            in result.files_created), str(result)
    assert (Path('scratch') / 'prjwithdatafile' / 'lib' / 'python'
            not in result.files_created), str(result)


def test_install_wheel_with_root(script, data):
    """
    Test installing a wheel using pip install --root
    """
    root_dir = script.scratch_path / 'root'
    result = script.pip(
        'install', 'simple.dist==0.1', '--root', root_dir,
        '--no-index', '--find-links=' + data.find_links,
    )
    assert Path('scratch') / 'root' in result.files_created


def test_install_wheel_with_prefix(script, data):
    """
    Test installing a wheel using pip install --prefix
    """
    prefix_dir = script.scratch_path / 'prefix'
    result = script.pip(
        'install', 'simple.dist==0.1', '--prefix', prefix_dir,
        '--no-index', '--find-links=' + data.find_links,
    )
    lib = distutils.sysconfig.get_python_lib(prefix=Path('scratch') / 'prefix')
    assert lib in result.files_created, str(result)


def test_install_from_wheel_installs_deps(script, data):
    """
    Test can install dependencies of wheels
    """
    # 'requires_source' depends on the 'source' project
    package = data.packages.join("requires_source-1.0-py2.py3-none-any.whl")
    result = script.pip(
        'install', '--no-index', '--find-links', data.find_links, package,
    )
    result.assert_installed('source', editable=False)


def test_install_from_wheel_no_deps(script, data):
    """
    Test --no-deps works with wheel installs
    """
    # 'requires_source' depends on the 'source' project
    package = data.packages.join("requires_source-1.0-py2.py3-none-any.whl")
    result = script.pip(
        'install', '--no-index', '--find-links', data.find_links, '--no-deps',
        package,
    )
    pkg_folder = script.site_packages / 'source'
    assert pkg_folder not in result.files_created


@pytest.mark.network
def test_install_user_wheel(script, virtualenv, data, wheel_installed):
    """
    Test user install from wheel (that has a script)
    """
    virtualenv.system_site_packages = True
    result = script.pip(
        'install', 'has.script==1.0', '--user', '--no-index',
        '--find-links=' + data.find_links,
    )
    egg_info_folder = script.user_site / 'has.script-1.0.dist-info'
    assert egg_info_folder in result.files_created, str(result)
    script_file = script.user_bin / 'script.py'
    assert script_file in result.files_created, str(result)


def test_install_from_wheel_gen_entrypoint(script, data):
    """
    Test installing scripts (entry points are generated)
    """
    result = script.pip(
        'install', 'script.wheel1a==0.1', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )
    if os.name == 'nt':
        wrapper_file = script.bin / 't1.exe'
    else:
        wrapper_file = script.bin / 't1'
    assert wrapper_file in result.files_created

    if os.name != "nt":
        assert bool(os.access(script.base_path / wrapper_file, os.X_OK))


def test_install_from_wheel_gen_uppercase_entrypoint(script, data):
    """
    Test installing scripts with uppercase letters in entry point names
    """
    result = script.pip(
        'install', 'console-scripts-uppercase==1.0', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )
    if os.name == 'nt':
        # Case probably doesn't make any difference on NT
        wrapper_file = script.bin / 'cmdName.exe'
    else:
        wrapper_file = script.bin / 'cmdName'
    assert wrapper_file in result.files_created

    if os.name != "nt":
        assert bool(os.access(script.base_path / wrapper_file, os.X_OK))


def test_install_from_wheel_with_legacy(script, data):
    """
    Test installing scripts (legacy scripts are preserved)
    """
    result = script.pip(
        'install', 'script.wheel2a==0.1', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )

    legacy_file1 = script.bin / 'testscript1.bat'
    legacy_file2 = script.bin / 'testscript2'

    assert legacy_file1 in result.files_created
    assert legacy_file2 in result.files_created


def test_install_from_wheel_no_setuptools_entrypoint(script, data):
    """
    Test that when we generate scripts, any existing setuptools wrappers in
    the wheel are skipped.
    """
    result = script.pip(
        'install', 'script.wheel1==0.1', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )
    if os.name == 'nt':
        wrapper_file = script.bin / 't1.exe'
    else:
        wrapper_file = script.bin / 't1'
    wrapper_helper = script.bin / 't1-script.py'

    # The wheel has t1.exe and t1-script.py. We will be generating t1 or
    # t1.exe depending on the platform. So we check that the correct wrapper
    # is present and that the -script.py helper has been skipped. We can't
    # easily test that the wrapper from the wheel has been skipped /
    # overwritten without getting very platform-dependent, so omit that.
    assert wrapper_file in result.files_created
    assert wrapper_helper not in result.files_created


def test_skipping_setuptools_doesnt_skip_legacy(script, data):
    """
    Test installing scripts (legacy scripts are preserved even when we skip
    setuptools wrappers)
    """
    result = script.pip(
        'install', 'script.wheel2==0.1', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )

    legacy_file1 = script.bin / 'testscript1.bat'
    legacy_file2 = script.bin / 'testscript2'
    wrapper_helper = script.bin / 't1-script.py'

    assert legacy_file1 in result.files_created
    assert legacy_file2 in result.files_created
    assert wrapper_helper not in result.files_created


def test_install_from_wheel_gui_entrypoint(script, data):
    """
    Test installing scripts (gui entry points are generated)
    """
    result = script.pip(
        'install', 'script.wheel3==0.1', '--no-index',
        '--find-links=' + data.find_links,
        expect_error=False,
    )
    if os.name == 'nt':
        wrapper_file = script.bin / 't1.exe'
    else:
        wrapper_file = script.bin / 't1'
    assert wrapper_file in result.files_created


def test_wheel_compiles_pyc(script, data):
    """
    Test installing from wheel with --compile on
    """
    script.pip(
        "install", "--compile", "simple.dist==0.1", "--no-index",
        "--find-links=" + data.find_links
    )
    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "simpledist/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "simpledist/__pycache__/__init__*.pyc"
    )

    assert any(exists)


def test_wheel_no_compiles_pyc(script, data):
    """
    Test installing from wheel with --compile on
    """
    script.pip(
        "install", "--no-compile", "simple.dist==0.1", "--no-index",
        "--find-links=" + data.find_links
    )
    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "simpledist/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "simpledist/__pycache__/__init__*.pyc"
    )

    assert not any(exists)


def test_install_from_wheel_uninstalls_old_version(script, data):
    # regression test for https://github.com/pypa/pip/issues/1825
    package = data.packages.join("simplewheel-1.0-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index', expect_error=True)
    package = data.packages.join("simplewheel-2.0-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index', expect_error=False)
    dist_info_folder = script.site_packages / 'simplewheel-2.0.dist-info'
    assert dist_info_folder in result.files_created
    dist_info_folder = script.site_packages / 'simplewheel-1.0.dist-info'
    assert dist_info_folder not in result.files_created


def test_wheel_compile_syntax_error(script, data):
    package = data.packages.join("compilewheel-1.0-py2.py3-none-any.whl")
    result = script.pip('install', '--compile', package, '--no-index')
    assert 'yield from' not in result.stdout
    assert 'SyntaxError: ' not in result.stdout
