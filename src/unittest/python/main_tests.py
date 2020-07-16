import unittest

from dash_emulator.config import Config
from dash_emulator.main import create_parser, validate_args


class MainTest(unittest.TestCase):
    def test_parser(self):
        parser = create_parser()
        assert parser is not None

    def test_args_validation(self):
        args = {}
        assert validate_args(args) == False

        args = {"target": "hxxps://127.0.0.1/", "output": None}
        assert validate_args(args) == False

        args = {"target": "https://127.0.0.1/", "output": None}
        assert validate_args(args) == True


class ConfigTest(unittest.TestCase):
    def test_config(self):
        config = Config({})
        assert config is not None
