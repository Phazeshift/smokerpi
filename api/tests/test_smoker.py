"""The Smoker holds all live state and does every control operation. It needs no Flask app,
so it is tested directly here; tests/test_api.py covers the routes on top of it."""
import threading

import pytest

from smokerpi.config import Config
from smokerpi.smoker import ControlBusy, DamperNotMoved, Smoker


@pytest.fixture
def smoker(tmp_path):
    configFile = Config(True, str(tmp_path / 'config.json'))
    return Smoker(Config(test=True).defaultConfig(), configFile, str(tmp_path), test=True)


@pytest.fixture
def held(smoker):
    """The control lock held by another thread, as by a worker stuck in a hardware call."""
    smoker.lockTimeout = 0.1
    holding, done = threading.Event(), threading.Event()

    def hold():
        with smoker.lock:
            holding.set()
            done.wait(5)

    holder = threading.Thread(target=hold)
    holder.start()
    assert holding.wait(5)
    yield
    done.set()
    holder.join(5)


class TestControlMode:
    """`automatic` is the one switch for whether the PID is in control; the PID's own
    auto_mode follows it and is never set anywhere else."""

    def test_starts_in_manual_with_the_pid_paused(self, smoker):
        assert smoker.automatic is False
        assert smoker.pid.auto_mode is False

    def test_the_first_switch_to_automatic_starts_from_a_clean_integral(self, smoker):
        # simple_pid starts in auto mode, so the PID used to run during every manual pass
        # after startup and the first "PID on" inherited the integral built up meanwhile;
        # every later one started from zero.
        for _ in range(3):
            smoker.pid(20)                 # what each worker pass does, in manual too
        smoker.setAutomatic(True)
        assert smoker.pid.components[1] == 0

    def test_automatic_on_starts_the_pid(self, smoker):
        smoker.setAutomatic(True)
        assert smoker.automatic is True
        assert smoker.pid.auto_mode is True

    def test_automatic_off_stops_the_pid_and_the_blower(self, smoker):
        smoker.setAutomatic(True)
        smoker.blower.on()
        smoker.setAutomatic(False)
        assert smoker.automatic is False
        assert smoker.pid.auto_mode is False
        assert smoker.blower.state == 0

    @pytest.mark.parametrize('operation', ['setBlower', 'setDamper'])
    @pytest.mark.parametrize('value', [True, False])
    def test_a_manual_control_takes_the_pid_out_of_the_loop(self, smoker, operation, value):
        smoker.setAutomatic(True)
        getattr(smoker, operation)(value)
        assert smoker.automatic is False
        assert smoker.pid.auto_mode is False

    def test_manual_blower_and_damper(self, smoker):
        smoker.setBlower(True)
        smoker.setDamper(False)
        assert smoker.blower.state == 100
        assert smoker.damper.state == 0


class TestTheLock:
    @pytest.mark.parametrize('call', [
        lambda s: s.setAutomatic(True),
        lambda s: s.setBlower(True),
        lambda s: s.setDamper(False),
        lambda s: s.updateConfig({'set_temperature': 130}),
    ])
    def test_every_control_operation_gives_up_if_the_lock_is_held(self, smoker, held, call):
        with pytest.raises(ControlBusy, match='control loop'):
            call(smoker)
        assert smoker.automatic is False
        assert smoker.blower.state == 0
        assert smoker.config['set_temperature'] != 130

    def test_reading_the_state_and_the_graph_does_not_need_it(self, smoker, held):
        assert smoker.snapshot()['pid'] is False
        assert smoker.graphSince(0) == []

    def test_the_lock_is_released_after_an_operation_fails(self, smoker):
        smoker.blower.on = lambda: (_ for _ in ()).throw(OSError('relay boom'))
        with pytest.raises(OSError):
            smoker.setBlower(True)
        assert smoker.lock.acquire(blocking=False)
        smoker.lock.release()


class TestSettings:
    def test_update_applies_and_saves(self, smoker, tmp_path):
        smoker.updateConfig({'set_temperature': 130, 'pid_kp': 2.5})
        assert smoker.pid.setpoint == 130
        assert smoker.pid.tunings[0] == 2.5
        assert '"set_temperature": 130' in (tmp_path / 'config.json').read_text()

    def test_a_damper_that_cannot_follow_an_invert_change_is_reported_but_the_setting_kept(self, smoker, tmp_path):
        def fail():
            raise OSError('pigpiod is down')
        smoker.damper.reposition = fail
        with pytest.raises(DamperNotMoved, match='pigpiod is down'):
            smoker.updateConfig({'damper_invert': True})
        assert smoker.config['damper_invert'] is True
        assert '"damper_invert": true' in (tmp_path / 'config.json').read_text()

    def test_the_password_is_never_public(self, smoker):
        smoker.config['password'] = 'secret'
        assert 'password' not in smoker.publicConfig()


class TestSnapshotAndGraph:
    def test_snapshot(self, smoker):
        smoker.temperature = 99.5
        assert smoker.snapshot() == {
            'temperature': 99.5, 'targetTemperature': 105, 'blower': 0, 'pid': False, 'damper': 99}

    def test_graph_since_a_point(self, smoker):
        smoker.graphData.extend({'i': i} for i in range(5))
        assert [p['i'] for p in smoker.graphSince(3)] == [3, 4]


class TestCleanup:
    def test_stops_and_releases_the_hardware(self, smoker):
        released = []
        smoker.blower.cleanup = lambda: released.append('blower')
        smoker.damper.cleanup = lambda: released.append('damper')
        smoker.cleanup()
        assert smoker.running is False
        assert released == ['blower', 'damper']
