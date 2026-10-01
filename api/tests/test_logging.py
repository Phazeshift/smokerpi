"""The app log lives on the Pi's SD card, so it must not grow without limit."""
import logging
from logging.handlers import RotatingFileHandler

import pytest

from smokerpi import create_app
from smokerpi.config import Config


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    # create_app writes ./log/app.log
    monkeypatch.chdir(tmp_path)


def make_app():
    return create_app(test_config={'config': Config(test=True).defaultConfig(), 'start_worker': False})


def file_handlers():
    return [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]


def test_the_app_log_is_a_size_limited_rotating_file(tmp_path):
    make_app()
    handlers = [h for h in file_handlers() if h.baseFilename == str(tmp_path / 'log' / 'app.log')]
    assert len(handlers) == 1
    assert isinstance(handlers[0], RotatingFileHandler)
    assert 0 < handlers[0].maxBytes <= 5 * 1024 * 1024
    assert handlers[0].backupCount >= 1


def test_creating_the_app_again_does_not_duplicate_log_lines(tmp_path):
    make_app()
    make_app()
    assert len(file_handlers()) == 1


def test_debug_noise_is_not_written(tmp_path):
    make_app()
    logging.getLogger('anything').debug('chatty debug line')
    logging.getLogger('anything').info('useful info line')
    for handler in file_handlers():
        handler.flush()
    text = (tmp_path / 'log' / 'app.log').read_text()
    assert 'chatty debug line' not in text
    assert 'useful info line' in text


def test_the_log_rotates_instead_of_growing(tmp_path):
    make_app()
    handler = file_handlers()[0]
    for _ in range(handler.backupCount + 2):
        handler.maxBytes = 1000
        logging.getLogger('anything').info('x' * 600)
        logging.getLogger('anything').info('x' * 600)
    handler.flush()
    log_dir = tmp_path / 'log'
    assert (log_dir / 'app.log.1').exists()
    assert not (log_dir / ('app.log.%d' % (handler.backupCount + 1))).exists()
