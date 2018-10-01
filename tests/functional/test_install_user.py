"""
tests specific to "pip install --user"
"""
import os
import textwrap

import pytest

from pip._internal.utils.compat import cache_from_source, uses_pycache
from tests.lib import (
    assert_distributions_installed, create_basic_wheel_for_package,
)
from tests.lib.local_repos import local_checkout


def _patch_dist_in_site_packages(script):
    # Since the tests are run from a virtualenv, and to avoid the "Will not
    # install to the usersite because it will lack sys.path precedence..."
    # error: Monkey patch `pip._internal.req.req_install.dist_in_site_packages`
    # so it's possible to install a conflicting distribution in the user site.
    sitecustomize_path = script.lib_path.join("sitecustomize.py")
    sitecustomize_path.write(textwrap.dedent("""
        def dist_in_site_packages(dist):
            return False

        from pip._internal.req import req_install
        req_install.dist_in_site_packages = dist_in_site_packages
    """))

    # Caught py32 with an outdated __pycache__ file after a sitecustomize
    #   update (after python should have updated it) so will delete the cache
    #   file to be sure
    #   See: https://github.com/pypa/pip/pull/893#issuecomment-16426701
    if uses_pycache:
        cache_path = cache_from_source(sitecustomize_path)
        if os.path.isfile(cache_path):
            os.remove(cache_path)


class Tests_UserSite:

    def test_reset_env_system_site_packages_usersite(self, script, virtualenv):
        """
        reset_env(system_site_packages=True) produces env where a --user
        install can be found using pkg_resources
        """
        virtualenv.system_site_packages = True
        script.pip_install_local('--user', 'INITools==0.2')
        result = script.run(
            'python', '-c',
            "import pkg_resources; print(pkg_resources.get_distribution"
            "('initools').project_name)",
        )
        project_name = result.stdout.strip()
        assert 'INITools' == project_name, project_name

    @pytest.mark.network
    def test_install_subversion_usersite_editable_with_distribute(
            self, script, virtualenv, tmpdir):
        """
        Test installing current directory ('.') into usersite after installing
        distribute
        """
        virtualenv.system_site_packages = True
        result = script.pip(
            'install', '--user', '-e',
            '%s#egg=initools' %
            local_checkout(
                'svn+http://svn.colorstudy.com/INITools/trunk',
                tmpdir.join("cache"),
            )
        )
        result.assert_installed('INITools', use_user_site=True)

    def test_install_from_current_directory_into_usersite(
            self, script, virtualenv, data, with_wheel):
        """
        Test installing current directory ('.') into usersite
        """
        virtualenv.system_site_packages = True
        script.pip(
            'install', '-vvv', '--user', os.path.curdir,
            cwd=data.packages.join("FSPkg"),
        )
        assert_distributions_installed(script, user='FSPkg-0.1.dev0')

    def test_install_user_venv_nositepkgs_fails(self, script, data):
        """
        user install in virtualenv (with no system packages) fails with message
        """
        result = script.pip(
            'install', '--user', '.',
            cwd=data.packages.join("FSPkg"),
            expect_error=True,
        )
        assert (
            "Can not perform a '--user' install. User site-packages are not "
            "visible in this virtualenv." in result.stderr
        )

    def test_install_user_conflict_in_usersite(self, script, virtualenv):
        """
        Test user install with conflict in usersite updates usersite.
        """
        virtualenv.system_site_packages = True

        create_basic_wheel_for_package(script, name='INITools', version='0.1')
        create_basic_wheel_for_package(script, name='INITools', version='0.3')

        script.pip_install_local('-f', script.scratch_path,
                                 '--user', 'INITools==0.3')
        assert_distributions_installed(script, user='INITools-0.3')

        script.pip_install_local('-f', script.scratch_path,
                                 '--user', 'INITools==0.1')
        assert_distributions_installed(script, user='INITools-0.1')

    def test_install_user_conflict_in_globalsite(self, script, virtualenv):
        """
        Test user install with conflict in global site ignores site and
        installs to usersite
        """
        virtualenv.system_site_packages = True
        _patch_dist_in_site_packages(script)

        create_basic_wheel_for_package(script, name='INITools', version='0.1')
        create_basic_wheel_for_package(script, name='INITools', version='0.2')

        script.pip_install_local('-f', script.scratch_path, 'INITools==0.2')
        assert_distributions_installed(script, system='INITools-0.2')

        script.pip_install_local('-f', script.scratch_path,
                                 '--user', 'INITools==0.1')
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.1')

    def test_upgrade_user_conflict_in_globalsite(self, script, virtualenv):
        """
        Test user install/upgrade with conflict in global site ignores site and
        installs to usersite
        """
        virtualenv.system_site_packages = True
        _patch_dist_in_site_packages(script)

        create_basic_wheel_for_package(script, 'INITools', '0.2')
        create_basic_wheel_for_package(script, 'INITools', '0.3.1')

        script.pip_install_local('-f', script.scratch_path, 'INITools==0.2')
        assert_distributions_installed(script, system='INITools-0.2')
        script.pip_install_local('-f', script.scratch_path,
                                 '--user', '--upgrade', 'INITools')
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.3.1')

    def test_install_user_conflict_in_globalsite_and_usersite(
            self, script, virtualenv):
        """
        Test user install with conflict in globalsite and usersite ignores
        global site and updates usersite.
        """
        virtualenv.system_site_packages = True
        _patch_dist_in_site_packages(script)

        create_basic_wheel_for_package(script, 'INITools', '0.1')
        create_basic_wheel_for_package(script, 'INITools', '0.2')
        create_basic_wheel_for_package(script, 'INITools', '0.3')

        script.pip_install_local('-f', script.scratch_path, 'INITools==0.2')
        assert_distributions_installed(script, system='INITools-0.2')
        script.pip_install_local('-f', script.scratch_path,
                                 '--user', 'INITools==0.3')
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.3')
        script.pip_install_local('-f', script.scratch_path,
                                 '--user', 'INITools==0.1')
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.1')

    def test_install_user_in_global_virtualenv_with_conflict_fails(
            self, script, virtualenv):
        """
        Test user install in --system-site-packages virtualenv with conflict in
        site fails.
        """
        virtualenv.system_site_packages = True

        create_basic_wheel_for_package(script, 'INITools', '0.1')
        create_basic_wheel_for_package(script, 'INITools', '0.2')

        script.pip_install_local('-f', script.scratch_path, 'INITools==0.2')
        assert_distributions_installed(script, system='INITools-0.2')

        result = script.pip_install_local('-f', script.scratch_path,
                                          '--user', 'INITools==0.1',
                                          expect_error=True)
        assert_distributions_installed(script, system='INITools-0.2')
        assert (
            "Will not install to the user site because it will lack sys.path "
            "precedence to %s in %s" %
            ('INITools', script.site_packages_path.normcase) in result.stderr
        )
