import os
import shutil
import sys

from runpip import pip, SITE_PACKAGES


def unvendor_pip():
    vendor_dir = os.path.join(SITE_PACKAGES, 'pip', '_vendor')
    vendor_init = os.path.join(vendor_dir, '__init__.py')
    if not os.path.exists(vendor_init):
        # pip's not installed yet.
        return
    with open(vendor_init) as fp:
        vendor_init_source = fp.read()
    is_vendored = '\nDEBUNDLED = False\n' in vendor_init_source
    if not is_vendored:
        # Already un-vendored.
        return
    shutil.rmtree(vendor_dir)
    os.mkdir(vendor_dir)
    with open(vendor_init, 'w') as fp:
        fp.write(vendor_init_source.replace('\nDEBUNDLED = False\n',
                                            '\nDEBUNDLED = True\n'))
    cmd = ['-q']
    if os.environ.get('WHEELS', 'no') == 'yes':
        cmd.extend('wheel --no-deps -r pip/_vendor/vendor.txt'.split()
                   + ['--wheel-dir', vendor_dir])
    else:
        cmd.extend('install --no-deps -r pip/_vendor/vendor.txt'.split())
    pip(cmd)


if __name__ == '__main__':
    # First, install requirements passed as arguments.
    pip(['install'] + sys.argv[1:])
    # And unvendor as needed.
    unvendor_pip()
