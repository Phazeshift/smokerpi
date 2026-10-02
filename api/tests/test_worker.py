"""The background worker reads the thermocouple, runs the PID and records the graph.

An exception in it used to kill the thread silently: the temperature and PID froze, and a
running blower stayed running unsupervised. These tests cover the loop surviving errors, and
failing safe (blower off) when a hardware or sensor step fails."""
import json
import logging
import threading
import time

import pytest

from smokerpi import create_app
from smokerpi.config import Config
from smokerpi.hardware.max31855 import MAX31855Error


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


class Clock:
    """Replaces the app's clock so tests can move time without sleeping."""
    def __init__(self, app):
        self.now = 1000.0
        app.smokerpi_clock = lambda: self.now
        app.smokerpi_lastReading = self.now
        app.smokerpi_lastPass = self.now

    def advance(self, seconds):
        self.now += seconds


class Flaky:
    """A sensor that fails on demand and otherwise reads 150."""
    def __init__(self, error=MAX31855Error('No Connection')):
        self.error = error
        self.failing = False

    def get(self):
        if self.failing:
            raise self.error
        return 150.0


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

    def test_a_sensor_that_has_been_silent_too_long_switches_the_blower_off(self, app, caplog):
        app.smokerpi_blower.on()
        app.smokerpi_max31855 = Exploding('spi boom')
        clock = Clock(app)

        clock.advance(app.smokerpi_config['sensor_timeout'])
        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 0
        assert 'spi boom' in caplog.text

    def test_the_pid_does_not_act_once_the_sensor_has_timed_out(self, app):
        app.smokerpi_max31855 = Exploding()
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Recorder()
        clock = Clock(app)

        clock.advance(app.smokerpi_config['sensor_timeout'])
        app.smokerpi_workerStep()

        assert app.smokerpi_pitController.calls == []

    def test_failing_to_switch_the_blower_off_is_survived_and_logged(self, app, caplog):
        app.smokerpi_blower = Exploding('relay boom')
        app.smokerpi_max31855 = Exploding()
        clock = Clock(app)

        clock.advance(app.smokerpi_config['sensor_timeout'])
        app.smokerpi_workerStep()          # must not raise

        assert 'relay boom' in caplog.text

    def test_a_graph_problem_is_logged_but_leaves_the_blower_alone(self, app, caplog):
        app.smokerpi_blower.on()
        app.smokerpi_graphData = None      # graphData() will fail on .append

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 100
        assert 'graph update' in caplog.text


class TestSensorDropouts:
    """The thermocouple sometimes fails to report on one check and answers on the next. A
    missed read must not stop the fan: only a sensor that stays silent for sensor_timeout."""

    @pytest.fixture
    def sensor(self, app):
        app.smokerpi_max31855 = Flaky()
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Recorder()
        return app.smokerpi_max31855

    def test_the_default_timeout_is_sixty_seconds(self, app):
        assert app.smokerpi_config['sensor_timeout'] == 60

    @pytest.mark.parametrize('error', [MAX31855Error('No Connection'), OSError('spi boom')])
    def test_one_missed_read_leaves_the_blower_and_pid_alone(self, app, sensor, error):
        sensor.error = error
        clock = Clock(app)
        app.smokerpi_workerStep()
        app.smokerpi_blower.on()
        sensor.failing = True
        clock.advance(10)

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 100
        assert len(app.smokerpi_pitController.calls) == 2       # the PID still ran

    def test_the_pid_carries_on_with_the_last_good_reading(self, app, sensor):
        clock = Clock(app)
        app.smokerpi_workerStep()
        sensor.failing = True
        clock.advance(10)
        app.smokerpi_workerStep()
        assert app.smokerpi_currentTemperature == 150.0

    def test_a_missed_read_is_logged_as_a_warning_not_an_error(self, app, sensor, caplog):
        clock = Clock(app)
        sensor.failing = True
        clock.advance(10)
        app.smokerpi_workerStep()
        assert errors(caplog) == []
        assert 'No Connection' in caplog.text

    def test_the_blower_stays_on_just_before_the_timeout(self, app, sensor):
        clock = Clock(app)
        app.smokerpi_workerStep()
        app.smokerpi_blower.on()
        sensor.failing = True
        clock.advance(app.smokerpi_config['sensor_timeout'] - 1)

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 100

    def test_the_blower_goes_off_once_the_sensor_has_been_silent_for_the_timeout(self, app, sensor):
        clock = Clock(app)
        app.smokerpi_workerStep()
        app.smokerpi_blower.on()
        sensor.failing = True
        for _ in range(6):
            clock.advance(10)
            app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 0

    def test_a_good_read_restarts_the_timer(self, app, sensor):
        clock = Clock(app)
        sensor.failing = True
        clock.advance(50)
        app.smokerpi_workerStep()
        sensor.failing = False
        app.smokerpi_workerStep()              # recovers at t=50
        sensor.failing = True
        clock.advance(50)                      # 50s since the good read, 100s since start
        app.smokerpi_blower.on()

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 100

    def test_control_resumes_when_the_sensor_comes_back(self, app, sensor):
        clock = Clock(app)
        sensor.failing = True
        clock.advance(app.smokerpi_config['sensor_timeout'])
        app.smokerpi_workerStep()
        assert app.smokerpi_pitController.calls == []

        sensor.failing = False
        clock.advance(10)
        app.smokerpi_workerStep()

        assert len(app.smokerpi_pitController.calls) == 1

    def test_a_sensor_that_never_works_times_out_from_startup(self, app, sensor):
        clock = Clock(app)
        sensor.failing = True
        app.smokerpi_blower.on()
        clock.advance(app.smokerpi_config['sensor_timeout'])

        app.smokerpi_workerStep()

        assert app.smokerpi_blower.state == 0


class TestWorkerHealth:
    """/api/state reports when the control loop is not working, so the UI can say so
    instead of leaving the person to notice a frozen temperature."""

    def workerError(self, app):
        return json.loads(app.test_client().get('/api/state').data)['workerError']

    def test_no_error_when_every_step_works(self, app):
        app.smokerpi_workerStep()
        assert self.workerError(app) is None

    def test_a_failing_pid_step_is_reported_with_its_message(self, app):
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Exploding('damper boom')
        app.smokerpi_workerStep()
        assert 'PID update' in self.workerError(app)
        assert 'damper boom' in self.workerError(app)

    def test_a_missed_read_within_the_timeout_is_not_reported(self, app):
        app.smokerpi_max31855 = Flaky()
        app.smokerpi_max31855.failing = True
        clock = Clock(app)
        clock.advance(10)
        app.smokerpi_workerStep()
        assert self.workerError(app) is None

    def test_a_sensor_timeout_is_reported(self, app):
        app.smokerpi_max31855 = Flaky()
        app.smokerpi_max31855.failing = True
        clock = Clock(app)
        clock.advance(app.smokerpi_config['sensor_timeout'])
        app.smokerpi_workerStep()
        assert 'temperature read' in self.workerError(app)

    def test_the_error_clears_when_the_fault_clears(self, app):
        app.smokerpi_pidRunning = True
        app.smokerpi_pitController = Exploding()
        app.smokerpi_workerStep()
        app.smokerpi_pitController = Recorder()
        app.smokerpi_workerStep()
        assert self.workerError(app) is None

    def test_a_loop_that_has_stopped_running_is_reported(self, app):
        clock = Clock(app)
        app.smokerpi_workerStep()
        clock.advance(120)                 # no pass for two minutes
        assert 'stopped' in self.workerError(app)

    def test_a_pass_after_a_long_gap_clears_the_stopped_report(self, app):
        clock = Clock(app)
        clock.advance(120)
        app.smokerpi_workerStep()
        assert self.workerError(app) is None


class TestWatchdog:
    """A worker stuck in a hardware call never reaches its own fail-safe, so a separate
    watchdog switches the blower off once no pass has completed for the stall limit."""

    def test_a_stalled_loop_switches_the_blower_off(self, app, caplog):
        clock = Clock(app)
        app.smokerpi_workerStep()
        app.smokerpi_blower.on()
        clock.advance(120)

        app.smokerpi_watchdogCheck()

        assert app.smokerpi_blower.state == 0
        assert any('stopped' in r.getMessage() for r in errors(caplog))

    def test_a_running_loop_is_left_alone(self, app, caplog):
        clock = Clock(app)
        app.smokerpi_workerStep()
        app.smokerpi_blower.on()
        clock.advance(10)

        app.smokerpi_watchdogCheck()

        assert app.smokerpi_blower.state == 100
        assert errors(caplog) == []

    def test_it_does_not_wait_for_the_control_lock(self, app):
        # A stuck worker is usually stuck holding the lock.
        clock = Clock(app)
        app.smokerpi_blower.on()
        clock.advance(120)
        app.smokerpi_lock.acquire()
        try:
            check = threading.Thread(target=app.smokerpi_watchdogCheck)
            check.start()
            check.join(2)
            assert not check.is_alive(), 'the watchdog waited for the lock'
        finally:
            app.smokerpi_lock.release()
        assert app.smokerpi_blower.state == 0

    def test_it_logs_once_per_stall(self, app, caplog):
        clock = Clock(app)
        clock.advance(120)
        app.smokerpi_watchdogCheck()
        app.smokerpi_watchdogCheck()
        assert len(errors(caplog)) == 1

        app.smokerpi_workerStep()          # the loop recovers
        clock.advance(120)                 # and stalls again
        app.smokerpi_watchdogCheck()
        assert len(errors(caplog)) == 2

    def test_a_failing_blower_is_survived_and_logged(self, app, caplog):
        clock = Clock(app)
        app.smokerpi_blower = Exploding('relay boom')
        clock.advance(120)
        app.smokerpi_watchdogCheck()       # must not raise
        assert 'relay boom' in caplog.text


class TestTheThread:
    def test_the_watchdog_thread_stops_the_blower_when_the_worker_hangs(self):
        config = dict(Config(test=True).defaultConfig(), worker_interval=0.02, graph_interval=0.02)
        application = create_app(test_config={'config': config, 'start_worker': True})
        stuck = threading.Event()
        release = threading.Event()

        class Hanging:
            def set(self, value):
                stuck.set()
                release.wait(10)

        try:
            application.smokerpi_pitController = Hanging()
            application.smokerpi_pidRunning = True
            assert stuck.wait(5), 'the worker never reached the hardware'
            application.smokerpi_blower.on()
            # Jump past the stall limit rather than wait 30 seconds.
            application.smokerpi_clock = lambda: time.monotonic() + 1000

            deadline = time.time() + 5
            while application.smokerpi_blower.state != 0 and time.time() < deadline:
                time.sleep(0.02)

            assert application.smokerpi_blower.state == 0
            assert application.watchdog.is_alive()
        finally:
            application.smokerpi_running = False
            release.set()
            application.worker.join(2)
            application.watchdog.join(2)

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
