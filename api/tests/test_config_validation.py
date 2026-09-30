import json

import pytest


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """A valid POST saves config.json relative to cwd; keep that away from the
    real (gitignored) api/config.json."""
    monkeypatch.chdir(tmp_path)


def valid_payload(**overrides):
    payload = {
        'set_temperature': 130,
        'blower_minimum': 50,
        'damper_minimum': 600,
        'damper_maximum': 2400,
    }
    payload.update(overrides)
    return payload


def current_config(client):
    return json.loads(client.get('/api/config').data)


class TestRejectsInvalidConfig:
    @pytest.mark.parametrize('field,value', [
        ('set_temperature', ''),
        ('set_temperature', 'hot'),
        ('set_temperature', None),
        ('set_temperature', True),
        ('set_temperature', 0),
        ('set_temperature', -5),
        ('blower_minimum', ''),
        ('blower_minimum', 'abc'),
        ('blower_minimum', 12.5),
        ('blower_minimum', -1),
        ('blower_minimum', 101),
        ('damper_minimum', 499),
        ('damper_maximum', 2501),
    ])
    def test_400_names_the_field_and_changes_nothing(self, client, field, value):
        before = current_config(client)

        response = client.post('/api/config', json=valid_payload(**{field: value}))

        assert response.status_code == 400
        body = json.loads(response.data)
        assert field in body['errors']
        assert field in body['error']
        assert current_config(client) == before

    def test_damper_minimum_must_be_below_maximum(self, client):
        response = client.post('/api/config', json=valid_payload(damper_minimum=2000, damper_maximum=2000))
        assert response.status_code == 400
        assert 'damper_minimum' in json.loads(response.data)['errors']

    @pytest.mark.parametrize('field', ['set_temperature', 'blower_minimum', 'damper_minimum', 'damper_maximum'])
    def test_a_missing_field_is_a_400_not_a_server_error(self, client, field):
        payload = valid_payload()
        del payload[field]
        response = client.post('/api/config', json=payload)
        assert response.status_code == 400
        assert field in json.loads(response.data)['errors']

    def test_reports_every_problem_at_once(self, client):
        response = client.post('/api/config', json=valid_payload(set_temperature='x', blower_minimum=500))
        errors = json.loads(response.data)['errors']
        assert set(errors) == {'set_temperature', 'blower_minimum'}

    @pytest.mark.parametrize('kwargs', [
        {'data': 'not json', 'content_type': 'application/json'},
        {'json': [1, 2, 3]},
        {'data': 'x=1'},
    ])
    def test_a_body_that_is_not_a_json_object_is_a_400(self, client, kwargs):
        response = client.post('/api/config', **kwargs)
        assert response.status_code == 400
        assert 'error' in json.loads(response.data)


class TestAcceptsValidConfig:
    def test_numeric_strings_are_accepted_as_the_frontend_sends_them(self, app, client):
        response = client.post('/api/config', json=valid_payload(
            set_temperature='140', blower_minimum='45', damper_minimum='550', damper_maximum='2450'))
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['set_temperature'] == 140 and isinstance(data['set_temperature'], int)
        assert app.smokerpi_pid.setpoint == 140

    def test_the_documented_limits_themselves_are_valid(self, client):
        response = client.post('/api/config', json=valid_payload(
            blower_minimum=0, damper_minimum=500, damper_maximum=2500))
        assert response.status_code == 200

    def test_read_only_settings_are_ignored_not_applied(self, client):
        before = current_config(client)
        response = client.post('/api/config', json=valid_payload(cs_pin=5, graph_interval=99, damper_pin=1))
        assert response.status_code == 200
        after = json.loads(response.data)
        for key in ('cs_pin', 'graph_interval', 'damper_pin'):
            assert after[key] == before[key]


class TestServerErrors:
    def test_an_unexpected_error_returns_500_and_is_logged(self, app, caplog):
        @app.route('/boom')
        def boom():
            raise RuntimeError('kaboom')

        response = app.test_client().get('/boom')

        assert response.status_code == 500
        assert 'kaboom' in caplog.text
