import textwrap
import time

import pytest

from tests.lib import (
    assert_all_changes, assert_distributions_installed,
    create_basic_wheel_for_package, pyversion,
)


def test_no_upgrade_unless_requested(script):
    """
    No upgrade if not specifically requested.

    """
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.1')
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '2.1')

    result = script.pip_install_local('pkg==0.1', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.1'), str(result)

    result = script.pip_install_local('pkg', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.1'), str(result)


def test_invalid_upgrade_strategy_causes_error(script):
    """
    It errors out when the upgrade-strategy is an invalid/unrecognised one

    """
    result = script.pip_install_local(
        '--upgrade', '--upgrade-strategy=bazinga', 'simple',
        expect_error=True
    )

    assert result.returncode
    assert "invalid choice" in result.stderr


def test_only_if_needed_does_not_upgrade_deps_when_satisfied(script):
    """
    It doesn't upgrade a dependency if it already satisfies the requirements.

    """
    create_basic_wheel_for_package(script.scratch_path, 'simple', '1.0')
    create_basic_wheel_for_package(script.scratch_path, 'simple', '2.0')
    create_basic_wheel_for_package(script.scratch_path, 'require_simple',
                                   '1.0', depends=['simple>=1.0'])

    result = script.pip_install_local('simple==1.0', links=script.scratch_path)
    assert_distributions_installed(script, system='simple-1.0'), str(result)

    result = script.pip_install_local(
        '--upgrade', '--upgrade-strategy=only-if-needed', 'require_simple',
        links=script.scratch_path)
    assert_distributions_installed(script, system='''
                                   require_simple-1.0
                                   simple-1.0
                                   '''), str(result)
    assert (
        "Requirement already satisfied, skipping upgrade: simple"
        in result.stdout
    ), str(result)


def test_only_if_needed_does_upgrade_deps_when_no_longer_satisfied(script):
    """
    It does upgrade a dependency if it no longer satisfies the requirements.

    """
    create_basic_wheel_for_package(script.scratch_path, 'simple', '1.0')
    create_basic_wheel_for_package(script.scratch_path, 'simple', '2.0')
    create_basic_wheel_for_package(script.scratch_path, 'require_simple',
                                   '1.0', depends=['simple>=2.0'])

    result = script.pip_install_local('simple==1.0', links=script.scratch_path)
    assert_distributions_installed(script, system='simple-1.0'), str(result)

    result = script.pip_install_local(
        '--upgrade', '--upgrade-strategy=only-if-needed', 'require_simple',
        links=script.scratch_path)
    assert_distributions_installed(script, system='''
                                   require_simple-1.0
                                   simple-2.0
                                   '''), str(result)


def test_eager_does_upgrade_dependencies_when_currently_satisfied(script):
    """
    It does upgrade a dependency even if it already satisfies the requirements.

    """
    create_basic_wheel_for_package(script.scratch_path, 'simple', '1.0')
    create_basic_wheel_for_package(script.scratch_path, 'simple', '2.0')
    create_basic_wheel_for_package(script.scratch_path, 'require_simple',
                                   '1.0', depends=['simple>=1.0'])

    result = script.pip_install_local('simple==1.0', links=script.scratch_path)
    assert_distributions_installed(script, system='simple-1.0'), str(result)

    result = script.pip_install_local(
        '--upgrade', '--upgrade-strategy=eager', 'require_simple',
        links=script.scratch_path)
    assert_distributions_installed(script, system='''
                                   require_simple-1.0
                                   simple-2.0
                                   '''), str(result)


def test_eager_does_upgrade_dependencies_when_no_longer_satisfied(script):
    """
    It does upgrade a dependency if it no longer satisfies the requirements.

    """
    create_basic_wheel_for_package(script.scratch_path, 'simple', '1.0')
    create_basic_wheel_for_package(script.scratch_path, 'simple', '2.0')
    create_basic_wheel_for_package(script.scratch_path, 'require_simple',
                                   '1.0', depends=['simple>=2.0'])

    result = script.pip_install_local('simple==1.0', links=script.scratch_path)
    assert_distributions_installed(script, system='simple-1.0'), str(result)

    result = script.pip_install_local(
        '--upgrade', '--upgrade-strategy=eager', 'require_simple',
        links=script.scratch_path)
    assert_distributions_installed(script, system='''
                                   require_simple-1.0
                                   simple-2.0
                                   '''), str(result)


def test_upgrade_to_specific_version(script):
    """
    It does upgrade to specific version requested.

    """
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.1')
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.2')

    result = script.pip_install_local('pkg==0.1', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.1'), str(result)

    result = script.pip_install_local('pkg==0.2', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.2'), str(result)


def test_upgrade_if_requested(script):
    """
    And it does upgrade if requested.

    """
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.1')
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.2')

    result = script.pip_install_local('pkg==0.1', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.1'), str(result)

    result = script.pip_install_local('--upgrade', 'pkg',
                                      links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.2'), str(result)


def test_upgrade_with_newest_already_installed(script, data):
    """
    If the newest version of a package is already installed, the package should
    not be reinstalled and the user should be informed.
    """
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '1.0')
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '2.0')

    result = script.pip_install_local('pkg', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-2.0'), str(result)

    result = script.pip_install_local('--upgrade', 'pkg',
                                      links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-2.0'), str(result)
    assert (
        not (result.files_created or result.files_updated) and
        'Requirement already up-to-date: pkg' in result.stdout
    ), str(result)


def test_upgrade_force_reinstall_newest(script):
    """
    Force reinstallation of a package even if it is already at its newest
    version if --force-reinstall is supplied.
    """
    def filter_files(files):
        return (f.path for f in files.values() if f.file)

    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.3')

    result1 = script.pip_install_local('pkg', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.3')

    # Update wheel timestamps.
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.3',
                                   timestamp=time.time() - 10)

    result2 = script.pip_install_local('--upgrade', '--force-reinstall', 'pkg',
                                       links=script.scratch_path)
    assert (
        set(filter_files(result2.files_updated)) ==
        set(filter_files(result1.files_created))
    )


def test_uninstall_before_upgrade(script):
    """
    Automatic uninstall-before-upgrade.

    """
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.2')
    create_basic_wheel_for_package(script.scratch_path, 'pkg', '0.3')

    script.pip_install_local('pkg==0.2', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.2')

    script.pip_install_local('pkg==0.3', links=script.scratch_path)
    assert_distributions_installed(script, system='pkg-0.3')


@pytest.mark.network
def test_uninstall_before_upgrade_from_url(script):
    """
    Automatic uninstall-before-upgrade from URL.

    """
    result = script.pip('install', 'INITools==0.2', expect_error=True)
    assert script.site_packages / 'initools' in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip(
        'install',
        'https://files.pythonhosted.org/packages/source/I/INITools/INITools-'
        '0.3.tar.gz',
        expect_error=True,
    )
    assert result2.files_created, 'upgrade to INITools 0.3 failed'
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


@pytest.mark.network
def test_upgrade_to_same_version_from_url(script):
    """
    When installing from a URL the same version that is already installed, no
    need to uninstall and reinstall if --upgrade is not specified.

    """
    result = script.pip('install', 'INITools==0.3', expect_error=True)
    assert script.site_packages / 'initools' in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip(
        'install',
        'https://files.pythonhosted.org/packages/source/I/INITools/INITools-'
        '0.3.tar.gz',
        expect_error=True,
    )
    assert not result2.files_updated, 'INITools 0.3 reinstalled same version'
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


def test_upgrade_from_reqs_file(script):
    """
    Upgrade from a requirements file.

    """
    create_basic_wheel_for_package(script.scratch_path, 'PyLogo', '0.3')
    create_basic_wheel_for_package(script.scratch_path, 'PyLogo', '0.4')
    create_basic_wheel_for_package(script.scratch_path, 'INITools', '0.3')
    create_basic_wheel_for_package(script.scratch_path, 'INITools', '0.3.1')

    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""\
        PyLogo<0.4
        # and something else to test out:
        INITools==0.3
        """))
    result = script.pip_install_local(
        '-r', script.scratch_path / 'test-req.txt',
        links=script.scratch_path,
    )
    assert_distributions_installed(script, system='''
                                   PyLogo-0.3
                                   INITools-0.3
                                   '''), str(result)

    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""\
        PyLogo
        # and something else to test out:
        INITools
        """))
    result = script.pip_install_local(
        '--upgrade', '-r', script.scratch_path / 'test-req.txt',
        links=script.scratch_path,
    )
    assert_distributions_installed(script, system='''
                                   PyLogo-0.4
                                   INITools-0.3.1
                                   '''), str(result)


def test_uninstall_rollback(script, data):
    """
    Test uninstall-rollback (using test package with a setup.py
    crafted to fail on install).

    """
    result = script.pip(
        'install', '-f', data.find_links, '--no-index', 'broken==0.1'
    )
    assert script.site_packages / 'broken.py' in result.files_created, list(
        result.files_created.keys()
    )
    result2 = script.pip(
        'install', '-f', data.find_links, '--no-index', 'broken===0.2broken',
        expect_error=True,
    )
    assert result2.returncode == 1, str(result2)
    assert script.run(
        'python', '-c', "import broken; print(broken.VERSION)"
    ).stdout == '0.1\n'
    assert_all_changes(
        result.files_after,
        result2,
        [script.venv / 'build'],
    )


@pytest.mark.network
def test_should_not_install_always_from_cache(script):
    """
    If there is an old cached package, pip should download the newer version
    Related to issue #175
    """
    script.pip('install', 'INITools==0.2', expect_error=True)
    script.pip('uninstall', '-y', 'INITools')
    result = script.pip('install', 'INITools==0.1', expect_error=True)
    assert (
        script.site_packages / 'INITools-0.2-py%s.egg-info' %
        pyversion not in result.files_created
    )
    assert (
        script.site_packages / 'INITools-0.1-py%s.egg-info' %
        pyversion in result.files_created
    )


def test_install_with_ignoreinstalled_requested(script):
    """
    Test old conflicting package is completely ignored
    """
    create_basic_wheel_for_package(script.scratch_path, 'INITools', '0.1')
    create_basic_wheel_for_package(script.scratch_path, 'INITools', '0.3')

    result = script.pip_install_local('INITools==0.1',
                                      links=script.scratch_path)
    assert_distributions_installed(script, system='INITools-0.1'), str(result)

    result = script.pip_install_local('-I', 'INITools==0.3',
                                      links=script.scratch_path)
    assert_distributions_installed(script, system='''
                                   INITools-0.1
                                   INITools-0.3
                                   '''), str(result)


@pytest.mark.network
def test_upgrade_vcs_req_with_no_dists_found(script, pip_test_package_clone):
    """It can upgrade a VCS requirement that has no distributions otherwise."""
    req = "%s#egg=pip-test-package" % pip_test_package_clone
    script.pip("install", req)
    result = script.pip("install", "-U", req)
    assert not result.returncode


@pytest.mark.network
def test_upgrade_vcs_req_with_dist_found(script):
    """It can upgrade a VCS requirement that has distributions on the index."""
    # TODO(pnasrat) Using local_checkout fails on windows - oddness with the
    # test path urls/git.
    req = (
        "%s#egg=pretend" %
        (
            "git+git://github.com/alex/pretend@e7f26ad7dbcb4a02a4995aade4"
            "743aad47656b27"
        )
    )
    script.pip("install", req, expect_stderr=True)
    result = script.pip("install", "-U", req, expect_stderr=True)
    assert "pypi.org" not in result.stdout, result.stdout
