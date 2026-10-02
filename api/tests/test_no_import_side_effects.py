"""Importing smokerpi must not start anything.

`smokerpi/__init__.py` used to end with `app = create_app()`, so merely importing any part of
the package (`from smokerpi.config import Config`, `smokerpi.hardware.blower`, ...) read and
wrote config.json, created log/, built the hardware objects and started the worker thread.
Every test module therefore ran a real app with a live worker, which wrote into whichever
directory the tests were in at the time. The app is now only built by create_app(), called by
runserver.py (or `flask run`, which finds the factory itself)."""
import json
import os
import signal
import subprocess
import sys

import pytest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def in_a_clean_interpreter(tmp_path, code):
    """Run `code` in a fresh Python started in an empty directory; return its JSON result."""
    env = dict(os.environ, PYTHONPATH=API_DIR, SMOKERPI_TEST='1')
    result = subprocess.run([sys.executable, '-c', code], cwd=str(tmp_path), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


REPORT = "import json, os, threading; print(json.dumps({'threads': threading.active_count(), 'files': sorted(os.listdir('.'))}))"


class TestImporting:
    @pytest.mark.parametrize('imports', [
        'import smokerpi',
        'import smokerpi, smokerpi.config',
        'import smokerpi.hardware.blower, smokerpi.hardware.damper2, smokerpi.hardware.max31855',
        'from smokerpi import create_app',
    ])
    def test_starts_no_threads_and_writes_no_files(self, tmp_path, imports):
        report = in_a_clean_interpreter(tmp_path, imports + '; ' + REPORT)
        assert report == {'threads': 1, 'files': []}

    def test_there_is_no_module_level_app(self, tmp_path):
        code = "import json, smokerpi; print(json.dumps([hasattr(smokerpi, 'app'), hasattr(smokerpi, 'cleanupHardware')]))"
        assert in_a_clean_interpreter(tmp_path, code) == [False, False]

    def test_importing_runserver_starts_nothing_either(self, tmp_path):
        report = in_a_clean_interpreter(tmp_path, 'import runserver; ' + REPORT)
        assert report == {'threads': 1, 'files': []}

    def test_create_app_is_still_the_factory_flask_finds(self, tmp_path):
        # `flask run` (yarn start-api2) is told FLASK_APP=smokerpi and must find create_app
        code = ("import json; from flask.cli import ScriptInfo; "
                "app = ScriptInfo(app_import_path='smokerpi').load_app(); "
                "print(json.dumps(sorted(r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/'))[:3]))")
        rules = in_a_clean_interpreter(tmp_path, code)
        assert rules[0].startswith('/api/')


class TestRunserverMain:
    """What runserver.py wires up when it is run, without starting a real server."""

    @pytest.fixture
    def started(self, monkeypatch):
        import runserver
        events = {'exits': []}

        class FakeSmoker:
            def cleanup(self):
                events['cleanup'] = True

        class FakeApp:
            debug = True
            smoker = FakeSmoker()

            def run(self, **kwargs):
                events['run'] = kwargs

        handlers = {}
        monkeypatch.setattr(runserver, 'create_app', lambda: FakeApp())
        monkeypatch.setattr(runserver.signal, 'signal', lambda number, handler: handlers.__setitem__(number, handler))
        monkeypatch.setattr(runserver.os, '_exit', events['exits'].append)
        runserver.main()
        events['handlers'] = handlers
        return events

    def test_runs_the_app_on_all_interfaces_never_in_debug_mode(self, started):
        assert started['run'] == {'host': '0.0.0.0', 'debug': False, 'load_dotenv': False}

    def test_cleans_up_the_hardware_on_sigterm_and_ctrl_c(self, started):
        assert set(started['handlers']) == {signal.SIGTERM, signal.SIGINT}
        for number in (signal.SIGTERM, signal.SIGINT):
            started.pop('cleanup', None)
            started['handlers'][number](number, None)
            assert started['cleanup'] is True
        assert started['exits'] == [0, 0]
