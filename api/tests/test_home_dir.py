"""config.json, log/ and data/ all live in one directory, worked out once when the app is
created: SMOKERPI_HOME if set, otherwise the directory the app was started from (api/ on the
Pi, where runserver.sh runs it). The config POST used to find config.json relative to the
working directory at the time of the request, while the history file was fixed at startup."""
import json
import os

import pytest

from smokerpi import create_app


def make_app():
    return create_app(test_config={'start_worker': False})


@pytest.fixture
def stop():
    apps = []
    yield apps.append
    for app in apps:
        app.smoker.running = False


def post_config(app):
    response = app.test_client().post('/api/config', json={
        'set_temperature': 123, 'damper_minimum': 500, 'damper_maximum': 2500})
    assert response.status_code == 200


class TestDefaultHome:
    def test_is_the_directory_the_app_started_in(self, tmp_path, stop):
        app = make_app()
        stop(app)
        assert app.smoker.home == str(tmp_path)
        assert (tmp_path / 'config.json').exists()
        assert (tmp_path / 'log' / 'app.log').exists()

    def test_a_later_change_of_directory_does_not_move_where_config_is_saved(self, tmp_path, monkeypatch, stop):
        app = make_app()
        stop(app)
        elsewhere = tmp_path / 'elsewhere'
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        post_config(app)

        assert json.loads((tmp_path / 'config.json').read_text())['set_temperature'] == 123
        assert not (elsewhere / 'config.json').exists()


class TestSmokerpiHome:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('SMOKERPI_HOME', str(home))
        return home

    def test_config_log_and_history_all_go_there(self, tmp_path, home, stop):
        app = make_app()
        stop(app)
        app.worker.step()        # records a graph point, so the history file is written

        assert app.smoker.home == str(home)
        assert (home / 'config.json').exists()
        assert (home / 'log' / 'app.log').exists()
        assert (home / 'data' / 'history.csv').exists()
        assert not (tmp_path / 'config.json').exists()
        assert not (tmp_path / 'log').exists()

    def test_the_config_post_saves_there(self, home, stop):
        app = make_app()
        stop(app)
        post_config(app)
        assert json.loads((home / 'config.json').read_text())['set_temperature'] == 123

    def test_an_existing_config_there_is_loaded(self, home, stop):
        (home / 'config.json').write_text(json.dumps({'set_temperature': 77}))
        app = make_app()
        stop(app)
        assert app.smoker.config['set_temperature'] == 77

    def test_a_relative_value_is_made_absolute_at_startup(self, tmp_path, monkeypatch, stop):
        (tmp_path / 'rel').mkdir()
        monkeypatch.setenv('SMOKERPI_HOME', 'rel')
        app = make_app()
        stop(app)
        assert app.smoker.home == str(tmp_path / 'rel')
        assert os.path.isabs(app.smoker.home)
