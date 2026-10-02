import os
import sys

# Make the `smokerpi` package importable regardless of how pytest is invoked
# (there is no setup.py/pyproject.toml packaging it), by putting the api/
# directory on sys.path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('SMOKERPI_TEST', '1')

import pytest

from smokerpi import create_app
from smokerpi.config import Config
from smokerpi.hardware.RPi import GPIO


def default_config():
    return Config(test=True).defaultConfig()


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """Run every test in a scratch directory. create_app writes ./log/app.log and the config
    endpoint saves ./config.json, which would otherwise land in the real api/ directory and
    overwrite a developer's local config."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def fresh_gpio():
    """The off-Pi GPIO shim keeps process-wide state, like the real library: which mode is set,
    which pins are outputs. Start every test from nothing set up, as on a freshly booted Pi."""
    GPIO.cleanup()


@pytest.fixture
def app():
    """A smokerpi Flask app with emulated hardware, no real config.json I/O,
    and no background worker thread."""
    application = create_app(test_config={'config': default_config(), 'start_worker': False})
    yield application
    application.smokerpi_running = False


@pytest.fixture
def client(app):
    return app.test_client()
