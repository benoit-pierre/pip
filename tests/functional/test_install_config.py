import textwrap


def test_options_from_env_vars(script):
    """
    Test if ConfigOptionParser reads env vars (e.g. not using PyPI here)

    """
    script.environ['PIP_NO_INDEX'] = '1'
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    assert (
        "DistributionNotFound: No matching distribution found for INITools"
        in result.stdout
    )


def test_command_line_options_override_env_vars(script, data):
    """
    Test that command line options override environmental variables.

    """
    script.environ['PIP_INDEX_URL'] = data.index_url(index='datarequire')
    result = script.pip('download', '-vvv', 'simple', expect_error=True)
    assert (
        "Looking in indexes: %s" % script.environ['PIP_INDEX_URL']
        in result.stdout
    )
    result = script.pip(
        'download', '-vvv', '--index-url', data.index_url(), 'simple',
        expect_error=True,
    )
    assert (
        "Looking in indexes: %s" % data.index_url()
        in result.stdout
    )


def test_env_vars_override_config_file(script, data):
    """
    Test that environmental variables override settings in config files.

    """
    config_file = script.scratch_path / 'pip.cfg'
    script.environ['PIP_CONFIG_FILE'] = config_file
    # It's important that we test this particular config value ('no-index')
    # because there is/was a bug which only shows up in cases in which
    # 'config-item' and 'config_item' hash to the same value modulo the size
    # of the config dictionary.
    (script.scratch_path / config_file).write(textwrap.dedent("""\
        [global]
        no-index = 1
        """))
    args = ('download', '-vvv', '-i', data.index_url(), 'simple')
    result = script.pip(*args, expect_error=True)
    assert (
        "DistributionNotFound: No matching distribution found for simple"
        in result.stdout
    )
    script.environ['PIP_NO_INDEX'] = '0'
    result = script.pip(*args)
    assert "Successfully downloaded simple" in result.stdout


def test_command_line_append_flags(script, virtualenv, data):
    """
    Test command line flags that append to defaults set by environmental
    variables.

    """
    script.environ['PIP_FIND_LINKS'] = data.find_links
    result = script.pip(
        'download', '-vvv', '--no-index', 'INITools',
    )
    assert (
        "Looking in links: %s" % data.find_links
        in result.stdout
    ), str(result)
    result = script.pip(
        'download', '-vvv', '--no-index', 'INITools',
        '--find-links', data.find_links2,
    )
    assert (
        "Looking in links: %s, %s" % (data.find_links, data.find_links2)
        in result.stdout
    ), str(result)


def test_command_line_appends_correctly(script, data):
    """
    Test multiple appending options set by environmental variables.

    """
    script.environ['PIP_FIND_LINKS'] = (
        '%s %s' % (data.find_links, data.find_links2)
    )
    result = script.pip(
        'download', '-vvv', '--no-index', 'INITools',
    )

    assert (
        "Looking in links: %s, %s" % (data.find_links, data.find_links2)
        in result.stdout
    ), result.stdout


def test_config_file_override_stack(script, virtualenv, data):
    """
    Test config files (global, overriding a global config with a
    local, overriding all with a command line flag).

    """
    config_file = script.scratch_path / 'pip.cfg'
    script.environ['PIP_CONFIG_FILE'] = config_file
    (script.scratch_path / config_file).write(textwrap.dedent("""\
        [global]
        index-url = %s
        """ % data.index_url()))
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Looking in indexes: %s" % data.index_url() in result.stdout
    virtualenv.clear()
    (script.scratch_path / config_file).write(textwrap.dedent("""\
        [global]
        index-url = https://download.zope.org/ppix
        [install]
        index-url = %s
        """ % data.index_url()))
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Looking in indexes: %s" % data.index_url() in result.stdout
    result = script.pip(
        'install', '-vvv', '--index-url', data.index_url('empty_with_pkg'),
        'INITools',
        expect_error=True,
    )
    assert "Looking in indexes: %s" % data.index_url('empty_with_pkg')


def test_options_from_venv_config(script, virtualenv):
    """
    Test if ConfigOptionParser reads a virtualenv-local config file

    """
    from pip._internal.locations import config_basename
    conf = "[global]\nno-index = true"
    ini = virtualenv.location / config_basename
    with open(ini, 'w') as f:
        f.write(conf)
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    assert (
        "DistributionNotFound: No matching distribution found for INITools"
        in result.stdout
    )


def test_install_no_binary_via_config_disables_cached_wheels(
        script, data, with_wheel):
    config_file = script.scratch_path / 'pip.cfg'
    script.environ['PIP_CONFIG_FILE'] = config_file
    config_file.write(textwrap.dedent("""\
        [global]
        no-binary = :all:
        """))
    res = script.pip(
        'install', '--no-index', '-f', data.find_links,
        'upper', expect_stderr=True)
    assert "Successfully installed upper-2.0" in str(res), str(res)
    # No wheel building for upper, which was blacklisted
    assert "Running setup.py bdist_wheel for upper" not in str(res), str(res)
    # Must have used source, not a cached wheel to install upper.
    assert "Running setup.py install for upper" in str(res), str(res)
