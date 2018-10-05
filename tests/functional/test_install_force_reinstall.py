
from tests.lib import assert_distributions_installed


def check_installed_version(script, package, expected):
    assert_distributions_installed(script, '%s-%s' % (package, expected))


def check_force_reinstall(script, specifier, expected):
    """
    Args:
      specifier: the requirement specifier to force-reinstall.
      expected: the expected version after force-reinstalling.
    """
    script.pip_install_local('simplewheel==1.0')
    check_installed_version(script, 'simplewheel', '1.0')

    script.pip_install_local('--force-reinstall', specifier)
    check_installed_version(script, 'simplewheel', expected)


def test_force_reinstall_with_no_version_specifier(script):
    """
    Check --force-reinstall when there is no version specifier and the
    installed version is not the newest version.
    """
    check_force_reinstall(script, 'simplewheel', '2.0')


def test_force_reinstall_with_same_version_specifier(script):
    """
    Check --force-reinstall when the version specifier equals the installed
    version and the installed version is not the newest version.
    """
    check_force_reinstall(script, 'simplewheel==1.0', '1.0')
