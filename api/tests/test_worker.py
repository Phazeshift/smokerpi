"""The background worker reads the thermocouple, runs the PID and records the graph.

An exception in it used to kill the thread silently: the temperature and PID froze, and a
running blower stayed running unsupervised. These tests cover the loop surviving errors, and
failing safe (blower off) when a hardware or sensor step fails."""
import logging
import time

import pytest

from smokerpi import create_app
from smokerpi.config import Config


class Exploding:
    """Stands in for any hardware object whose calls fail."""
    def __init__(self, message='gpio boom'):
        self.message = message
        self.calls = 0

    def _fail(self, *args, **kwargs):
        self.calls += 1
        raise OSError(self.message)

    get = set = on = off = open = _fail


class Recorder:
    def __init__(self):
        self.calls = []

    def set(self, value):
        self.calls.append(value)


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    # create_app writes ./log/app.log
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def app():
    application = create_app(test_config={'config': Config(test=True).defaultConfig(), 'start_worker': False})
    yield application
    application.smokerpi_running = False


def errors(caplog):
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


class TestOneStep:
    def test_a_normal_step_runs_cleanly_and_records_a_graph_point(self, app, caplog):
        app.smokerpi_workerStep()
        assert errors(caplog) == []
        assert len(app.smokerpi_graphData) == 1

    def test_a_failing_pid_step_is_logged_and_does_not_raise(self, app, caplog):
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Exploding('damper boom')

        app.smokerpi_workerStep()          # must not raise

        assert 'damper boom' in caplog.text
        assert 'PID update' in caplog.text

    def test_the_loop_keeps_working_once_the_fault_clears(self, app):
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Exploding()
        app.smokerpi_workerStep()
        app.smokerpi_pitController = Recorder()
        app.smokerpi_workerStep()
        assert len(app.smokerpi_pitController.calls) == 1


class TestFailingSafe:
    def test_a_failing_pid_step_switches_the_blower_off(self, app):
        app.smokerpi_blower.on()
        assert app.smokerpi_blower.state == 100
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Exploding()

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 0

    def test_a_failing_sensor_read_switches_the_blower_off(self, app, caplog):
        app.smokerpi_blower.on()
        app.smokerpi_max31855 = Exploding('spi boom')

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 0
        assert 'spi boom' in caplog.text

    def test_the_pid_does_not_act_on_a_reading_that_could_not_be_taken(self, app):
        app.smokerpi_max31855 = Exploding()
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Recorder()

        app.smokerpi_workerStep()

        assert app.smokerpi_pitController.calls == []

    def test_failing_to_switch_the_blower_off_is_survived_and_logged(self, app, caplog):
        app.smokerpi_blower = Exploding('relay boom')
        app.smokerpi_max31855 = Exploding()

        app.smokerpi_workerStep()          # must not raise

        assert 'relay boom' in caplog.text

    def test_a_graph_problem_is_logged_but_leaves_the_blower_alone(self, app, caplog):
        app.smokerpi_blower.on()
        app.smokerpi_graphData = None      # graphData() will fail on .append

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 100
        assert 'graph update' in caplog.text


class TestTheThread:
    def test_the_worker_thread_survives_repeated_failures(self):
        config = dict(Config(test=True).defaultConfig(), worker_interval=0.02, graph_interval=0.02)
        application = create_app(test_config={'config': config, 'start_worker': True})
        try:
            failing = Exploding()
            application.smokerpi_pidRunning = True
            application.smokerpi_pitController = failing
            deadline = time.time() + 5
            while failing.calls < 4 and time.time() < deadline:
                time.sleep(0.02)

            assert failing.calls >= 4, 'the loop stopped calling the failing step'
            assert application.worker.is_alive()
        finally:
            application.smokerpi_running = False
            application.worker.join(2)
