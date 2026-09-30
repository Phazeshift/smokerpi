import json

from smokerpi import create_app
from smokerpi.config import Config


class TestStateEndpoint:
    def test_returns_current_hardware_state(self, client):
        response = client.get('/api/state')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {
            'temperature': 0,
            'targetTemperature': 105,
            'blower': 0,
            'pid': False,
            'damper': 99,
        }


class TestConfigEndpoint:
    def test_get_returns_current_config(self, client):
        response = client.get('/api/config')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['set_temperature'] == 105

    def test_post_updates_config_and_dependent_hardware(self, app, client):
        response = client.post('/api/config', json={
            'set_temperature': 130,
            'damper_minimum': 600,
            'damper_maximum': 2400,
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['set_temperature'] == 130
        assert app.smokerpi_pid.setpoint == 130
        assert app.smokerpi_damper.min == 600
        assert app.smokerpi_damper.max == 2400

    def test_post_persists_to_disk_without_touching_other_tests(self, tmp_path, monkeypatch):
        (tmp_path / 'log').mkdir()
        monkeypatch.chdir(tmp_path)
        application = create_app(test_config={'config': Config(test=True).defaultConfig(), 'start_worker': False})
        client = application.test_client()

        client.post('/api/config', json={
            'set_temperature': 140,
            'damper_minimum': 500,
            'damper_maximum': 2500,
        })

        assert (tmp_path / 'config.json').exists()
        saved = json.loads((tmp_path / 'config.json').read_text())
        assert saved['set_temperature'] == 140
        application.smokerpi_running = False


class TestBlowerEndpoint:
    def test_enabling_turns_blower_on(self, app, client):
        response = client.post('/api/blower', json={'enabled': True})
        assert response.status_code == 200
        assert app.smokerpi_blower.state == 100
        assert app.smokerpi_pidRunning is False

    def test_disabling_turns_blower_off(self, app, client):
        client.post('/api/blower', json={'enabled': True})
        client.post('/api/blower', json={'enabled': False})
        assert app.smokerpi_blower.state == 0


class TestDamperEndpoint:
    def test_enabling_opens_damper_fully(self, app, client):
        response = client.post('/api/damper', json={'enabled': True})
        assert response.status_code == 200
        assert app.smokerpi_damper.state == 100

    def test_disabling_closes_damper(self, app, client):
        client.post('/api/damper', json={'enabled': True})
        client.post('/api/damper', json={'enabled': False})
        assert app.smokerpi_damper.state == 0


class TestPidEndpoint:
    def test_enabling_starts_pid(self, app, client):
        response = client.post('/api/pid', json={'enabled': True})
        assert response.status_code == 200
        assert app.smokerpi_pidRunning is True
        assert app.smokerpi_pid.auto_mode is True

    def test_disabling_stops_pid_and_blower(self, app, client):
        client.post('/api/pid', json={'enabled': True})
        app.smokerpi_blower.on()
        client.post('/api/pid', json={'enabled': False})
        assert app.smokerpi_pidRunning is False
        assert app.smokerpi_pid.auto_mode is False
        assert app.smokerpi_blower.state == 0


class TestGraphEndpoint:
    def test_returns_empty_list_when_no_data_yet(self, client):
        response = client.get('/api/graph')
        assert response.status_code == 200
        assert json.loads(response.data) == []

    def test_filters_by_from_index(self, app, client):
        app.smokerpi_graphData = [
            {'i': 0, 't': 20},
            {'i': 1, 't': 21},
            {'i': 2, 't': 22},
        ]
        response = client.get('/api/graph?from=1')
        data = json.loads(response.data)
        assert [entry['i'] for entry in data] == [1, 2]
