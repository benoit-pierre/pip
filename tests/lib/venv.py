from __future__ import absolute_import

import compileall
import os
import shutil
import sys

import virtualenv as _virtualenv

from . import virtualenv_lib_path
from .path import Path


class VirtualEnvironment(object):
    """
    An abstraction around virtual environments, currently it only uses
    virtualenv but in the future it could use pyvenv.
    """

    def __init__(self, location, template=None):
        self.location = Path(location)
        self._user_site_packages = False
        self._template = template
        home, lib, inc, bin = _virtualenv.path_locations(self.location)
        self.lib = Path(virtualenv_lib_path(home, lib))
        self.bin = Path(bin)

    def __repr__(self):
        return "<VirtualEnvironment {}>".format(self.location)

    @classmethod
    def create(cls, location, template=None):
        obj = cls(location, template)
        obj._create()
        return obj

    def _create(self, clear=False):
        if clear:
            shutil.rmtree(self.location)
        if self._template:
            # On Windows, calling `_virtualenv.path_locations(target)`
            # will have created the `target` directory...
            if sys.platform == 'win32' and os.path.exists(self.location):
                os.rmdir(self.location)
            # Clone virtual environment from template.
            shutil.copytree(self._template, self.location, symlinks=True)
        else:
            # Create a new virtual environment.
            _virtualenv.create_environment(
                self.location,
                no_pip=True,
                no_wheel=True,
                no_setuptools=True,
            )
            self._fix_site_module()

    def _fix_site_module(self):
        # Patch `site.py` so user site work as expected.
        site_py = self.lib / 'site.py'
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
                # Fix sites ordering: user site must be added before system.
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

    def clear(self):
        self._create(clear=True)

    @property
    def user_site_packages(self):
        return self._user_site_packages

    @user_site_packages.setter
    def user_site_packages(self, value):
        marker = self.lib.join("no-global-site-packages.txt")
        if value:
            marker.rm()
        else:
            marker.touch()
        self._user_site_packages = value
