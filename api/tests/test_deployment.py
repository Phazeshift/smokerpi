"""Guards for how the app is started in production.

Flask 2.0's app.run() loads .flaskenv itself and, when FLASK_ENV is set, turns debug
mode back on, overriding `app.debug = False`. That exposed the interactive Werkzeug
debugger (/console) on the Pi's LAN address. These tests keep that from coming back."""
import ast
import os

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def read_flaskenv():
    with open(os.path.join(API_DIR, '.flaskenv')) as f:
        return dict(
            line.strip().split('=', 1) for line in f
            if '=' in line and not line.lstrip().startswith('#')
        )


class TestFlaskEnvFile:
    """.flaskenv is shipped in the release bundle and copied onto the Pi."""

    def test_does_not_enable_development_mode(self):
        env = read_flaskenv()
        assert env.get('FLASK_ENV') != 'development'
        assert 'FLASK_ENV' not in env

    def test_does_not_enable_debug(self):
        assert read_flaskenv().get('FLASK_DEBUG', '0').lower() in ('0', 'false', '')

    def test_still_names_the_app_for_the_flask_cli(self):
        assert read_flaskenv().get('FLASK_APP') == 'smokerpi'


class TestRunserver:
    def run_call(self):
        with open(os.path.join(API_DIR, 'runserver.py')) as f:
            tree = ast.parse(f.read())
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'run'
        ]
        assert len(calls) == 1, 'expected exactly one app.run(...) call'
        return {kw.arg: kw.value for kw in calls[0].keywords}

    def test_passes_debug_false_explicitly(self):
        # An explicit debug argument overrides everything else, including FLASK_ENV.
        debug = self.run_call().get('debug')
        assert isinstance(debug, ast.Constant) and debug.value is False

    def test_does_not_load_dotenv_files(self):
        load = self.run_call().get('load_dotenv')
        assert isinstance(load, ast.Constant) and load.value is False

    def test_listens_on_all_interfaces_as_before(self):
        host = self.run_call().get('host')
        assert isinstance(host, ast.Constant) and host.value == '0.0.0.0'
