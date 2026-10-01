"""Optional password protection. Anyone on the LAN can otherwise open the damper, run the
blower or change the set temperature. A `password` in config.json turns on HTTP Basic auth for
every request (page and API); empty means off, so an update never locks the owner out."""
import base64
import json

import pytest

from smokerpi import create_app
from smokerpi.config import Config


def make_app(password):
    config = dict(Config(test=True).defaultConfig(), password=password)
    return create_app(test_config={'config': config, 'start_worker': False})


def basic(password, username='anyone'):
    token = base64.b64encode(('%s:%s' % (username, password)).encode('utf-8')).decode()
    return {'Authorization': 'Basic ' + token}


@pytest.fixture
def locked():
    application = make_app('s3cret')
    yield application
    application.smokerpi_running = False


@pytest.fixture
def open_app():
    application = make_app('')
    yield application
    application.smokerpi_running = False


PROTECTED = [('get', '/'), ('get', '/api/state'), ('get', '/api/config'), ('get', '/api/graph'),
             ('get', '/config'), ('get', '/no/such/page'),
             ('post', '/api/blower'), ('post', '/api/damper'), ('post', '/api/pid'), ('post', '/api/config')]


class TestPasswordSet:
    @pytest.mark.parametrize('method,path', PROTECTED)
    def test_requests_without_credentials_are_refused(self, locked, method, path):
        response = getattr(locked.test_client(), method)(path, json={'enabled': True})
        assert response.status_code == 401
        assert response.headers['WWW-Authenticate'].startswith('Basic')

    def test_a_refused_request_does_not_act(self, locked):
        locked.smokerpi_blower.off()
        locked.test_client().post('/api/blower', json={'enabled': True})
        assert locked.smokerpi_blower.state == 0

    def test_a_wrong_password_is_refused(self, locked):
        response = locked.test_client().get('/api/state', headers=basic('wrong'))
        assert response.status_code == 401

    def test_malformed_authorization_headers_are_refused(self, locked):
        client = locked.test_client()
        for header in ['Basic', 'Basic !!!notbase64', 'Bearer s3cret', 'Basic ' + base64.b64encode(b'nocolon').decode()]:
            assert client.get('/api/state', headers={'Authorization': header}).status_code == 401

    def test_the_right_password_is_accepted_with_any_username(self, locked):
        client = locked.test_client()
        for username in ['anyone', '', 'smoker']:
            assert client.get('/api/state', headers=basic('s3cret', username)).status_code == 200

    def test_a_password_with_a_colon_or_non_ascii_characters_works(self):
        application = make_app('pa:ss wörd')
        try:
            assert application.test_client().get('/api/state', headers=basic('pa:ss wörd')).status_code == 200
        finally:
            application.smokerpi_running = False

    def test_controls_work_with_the_password(self, locked):
        response = locked.test_client().post('/api/blower', json={'enabled': True}, headers=basic('s3cret'))
        assert response.status_code == 200
        assert locked.smokerpi_blower.state == 100


class TestNoPassword:
    @pytest.mark.parametrize('method,path', [('get', '/api/state'), ('get', '/api/config'), ('post', '/api/blower')])
    def test_everything_is_open(self, open_app, method, path):
        response = getattr(open_app.test_client(), method)(path, json={'enabled': True})
        assert response.status_code == 200


class TestPasswordIsNeverExposed:
    @pytest.mark.parametrize('app_fixture', ['locked', 'open_app'])
    def test_no_endpoint_returns_the_password(self, request, app_fixture):
        application = request.getfixturevalue(app_fixture)
        client = application.test_client()
        headers = basic('s3cret')
        bodies = [
            client.get('/api/config', headers=headers).data,
            client.post('/api/blower', json={'enabled': False}, headers=headers).data,
            client.post('/api/damper', json={'enabled': False}, headers=headers).data,
            client.post('/api/pid', json={'enabled': False}, headers=headers).data,
            client.post('/api/config', json={'set_temperature': 120, 'damper_minimum': 500, 'damper_maximum': 2500},
                        headers=headers).data,
        ]
        for body in bodies:
            assert b'password' not in body
            assert b's3cret' not in body

    def test_it_cannot_be_changed_over_the_api(self, locked):
        locked.test_client().post('/api/config', headers=basic('s3cret'), json={
            'set_temperature': 120, 'damper_minimum': 500, 'damper_maximum': 2500, 'password': 'hacked'})
        assert locked.smokerpi_config['password'] == 's3cret'


class TestControlRequestValidation:
    @pytest.mark.parametrize('path', ['/api/blower', '/api/damper', '/api/pid'])
    @pytest.mark.parametrize('body', [None, {}, {'enabled': 'yes'}, {'enabled': None}, [1]])
    def test_a_missing_or_malformed_enabled_is_a_400_not_a_500(self, open_app, path, body):
        response = open_app.test_client().post(path, json=body)
        assert response.status_code == 400
        assert 'enabled' in json.loads(response.data)['error']

    def test_a_non_json_body_is_a_400(self, open_app):
        response = open_app.test_client().post('/api/blower', data='enabled=1')
        assert response.status_code == 400

    def test_a_bad_request_does_not_stop_the_pid(self, open_app):
        open_app.smokerpi_pidRunning = True
        open_app.test_client().post('/api/blower', json={'enabled': 'yes'})
        assert open_app.smokerpi_pidRunning is True


def test_the_default_config_has_no_password():
    assert Config(test=True).defaultConfig()['password'] == ''
