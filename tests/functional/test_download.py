import os
import shlex
import textwrap

import pytest

from pip._internal.cli.status_codes import ERROR
from tests.lib import DATA_DIR
from tests.lib.path import Path


def fake_wheel(script, wheel_path):
    (
        DATA_DIR / 'packages' / 'simple.dist-0.1-py2.py3-none-any.whl'
    ).copy((script.scratch_path / 'fakes').mkdir() / wheel_path)


@pytest.mark.network
def test_download_if_requested(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip(
        'download', '-d', 'pip_downloads', 'INITools==0.1', expect_error=True
    )
    assert Path('scratch') / 'pip_downloads' / 'INITools-0.1.tar.gz' \
        in result.files_created
    assert script.site_packages / 'initools' not in result.files_created


@pytest.mark.network
def test_basic_download_setuptools(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip('download', 'setuptools')
    setuptools_prefix = str(Path('scratch') / 'setuptools')
    assert any(
        path.startswith(setuptools_prefix) for path in result.files_created
    )


def test_download_wheel(script, data):
    """
    Test using "pip download" to download a *.whl archive.
    """
    result = script.pip(
        'download',
        '--no-index',
        '-f', data.packages,
        '-d', '.', 'meta'
    )
    assert (
        Path('scratch') / 'meta-1.0-py2.py3-none-any.whl'
        in result.files_created
    )
    assert script.site_packages / 'piptestpackage' not in result.files_created


@pytest.mark.network
def test_single_download_from_requirements_file(script):
    """
    It should support download (in the scratch path) from PyPI from a
    requirements file
    """
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        INITools==0.1
        """))
    result = script.pip(
        'download', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
        expect_error=True,
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' in result.files_created
    assert script.site_packages / 'initools' not in result.files_created


@pytest.mark.network
def test_basic_download_should_download_dependencies(script):
    """
    It should download dependencies (in the scratch path)
    """
    result = script.pip(
        'download', 'Paste[openid]==1.7.5.1', '-d', '.', expect_error=True,
    )
    assert Path('scratch') / 'Paste-1.7.5.1.tar.gz' in result.files_created
    openid_tarball_prefix = str(Path('scratch') / 'python-openid-')
    assert any(
        path.startswith(openid_tarball_prefix) for path in result.files_created
    )
    assert script.site_packages / 'openid' not in result.files_created


def check_download(script, args, expected, links=DATA_DIR / 'packages'):
    result = script.pip_local('download', '-d', 'downloads', *args,
                              links=links, expect_error=not expected)
    expected = {
        os.path.join(script.scratch_path.name, 'downloads', path)
        for path in expected
    }
    # Downloads directory will be created even on failure.
    expected.add(os.path.join(script.scratch_path.name, 'downloads'))
    assert set(result.files_created.keys()) == expected


def test_download_wheel_archive(script, data):
    """
    It should download a wheel archive path
    """
    wheel_filename = 'colander-0.9.9-py2.py3-none-any.whl'
    wheel_path = '/'.join((data.find_links, wheel_filename))
    check_download(script, ('--no-deps', wheel_path), (wheel_filename,))


def test_download_should_download_wheel_deps(script, data):
    """
    It should download dependencies for wheels(in the scratch path)
    """
    wheel_filename = 'colander-0.9.9-py2.py3-none-any.whl'
    dep_filename = 'translationstring-1.1.tar.gz'
    wheel_path = '/'.join((data.find_links, wheel_filename))
    check_download(script, (wheel_path,), (wheel_filename, dep_filename))


@pytest.mark.network
def test_download_should_skip_existing_files(script):
    """
    It should not download files already existing in the scratch dir
    """
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        INITools==0.1
        """))

    result = script.pip(
        'download', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
        expect_error=True,
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' in result.files_created
    assert script.site_packages / 'initools' not in result.files_created

    # adding second package to test-req.txt
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        INITools==0.1
        python-openid==2.2.5
        """))

    # only the second package should be downloaded
    result = script.pip(
        'download', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
        expect_error=True,
    )
    openid_tarball_prefix = str(Path('scratch') / 'python-openid-')
    assert any(
        path.startswith(openid_tarball_prefix) for path in result.files_created
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' not in result.files_created
    assert script.site_packages / 'initools' not in result.files_created
    assert script.site_packages / 'openid' not in result.files_created


@pytest.mark.network
def test_download_vcs_link(script, pip_test_package_clone):
    """
    It should allow -d flag for vcs links, regression test for issue #798.
    """
    check_download(script, (pip_test_package_clone,),
                   ('pip-test-package-0.1.1.zip',))


PLATFORM_DOWNLOAD_TESTS = (

    # Confirm that specifying an interpreter/platform constraint
    # is allowed when ``--only-binary=:all:`` is set.
    ('only_binary_set_then_download_specific_platform',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --platform=linux_x86_64 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),

    # Confirm that specifying an interpreter/platform constraint
    # is allowed when ``--no-deps`` is set.
    ('no_deps_set_then_download_specific_platform',
     'fake-1.0-py2.py3-none-any.whl',
     '--no-deps --platform=linux_x86_64 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),

    # Test using "pip download --platform" to download a .whl archive
    # supported for a specific platform

    # Confirm that universal wheels are returned even for specific
    # platforms.
    ('specify_platform',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --platform=linux_x86_64 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('specify_platform',
     'fake-1.0-cp37-cp37m-linux_x86_64.whl',
     '--only-binary=:all: --platform=macosx_10_9_x86_64 -f {fakes} fake',
     ''),

    ('specify_platform',
     '''
     fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl
     fake-2.0-py2.py3-none-linux_x86_64.whl
     ''',
     '--only-binary=:all: --platform=macosx_10_10_x86_64 -f {fakes} fake',
     'fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl'),
    # OSX platform wheels are not backward-compatible.
    ('specify_platform',
     '''
     fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl
     fake-2.0-py2.py3-none-linux_x86_64.whl
     ''',
     '--only-binary=:all: --platform=macosx_10_8_x86_64 -f {fakes} fake',
     ''),
    # No linux wheel provided for this version.
    ('specify_platform',
     '''
     fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl
     fake-2.0-py2.py3-none-linux_x86_64.whl
     ''',
     '--only-binary=:all: --platform=linux_x86_64 -f {fakes} fake==1',
     ''),
    ('specify_platform',
     '''
     fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl
     fake-2.0-py2.py3-none-linux_x86_64.whl
     ''',
     '--only-binary=:all: --platform=linux_x86_64 -f {fakes} fake==2',
     'fake-2.0-py2.py3-none-linux_x86_64.whl'),

    # ('prefer_binary_when_wheel_doesnt_satisfy_req',
    #  'source-0.8-py2.py3-none-any.whl',
    #  '--prefer-binary

    # Test using "pip download --platform" to download a .whl archive
    # supported for a specific platform.

    # Confirm that universal wheels are returned even for specific
    # platforms.
    ('platform_manylinux',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --platform=linux_x86_64 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('platform_manylinux',
     'fake-1.0-py2.py3-none-manylinux1_x86_64.whl',
     '--only-binary=:all: --platform=manylinux1_x86_64 -f {fakes} fake',
     'fake-1.0-py2.py3-none-manylinux1_x86_64.whl'),
    # When specifying the platform, manylinux1 needs to be the
    # explicit platform--it won't ever be added to the compatible
    # tags.
    # FIXME: original test was wrong!
    # ('platform_manylinux',
    #  'fake-1.0-py2.py3-none-linux_x86_64.whl',
    #  '--only-binary=:all: --platform=linux_x86_64 fake',
    #  '',
    # ),

    # Test using "pip download --python-version" to download a .whl archive
    # supported for a specific interpreter
    ('specify_python_version',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --python-version=2 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('specify_python_version',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --python-version=3 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('specify_python_version',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --python-version=27 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('specify_python_version',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --python-version=33 -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('specify_python_version',
     'fake-1.0-py2-none-any.whl fake-2.0-py3-none-any.whl',
     '--only-binary=:all: --python-version=3 -f {fakes} fake==1.0',
     ''),
    ('specify_python_version',
     'fake-1.0-py2-none-any.whl fake-2.0-py3-none-any.whl',
     '--only-binary=:all: --python-version=2 -f {fakes} fake',
     'fake-1.0-py2-none-any.whl'),
    ('specify_python_version',
     'fake-1.0-py2-none-any.whl fake-2.0-py3-none-any.whl',
     '--only-binary=:all: --python-version=26 -f {fakes} fake',
     'fake-1.0-py2-none-any.whl'),
    ('specify_python_version',
     'fake-1.0-py2-none-any.whl fake-2.0-py3-none-any.whl',
     '--only-binary=:all: --python-version=3 -f {fakes} fake',
     'fake-2.0-py3-none-any.whl'),

    # Test using "pip download --abi" to download a .whl archive
    # supported for a specific abi
    ('specify_abi',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --implementation=fk --abi=fake_abi -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('specify_abi',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --implementation=fk --abi=none -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    # FIXME: another wrong test...
    # ('specify_abi',
    #  'fake-1.0-py2.py3-none-any.whl',
    #  '--only-binary=:all: --implementation=fk --abi=cp27m -f {fakes} fake',
    #  ''),
    ('specify_abi',
     'fake-1.0-fk2-fakeabi-fake_platform.whl',
     '''--only-binary=:all: --python-version=2 --implementation=fk
     --platform=fake_platform --abi=fakeabi -f {fakes} fake''',
     'fake-1.0-fk2-fakeabi-fake_platform.whl'),
    ('specify_abi',
     'fake-1.0-fk2-fakeabi-fake_platform.whl',
     '''--only-binary=:all: --implementation=fk --platform=fake_platform
     --abi=none -f {fakes} fake''',
     ''),

    # Test using "pip download --abi" to download a .whl archive
    # supported for a specific abi
    ('specify_implementation',
     'fake-1.0-py2.py3-none-any.whl',
     '--only-binary=:all: --implementation=fk -f {fakes} fake',
     'fake-1.0-py2.py3-none-any.whl'),
    ('specify_implementation',
     'fake-1.0-fk2.fk3-none-any.whl',
     '--only-binary=:all: --implementation=fk -f {fakes} fake',
     'fake-1.0-fk2.fk3-none-any.whl'),
    ('specify_implementation',
     'fake-1.0-fk3-none-any.whl',
     '''--only-binary=:all: --implementation=fk --python-version=3
     -f {fakes} fake''',
     'fake-1.0-fk3-none-any.whl'),
    ('specify_implementation',
     'fake-1.0-fk3-none-any.whl',
     '''--only-binary=:all: --implementation=fk --python-version=2
     -f {fakes} fake''',
     ''),

    ('prefer_binary_when_tarball_higher_than_wheel',
     'source-0.8-py2.py3-none-any.whl',
     '--prefer-binary -f {fakes} -f {packages} source',
     'source-0.8-py2.py3-none-any.whl'),

    ('prefer_binary_when_wheel_doesnt_satisfy_req',
     'source-0.8-py2.py3-none-any.whl',
     # Because of Windows, `source>0.9` can't be used... and no, updating the
     # workaround for `shell=True` in `PipTestEnvironment.run` is not an
     # option: it will fix this case but break one of the YAML tests...
     '--prefer-binary -f {packages} "source > 0.9"',
     'source-1.0.tar.gz'),

    ('prefer_binary_when_only_tarball_exists',
     '',
     '--prefer-binary -f {packages} source',
     'source-1.0.tar.gz'),

)


@pytest.mark.parametrize('fakes, args, downloads',
                         [t[1:] for t in PLATFORM_DOWNLOAD_TESTS],
                         ids=[t[0] for t in PLATFORM_DOWNLOAD_TESTS])
def test_download(script, fakes, args, downloads):
    fakes = fakes.split()
    for name in fakes:
        fake_wheel(script, name)
    args = [
        a.format(
            fakes=script.scratch_path / 'fakes',
            packages=DATA_DIR / 'packages',
        )
        for a in shlex.split(args)
    ]
    downloads = downloads.split()
    check_download(script, args, downloads, links=None)


def test_download_specific_platform_fails(script):
    """
    Confirm that specifying an interpreter/platform constraint
    enforces that ``--no-deps`` or ``--only-binary=:all:`` is set.
    """
    result = script.pip_local(
        'download',
        '--platform', 'linux_x86_64',
        'fake',
        expect_error=True,
    )
    assert '--only-binary=:all:' in result.stderr


def test_no_binary_set_then_download_specific_platform_fails(script):
    """
    Confirm that specifying an interpreter/platform constraint
    enforces that ``--only-binary=:all:`` is set without ``--no-binary``.
    """
    result = script.pip_local(
        'download',
        '--only-binary=:all:',
        '--no-binary=fake',
        '--platform', 'linux_x86_64',
        'fake',
        expect_error=True,
    )
    assert '--only-binary=:all:' in result.stderr


def test_download_exit_status_code_when_no_requirements(script):
    """
    Test download exit status code when no requirements specified
    """
    result = script.pip('download', expect_error=True)
    assert (
        "You must give at least one requirement to download" in result.stderr
    )
    assert result.returncode == ERROR


def test_download_exit_status_code_when_blank_requirements_file(script):
    """
    Test download exit status code when blank requirements file specified
    """
    script.scratch_path.join("blank.txt").write("\n")
    script.pip('download', '-r', 'blank.txt')
