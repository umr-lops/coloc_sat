#!/usr/bin/env python

"""Tests for `sar_coloc` package."""


import unittest
from click.testing import CliRunner

from sar_coloc import sar_coloc
from sar_coloc import cli


class TestSar_coloc(unittest.TestCase):
    """Tests for `sar_coloc` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_000_something(self):
        """Test something."""

    def test_command_line_interface(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.main)
        assert result.exit_code == 0
        assert 'sar_coloc.cli.main' in result.output
        help_result = runner.invoke(cli.main, ['--help'])
        assert help_result.exit_code == 0
        assert '--help  Show this message and exit.' in help_result.output
