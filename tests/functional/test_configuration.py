"""Tests for the config command
"""

import textwrap

from pip._internal.cli.status_codes import ERROR
from tests.lib.configuration_helpers import ConfigurationMixin


def test_no_options_passed_should_error(script):
    result = script.pip('config', expect_error=True)
    assert result.returncode == ERROR


class TestBasicLoading(ConfigurationMixin):

    def test_reads_file_appropriately(self, script):

        config_file = script.scratch_path / 'config'
        with open(config_file, 'w') as fp:
            fp.write("""
                     [test]
                     hello = 1
                     """)
        script.environ['PIP_CONFIG_FILE'] = config_file

        result = script.pip("config", "list")

        assert "test.hello='1'" in result.stdout

    def test_basic_modification_pipeline(self, script):
        script.pip("config", "get", "test.blah", expect_error=True)
        script.pip("config", "set", "test.blah", "1")

        result = script.pip("config", "get", "test.blah")
        assert result.stdout.strip() == "1"

        script.pip("config", "unset", "test.blah")
        script.pip("config", "get", "test.blah", expect_error=True)

    def test_listing_is_correct(self, script):
        script.pip("config", "set", "test.listing-beta", "2")
        script.pip("config", "set", "test.listing-alpha", "1")
        script.pip("config", "set", "test.listing-gamma", "3")

        result = script.pip("config", "list")

        lines = list(filter(
            lambda x: x.startswith("test.listing-"),
            result.stdout.splitlines()
        ))

        expected = """
            test.listing-alpha='1'
            test.listing-beta='2'
            test.listing-gamma='3'
        """

        assert lines == textwrap.dedent(expected).strip().splitlines()
