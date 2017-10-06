import os
import shutil
import subprocess
import sys


TOX_PIP_DIR = os.path.join(os.environ['VIRTUAL_ENV'], 'pip')


def pip(args):
    # First things first, safeguard the environment
    # original pip so it can be used for all calls.
    if not os.path.exists(TOX_PIP_DIR):
        # Install latest release of pip.
        cmd = (
            [sys.executable] +
            '-m pip install -t'.split() +
            [TOX_PIP_DIR, 'pip']
        )
        subprocess.check_call(cmd)
        # Uninstall currently installed version.
        cmd = (
            [sys.executable] +
            '-m pip uninstall -y pip'.split()
        )
        subprocess.check_call(cmd)
        # Create a very simple launcher that
        # can be used for Linux and Windows.
        with open(os.path.join(TOX_PIP_DIR, 'pip.py'), 'w') as fp:
            fp.write('from pip import main; main()')
    # And use a temporary copy of that version
    # so it can uninstall itself if needed.
    temp_pip = TOX_PIP_DIR + '.tmp'
    try:
        shutil.copytree(TOX_PIP_DIR, temp_pip)
        cmd = [sys.executable, os.path.join(temp_pip, 'pip.py')]
        cmd.extend(args)
        subprocess.check_call(cmd)
    finally:
        shutil.rmtree(temp_pip)


if __name__ == '__main__':
    pip(sys.argv[1:])
