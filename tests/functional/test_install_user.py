"""
tests specific to "pip install --user"
"""
import os
import textwrap

import pytest

from tests.lib import (
    assert_distributions_installed, create_basic_wheel_for_package, need_svn,
)
from tests.lib.local_repos import local_checkout


def _patch_dist_in_site_packages(virtualenv):
    # Since the tests are run from a virtualenv, and to avoid the "Will not
    # install to the usersite because it will lack sys.path precedence..."
    # error: Monkey patch `pip._internal.req.req_install.dist_in_site_packages`
    # so it's possible to install a conflicting distribution in the user site.
    virtualenv.sitecustomize = textwrap.dedent("""
        def dist_in_site_packages(dist):
            return False

        from pip._internal.req import req_install
        req_install.dist_in_site_packages = dist_in_site_packages
    """)


class Tests_UserSite:

    def test_reset_env_system_site_packages_usersite(self, script):
        """
        Check user site works as expected.
        """
        pkg = create_basic_wheel_for_package(script, name='INITools',
                                             version='0.1')
        script.pip_install_local('--user', pkg)
        assert_distributions_installed(script, user='INITools-0.1')
        script.run('python', '-c', 'import INITools')

    @pytest.mark.network
    @need_svn
    def test_install_subversion_usersite_editable_with_distribute(
            self, script, tmpdir):
        """
        Test installing current directory ('.') into usersite after installing
        distribute
        """
        script.pip(
            'install', '--user', '-e',
            '%s#egg=initools' %
            local_checkout(
                'svn+http://svn.colorstudy.com/INITools/trunk',
                tmpdir.join("cache"),
            )
        )
        assert_distributions_installed(script, user='INITools-0.3.1.dev0')

    def test_install_from_current_directory_into_usersite(
            self, script, data, with_wheel):
        """
        Test installing current directory ('.') into usersite
        """
        script.pip(
            'install', '-vvv', '--user', os.path.curdir,
            cwd=data.packages.join("FSPkg"),
        )
        assert_distributions_installed(script, user='FSPkg-0.1.dev0')

    def test_install_user_venv_nositepkgs_fails(self, virtualenv, script):
        """
        user install in virtualenv (with no system packages) fails with message
        """
        # We can't use PYTHONNOUSERSITE, as it's not
        # honoured by virtualenv's custom site.py.
        virtualenv.user_site_packages = False
        result = script.pip(
            'install', '--user', 'simplewheel',
            expect_error=True,
        )
        assert (
            "Can not perform a '--user' install. User site-packages are not "
            "visible in this virtualenv." in result.stderr
        )

    def test_install_user_conflict_in_usersite(self, script):
        """
        Test user install with conflict in usersite updates usersite.
        """
        create_basic_wheel_for_package(script, name='INITools', version='0.1')
        create_basic_wheel_for_package(script, name='INITools', version='0.3')

        script.pip_install_local('--user', 'INITools==0.3',
                                 links=script.scratch_path)
        assert_distributions_installed(script, user='INITools-0.3')

        script.pip_install_local('--user', 'INITools==0.1',
                                 links=script.scratch_path)
        assert_distributions_installed(script, user='INITools-0.1')

    def test_install_user_conflict_in_globalsite(self, virtualenv, script):
        """
        Test user install with conflict in global site ignores site and
        installs to usersite
        """
        _patch_dist_in_site_packages(virtualenv)

        create_basic_wheel_for_package(script, name='INITools', version='0.1')
        create_basic_wheel_for_package(script, name='INITools', version='0.2')

        script.pip_install_local('INITools==0.2', links=script.scratch_path)
        assert_distributions_installed(script, system='INITools-0.2')

        script.pip_install_local('--user', 'INITools==0.1',
                                 links=script.scratch_path)
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.1')

    def test_upgrade_user_conflict_in_globalsite(self, virtualenv, script):
        """
        Test user install/upgrade with conflict in global site ignores site and
        installs to usersite
        """
        _patch_dist_in_site_packages(virtualenv)

        create_basic_wheel_for_package(script, 'INITools', '0.2')
        create_basic_wheel_for_package(script, 'INITools', '0.3.1')

        script.pip_install_local('INITools==0.2', links=script.scratch_path)
        assert_distributions_installed(script, system='INITools-0.2')
        script.pip_install_local('--user', '--upgrade', 'INITools',
                                 links=script.scratch_path)
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.3.1')

    def test_install_user_conflict_in_globalsite_and_usersite(
            self, virtualenv, script):
        """
        Test user install with conflict in globalsite and usersite ignores
        global site and updates usersite.
        """
        _patch_dist_in_site_packages(virtualenv)

        create_basic_wheel_for_package(script, 'INITools', '0.1')
        create_basic_wheel_for_package(script, 'INITools', '0.2')
        create_basic_wheel_for_package(script, 'INITools', '0.3')

        script.pip_install_local('INITools==0.2', links=script.scratch_path)
        assert_distributions_installed(script, system='INITools-0.2')
        script.pip_install_local('--user', 'INITools==0.3',
                                 links=script.scratch_path)
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.3')
        script.pip_install_local('--user', 'INITools==0.1',
                                 links=script.scratch_path)
        assert_distributions_installed(script,
                                       system='INITools-0.2',
                                       user='INITools-0.1')

    def test_install_user_in_global_virtualenv_with_conflict_fails(
            self, script):
        """
        Test user install in --system-site-packages virtualenv with conflict in
        site fails.
        """
        create_basic_wheel_for_package(script, 'INITools', '0.1')
        create_basic_wheel_for_package(script, 'INITools', '0.2')

        script.pip_install_local('INITools==0.2', links=script.scratch_path)
        assert_distributions_installed(script, system='INITools-0.2')

        result = script.pip_install_local('--user', 'INITools==0.1',
                                          links=script.scratch_path,
                                          expect_error=True)
        assert_distributions_installed(script, system='INITools-0.2')
        assert (
            "Will not install to the user site because it will lack sys.path "
            "precedence to %s in %s" %
            ('INITools', script.site_packages_path.normcase) in result.stderr
        )
