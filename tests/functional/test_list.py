import json
import os

import pytest


def test_basic_list(script):
    """
    Test default behavior of list command without format specifier.

    """
    script.pip_install_local('simple==1.0', 'simple2==3.0')
    result = script.pip_local('list')
    assert 'simple     1.0' in result.stdout, str(result)
    assert 'simple2    3.0' in result.stdout, str(result)


def test_verbose_flag(script):
    """
    Test the list command with the '-v' option
    """
    script.pip_install_local('simple==1.0', 'simple2==3.0')
    result = script.pip_local('list', '-v', '--format=columns')
    assert 'Package' in result.stdout, str(result)
    assert 'Version' in result.stdout, str(result)
    assert 'Location' in result.stdout, str(result)
    assert 'Installer' in result.stdout, str(result)
    assert 'simple     1.0' in result.stdout, str(result)
    assert 'simple2    3.0' in result.stdout, str(result)


def test_columns_flag(script):
    """
    Test the list command with the '--format=columns' option
    """
    script.pip_install_local('simple==1.0', 'simple2==3.0')
    result = script.pip_local('list', '--format=columns')
    assert 'Package' in result.stdout, str(result)
    assert 'Version' in result.stdout, str(result)
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert 'simple     1.0' in result.stdout, str(result)
    assert 'simple2    3.0' in result.stdout, str(result)


def test_format_priority(script):
    """
    Test that latest format has priority over previous ones.
    """
    script.pip_install_local('simple==1.0', 'simple2==3.0')
    result = script.pip_local('list', '--format=columns', '--format=freeze')
    assert 'simple==1.0' in result.stdout, str(result)
    assert 'simple2==3.0' in result.stdout, str(result)
    assert 'simple     1.0' not in result.stdout, str(result)
    assert 'simple2    3.0' not in result.stdout, str(result)

    result = script.pip_local('list', '--format=freeze', '--format=columns')
    assert 'Package' in result.stdout, str(result)
    assert 'Version' in result.stdout, str(result)
    assert 'simple==1.0' not in result.stdout, str(result)
    assert 'simple2==3.0' not in result.stdout, str(result)
    assert 'simple     1.0' in result.stdout, str(result)
    assert 'simple2    3.0' in result.stdout, str(result)


def test_local_flag(script):
    """
    Test the behavior of --local flag in the list command

    """
    script.pip_install_local('simple==1.0')
    result = script.pip_local('list', '--local', '--format=json')
    assert {"name": "simple", "version": "1.0"} in json.loads(result.stdout)


def test_local_columns_flag(script):
    """
    Test the behavior of --local --format=columns flags in the list command

    """
    script.pip_install_local('simple==1.0')
    result = script.pip_local('list', '--local', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'simple (1.0)' not in result.stdout
    assert 'simple     1.0' in result.stdout, str(result)


@pytest.mark.network
def test_user_flag(script):
    """
    Test the behavior of --user flag in the list command

    """
    script.pip_install_local('simple==1.0')
    script.pip_install_local('--user', 'simple2==2.0')
    result = script.pip_local('list', '--user', '--format=json')
    assert {"name": "simple", "version": "1.0"} \
        not in json.loads(result.stdout)
    assert {"name": "simple2", "version": "2.0"} in json.loads(result.stdout)


@pytest.mark.network
def test_user_columns_flag(script):
    """
    Test the behavior of --user --format=columns flags in the list command

    """
    script.pip_install_local('simple==1.0')
    script.pip_install_local('--user', 'simple2==2.0')
    result = script.pip_local('list', '--user', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'simple2 (2.0)' not in result.stdout
    assert 'simple2 2.0' in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_flag(script, pip_test_package_clone):
    """
    Test the behavior of --uptodate flag in the list command

    """
    script.pip_install_local(
        'simple==1.0', 'simple2==3.0',
        '-e', '%s#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--uptodate', '--format=json')
    assert {"name": "simple", "version": "1.0"} \
        not in json.loads(result.stdout)  # 3.0 is latest
    assert {"name": "pip-test-package", "version": "0.1.1"} \
        in json.loads(result.stdout)  # editables included
    assert {"name": "simple2", "version": "3.0"} in json.loads(result.stdout)


@pytest.mark.network
def test_uptodate_columns_flag(script, pip_test_package_clone):
    """
    Test the behavior of --uptodate --format=columns flag in the list command

    """
    script.pip_install_local(
        'simple==1.0', 'simple2==3.0', '-e',
        '%s#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--uptodate', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout      # editables included
    assert 'pip-test-package (0.1.1,' not in result.stdout
    assert 'pip-test-package 0.1.1' in result.stdout, str(result)
    assert 'simple2          3.0' in result.stdout, str(result)


@pytest.mark.network
def test_outdated_flag(script, pip_test_package_clone):
    """
    Test the behavior of --outdated flag in the list command

    """
    script.pip_install_local(
        'simple==1.0', 'simple2==3.0', 'simplewheel==1.0',
        '-e', '%s@0.1#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--outdated', '--format=json')
    assert {"name": "simple", "version": "1.0",
            "latest_version": "3.0", "latest_filetype": "sdist"} \
        in json.loads(result.stdout)
    assert dict(name="simplewheel", version="1.0",
                latest_version="2.0", latest_filetype="wheel") \
        in json.loads(result.stdout)
    assert dict(name="pip-test-package", version="0.1",
                latest_version="0.1.1", latest_filetype="sdist") \
        in json.loads(result.stdout)
    assert "simple2" not in {p["name"] for p in json.loads(result.stdout)}


@pytest.mark.network
def test_outdated_columns_flag(script, pip_test_package_clone):
    """
    Test the behavior of --outdated --format=columns flag in the list command

    """
    script.pip_install_local(
        'simple==1.0', 'simple2==3.0', 'simplewheel==1.0',
        '-e', '%s@0.1#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--outdated', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Latest' in result.stdout
    assert 'Type' in result.stdout
    assert 'simple (1.0) - Latest: 3.0 [sdist]' not in result.stdout
    assert 'simplewheel (1.0) - Latest: 2.0 [wheel]' not in result.stdout
    assert 'simple           1.0     3.0    sdist' in result.stdout, (
        str(result)
    )
    assert 'simplewheel      1.0     2.0    wheel' in result.stdout, (
        str(result)
    )
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


@pytest.mark.network
def test_editables_flag(script, pip_test_package_clone):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip_install_local(
        'simple==1.0',
        '-e', '%s#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--editable', '--format=json')
    result2 = script.pip_local('list', '--editable')
    assert {"name": "simple", "version": "1.0"} \
        not in json.loads(result.stdout)
    assert os.path.join('src', 'pip-test-package') in result2.stdout


@pytest.mark.network
def test_exclude_editable_flag(script, pip_test_package_clone):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip_install_local(
        'simple==1.0', '-e',
        '%s#egg=pip-test-package' % pip_test_package_clone
    )
    result = script.pip_local('list', '--exclude-editable', '--format=json')
    assert {"name": "simple", "version": "1.0"} in json.loads(result.stdout)
    assert "pip-test-package" \
        not in {p["name"] for p in json.loads(result.stdout)}


@pytest.mark.network
def test_editables_columns_flag(script, pip_test_package_clone):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip_install_local(
        'simple==1.0',
        '-e', '%s#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--editable', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_flag(script, pip_test_package_clone):
    """
    test the behavior of --editable --uptodate flag in the list command
    """
    script.pip_install_local(
        'simple==1.0',
        '-e', '%s#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--editable', '--uptodate')
    assert 'simple' not in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_columns_flag(script, pip_test_package_clone):
    """
    test the behavior of --editable --uptodate --format=columns flag in the
    list command
    """
    script.pip_install_local(
        'simple==1.0',
        '-e', '%s#egg=pip-test-package' % pip_test_package_clone
    )
    result = script.pip_local(
        'list', '--editable', '--uptodate', '--format=columns',
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_outdated_editables_flag(script, pip_test_package_clone):
    """
    test the behavior of --editable --outdated flag in the list command
    """
    script.pip_install_local(
        'simple==1.0',
        '-e', '%s@0.1#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--editable', '--outdated')
    assert 'simple' not in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout


@pytest.mark.network
def test_outdated_editables_columns_flag(script, pip_test_package_clone):
    """
    test the behavior of --editable --outdated flag in the list command
    """
    script.pip_install_local(
        'simple==1.0',
        '-e', '%s@0.1#egg=pip-test-package' % pip_test_package_clone,
    )
    result = script.pip_local('list', '--editable', '--outdated',
                              '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


def test_outdated_pre(script):
    script.pip_install_local('simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    wheelhouse_path.join('simple-2.0.dev0-py2.py3-none-any.whl').write('')
    result = script.pip_local('list', '--format=json', links=wheelhouse_path)
    assert {"name": "simple", "version": "1.0"} in json.loads(result.stdout)
    result = script.pip_local('list', '--format=json', '--outdated',
                              links=wheelhouse_path)
    assert {"name": "simple", "version": "1.0",
            "latest_version": "1.1", "latest_filetype": "wheel"} \
        in json.loads(result.stdout)
    result_pre = script.pip_local('list', '--outdated', '--pre',
                                  '--format=json', links=wheelhouse_path)
    assert {"name": "simple", "version": "1.0",
            "latest_version": "2.0.dev0", "latest_filetype": "wheel"} \
        in json.loads(result_pre.stdout)


def test_outdated_formats(script):
    """ Test of different outdated formats """
    script.pip_install_local('simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    result = script.pip_local('list', '--format=freeze', links=wheelhouse_path)
    assert 'simple==1.0' in result.stdout

    # Check columns
    result = script.pip_local('list', '--outdated', '--format=columns',
                              links=wheelhouse_path)
    assert 'Package Version Latest Type' in result.stdout
    assert 'simple  1.0     1.1    wheel' in result.stdout

    # Check freeze
    result = script.pip_local('list', '--outdated', '--format=freeze',
                              links=wheelhouse_path)
    assert 'simple==1.0' in result.stdout

    # Check json
    result = script.pip_local('list', '--outdated', '--format=json',
                              links=wheelhouse_path)
    data = json.loads(result.stdout)
    assert data == [{'name': 'simple', 'version': '1.0',
                     'latest_version': '1.1', 'latest_filetype': 'wheel'}]


def test_not_required_flag(script):
    script.pip_install_local('TopoRequires4')
    result = script.pip_local('list', '--not-required')
    assert 'TopoRequires4 ' in result.stdout, str(result)
    assert 'TopoRequires ' not in result.stdout
    assert 'TopoRequires2 ' not in result.stdout
    assert 'TopoRequires3 ' not in result.stdout


def test_list_freeze(script):
    """
    Test freeze formatting of list command

    """
    script.pip_install_local(
        'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip_local('list', '--format=freeze')
    assert 'simple==1.0' in result.stdout, str(result)
    assert 'simple2==3.0' in result.stdout, str(result)


def test_list_json(script):
    """
    Test json formatting of list command

    """
    script.pip_install_local(
        'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--format=json')
    data = json.loads(result.stdout)
    assert {'name': 'simple', 'version': '1.0'} in data
    assert {'name': 'simple2', 'version': '3.0'} in data
