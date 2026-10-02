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
        ('damper_minimum', ''),
        ('damper_minimum', 'abc'),
        ('damper_minimum', 499),
        ('damper_maximum', 12.5),
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

    @pytest.mark.parametrize('field', ['set_temperature', 'damper_minimum', 'damper_maximum'])
    def test_a_missing_field_is_a_400_not_a_server_error(self, client, field):
        payload = valid_payload()
        del payload[field]
        response = client.post('/api/config', json=payload)
        assert response.status_code == 400
        assert field in json.loads(response.data)['errors']

    def test_reports_every_problem_at_once(self, client):
        response = client.post('/api/config', json=valid_payload(set_temperature='x', damper_maximum=9999))
        errors = json.loads(response.data)['errors']
        assert set(errors) == {'set_temperature', 'damper_maximum'}

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
            set_temperature='140', damper_minimum='550', damper_maximum='2450'))
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['set_temperature'] == 140 and isinstance(data['set_temperature'], int)
        assert app.smokerpi_pid.setpoint == 140

    def test_the_documented_limits_themselves_are_valid(self, client):
        response = client.post('/api/config', json=valid_payload(
            damper_minimum=500, damper_maximum=2500))
        assert response.status_code == 200

    def test_read_only_settings_are_ignored_not_applied(self, client):
        before = current_config(client)
        response = client.post('/api/config', json=valid_payload(cs_pin=5, graph_interval=99, damper_pin=1))
        assert response.status_code == 200
        after = json.loads(response.data)
        for key in ('cs_pin', 'graph_interval', 'damper_pin'):
            assert after[key] == before[key]


class TestRemovedBlowerMinimum:
    def test_a_stale_blower_minimum_in_the_payload_is_ignored_not_rejected(self, client):
        # e.g. a browser still running the previous frontend, which posted it
        response = client.post('/api/config', json=valid_payload(blower_minimum=999))
        assert response.status_code == 200
        assert 'blower_minimum' not in json.loads(response.data)

    def test_it_is_not_reported_when_missing(self, client):
        response = client.post('/api/config', json=valid_payload(set_temperature='x'))
        assert 'blower_minimum' not in json.loads(response.data)['errors']


class TestServerErrors:
    def test_an_unexpected_error_returns_500_and_is_logged(self, app, caplog):
        @app.route('/boom')
        def boom():
            raise RuntimeError('kaboom')

        response = app.test_client().get('/boom')

        assert response.status_code == 500
        assert 'kaboom' in caplog.text


class TestPidGains:
    """pid_kp, pid_ki and pid_kd are editable and apply to the running controller at once.
    They are optional in a POST so a client that only knows the original three settings keeps
    working."""

    def test_valid_gains_apply_to_the_running_controller(self, client, app):
        response = client.post('/api/config', json=valid_payload(pid_kp=5, pid_ki=0.005, pid_kd=0))
        assert response.status_code == 200
        assert app.smokerpi_pid.tunings == (5.0, 0.005, 0.0)
        data = json.loads(response.data)
        assert (data['pid_kp'], data['pid_ki'], data['pid_kd']) == (5.0, 0.005, 0.0)

    def test_gains_sent_as_strings_are_accepted(self, client, app):
        # the web form sends strings
        response = client.post('/api/config', json=valid_payload(pid_kp='2.5', pid_ki=' 0.01 ', pid_kd='0'))
        assert response.status_code == 200
        assert app.smokerpi_pid.tunings == (2.5, 0.01, 0.0)

    def test_gains_are_saved_to_config_json(self, client, tmp_path):
        client.post('/api/config', json=valid_payload(pid_kp=5, pid_ki=0.005, pid_kd=0))
        saved = json.loads((tmp_path / 'config.json').read_text())
        assert (saved['pid_kp'], saved['pid_ki'], saved['pid_kd']) == (5.0, 0.005, 0.0)

    def test_omitting_them_leaves_the_gains_alone(self, client, app):
        client.post('/api/config', json=valid_payload(pid_kp=5))
        response = client.post('/api/config', json=valid_payload())
        assert response.status_code == 200
        assert app.smokerpi_pid.tunings[0] == 5.0

    def test_a_partial_set_changes_only_the_ones_given(self, client, app):
        client.post('/api/config', json=valid_payload(pid_ki=0.02))
        assert app.smokerpi_pid.tunings == (1, 0.02, 0.05)

    @pytest.mark.parametrize('field,value', [
        ('pid_kp', ''), ('pid_kp', 'fast'), ('pid_kp', None), ('pid_kp', True), ('pid_kp', -1),
        ('pid_kp', 'nan'), ('pid_kp', 'inf'), ('pid_kp', float('inf')), ('pid_kp', 101),
        ('pid_ki', -0.1), ('pid_ki', 11), ('pid_ki', '1e999'),
        ('pid_kd', -5), ('pid_kd', 101), ('pid_kd', [1]),
    ])
    def test_invalid_gains_are_a_400_naming_the_field_and_change_nothing(self, client, app, field, value):
        before = current_config(client)
        gains = app.smokerpi_pid.tunings

        response = client.post('/api/config', json=valid_payload(**{field: value}))

        assert response.status_code == 400
        assert field in json.loads(response.data)['errors']
        assert current_config(client) == before
        assert app.smokerpi_pid.tunings == gains

    def test_one_bad_gain_stops_the_valid_settings_in_the_same_post_applying(self, client):
        before = current_config(client)
        client.post('/api/config', json=valid_payload(set_temperature=200, pid_kp=-1))
        assert current_config(client) == before

    def test_zero_is_allowed(self, client, app):
        assert client.post('/api/config', json=valid_payload(pid_kp=0, pid_ki=0, pid_kd=0)).status_code == 200
        assert app.smokerpi_pid.tunings == (0, 0, 0)


class FakeDamper:
    def __init__(self, fail=False):
        self.invert = False
        self.min, self.max = 500, 2500
        self.state = 99
        self.repositioned = 0
        self.fail = fail

    def reposition(self):
        self.repositioned += 1
        if self.fail:
            raise OSError('pigpiod is down')

    def open(self, value):
        self.state = value


class TestDamperInvert:
    """damper_invert is optional in a POST (older clients do not send it), applies at once and
    moves the physical damper so it matches the new mapping."""

    def test_the_default_is_not_inverted(self, client, app):
        assert current_config(client)['damper_invert'] is False
        assert app.smokerpi_damper.invert is False

    def test_setting_it_applies_saves_and_returns_it(self, client, app, tmp_path):
        response = client.post('/api/config', json=valid_payload(damper_invert=True))
        assert response.status_code == 200
        assert json.loads(response.data)['damper_invert'] is True
        assert app.smokerpi_damper.invert is True
        assert json.loads((tmp_path / 'config.json').read_text())['damper_invert'] is True

    def test_it_can_be_turned_off_again(self, client, app):
        client.post('/api/config', json=valid_payload(damper_invert=True))
        client.post('/api/config', json=valid_payload(damper_invert=False))
        assert app.smokerpi_damper.invert is False

    def test_omitting_it_leaves_it_alone(self, client, app):
        client.post('/api/config', json=valid_payload(damper_invert=True))
        client.post('/api/config', json=valid_payload())
        assert app.smokerpi_damper.invert is True

    @pytest.mark.parametrize('value', ['yes', 'true', 1, 0, None, [True]])
    def test_anything_but_a_boolean_is_a_400_and_changes_nothing(self, client, app, value):
        before = current_config(client)
        response = client.post('/api/config', json=valid_payload(damper_invert=value))
        assert response.status_code == 400
        assert 'damper_invert' in json.loads(response.data)['errors']
        assert current_config(client) == before
        assert app.smokerpi_damper.invert is False

    def test_changing_it_moves_the_damper_to_match(self, client, app):
        app.smokerpi_damper = FakeDamper()
        client.post('/api/config', json=valid_payload(damper_invert=True))
        assert app.smokerpi_damper.repositioned == 1

    def test_posting_the_same_value_does_not_move_the_damper(self, client, app):
        app.smokerpi_damper = FakeDamper()
        client.post('/api/config', json=valid_payload(damper_invert=False))
        client.post('/api/config', json=valid_payload())
        assert app.smokerpi_damper.repositioned == 0

    def test_a_failed_move_is_reported_but_the_setting_is_kept(self, client, app, tmp_path):
        app.smokerpi_damper = FakeDamper(fail=True)
        response = client.post('/api/config', json=valid_payload(damper_invert=True))
        assert response.status_code == 500
        assert 'damper' in json.loads(response.data)['error'].lower()
        assert 'pigpiod is down' in json.loads(response.data)['error']
        assert current_config(client)['damper_invert'] is True
        assert json.loads((tmp_path / 'config.json').read_text())['damper_invert'] is True

    def test_the_app_starts_with_the_configured_setting(self):
        from smokerpi import create_app
        from smokerpi.config import Config
        config = dict(Config(test=True).defaultConfig(), damper_invert=True)
        app = create_app(test_config={'config': config, 'start_worker': False})
        try:
            assert app.smokerpi_damper.invert is True
        finally:
            app.smokerpi_running = False


class TestFieldDescriptions:
    """GET /api/config also says which settings the Config page should show, and how."""

    def fields(self, client):
        return {f['name']: f for f in current_config(client)['fields']}

    def test_describes_each_editable_and_read_only_setting(self, client):
        fields = self.fields(client)
        assert fields['set_temperature'] == {
            'name': 'set_temperature', 'label': 'Target temperature', 'kind': 'whole', 'help': None}
        assert fields['pid_kp']['kind'] == 'gain'
        assert fields['damper_invert']['kind'] == 'bool'
        assert 'smaller pulse width' in fields['damper_invert']['help']
        assert fields['cs_pin']['kind'] is None

    def test_leaves_out_settings_that_are_not_for_display(self, client):
        fields = self.fields(client)
        for name in ('password', 'worker_interval', 'sensor_timeout', 'history_max_mb'):
            assert name not in fields

    def test_only_describes_settings_the_config_has(self, app, client):
        del app.smokerpi_config['pid_kp']
        assert 'pid_kp' not in self.fields(client)

    def test_a_leftover_setting_with_no_field_is_not_described(self, app, client):
        app.smokerpi_config['blower_minimum'] = 40
        assert 'blower_minimum' not in self.fields(client)

    def test_the_post_response_has_them_too(self, client):
        response = client.post('/api/config', json=valid_payload())
        assert 'fields' in json.loads(response.data)
