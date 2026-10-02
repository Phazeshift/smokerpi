"""PID anti-windup and configurable gains.

On the Pi the output stayed at 100 with the temperature just 1.25 degrees under the target,
because the integral term had wound up to its limit during the climb. simple_pid only clamps
the integral to the output range, so it still winds up while the output is saturated."""
import pytest
from simple_pid import PID

from smokerpi import create_app
from smokerpi.config import Config
from smokerpi.pid import AntiWindupPID

DT = 10.0


def make(cls=AntiWindupPID, gains=(1, 0.1, 0), setpoint=105):
    pid = cls(*gains, setpoint=setpoint, sample_time=0.1, output_limits=(0, 100))
    pid.set_auto_mode(True)
    return pid


def run(pid, temperature, steps):
    output = None
    for _ in range(steps):
        output = pid(temperature, dt=DT)
    return output


class TestWhileSaturated:
    def test_the_integral_does_not_wind_up_while_the_output_is_saturated(self):
        pid = make()
        run(pid, 27, 30)                  # 78 degrees under the target for five minutes
        assert pid.components[1] == 0

    def test_the_plain_controller_does_wind_up_which_is_the_bug(self):
        pid = make(PID)
        run(pid, 27, 30)
        assert pid.components[1] == 100

    def test_the_output_is_still_clamped(self):
        pid = make(gains=(5, 0.1, 0))
        assert run(pid, 27, 5) == 100

    def test_it_comes_off_full_output_as_soon_as_the_error_is_small(self):
        pid = make(gains=(1, 0.1, 0), setpoint=105)
        run(pid, 27, 30)
        pid.setpoint = 28                  # the reading is now only 1.25 under the target
        assert run(pid, 26.75, 2) < 99

    def test_the_plain_controller_stays_at_full_output_in_that_case(self):
        pid = make(PID, setpoint=105)
        run(pid, 27, 30)
        pid.setpoint = 28
        assert run(pid, 26.75, 2) == 100

    def test_a_high_temperature_does_not_wind_the_integral_negative(self):
        pid = make()
        run(pid, 200, 30)
        assert pid.components[1] == 0


class TestNormalOperation:
    def test_it_still_integrates_when_the_output_is_not_saturated(self):
        pid = make(gains=(1, 0.01, 0))
        run(pid, 100, 10)                  # 5 under the target: P=5, I grows 0.5 a step
        assert pid.components[1] == pytest.approx(5.0)
        assert run(pid, 100, 1) == pytest.approx(5 + 5.5)

    def test_it_unwinds_the_integral_when_above_the_target(self):
        pid = make(gains=(1, 0.01, 0))
        run(pid, 100, 20)
        built_up = pid.components[1]
        run(pid, 106, 5)
        assert pid.components[1] < built_up

    def test_matches_the_plain_controller_when_never_saturated(self):
        a, b = make(AntiWindupPID, gains=(2, 0.02, 0.5)), make(PID, gains=(2, 0.02, 0.5))
        for temperature in [95, 97, 99, 101, 103, 104, 106, 105, 104]:
            assert a(temperature, dt=DT) == pytest.approx(b(temperature, dt=DT))

    def test_does_nothing_in_manual_mode(self):
        pid = make()
        pid.auto_mode = False
        assert pid(27, dt=DT) is None or pid(27, dt=DT) == pid._last_output


def simulate(cls, gains, setpoint=105, hours=3):
    """A rough smoker: a first-order response (20 minute time constant) to the output, with
    a one minute transport delay, controlled every 11 seconds. Returns the peak overshoot."""
    import collections
    import math
    dt, tau, ambient = 11.0, 1200.0, 20.0
    pid = make(cls, gains=gains, setpoint=setpoint)
    delayed = collections.deque([0.0] * 6)
    temperature, peak = ambient, 0.0
    for _ in range(int(hours * 3600 / dt)):
        delayed.append(pid(temperature, dt=dt))
        output = delayed.popleft()
        temperature += (ambient + 1.6 * output - temperature) * (1 - math.exp(-dt / tau))
        peak = max(peak, temperature)
    return peak - setpoint


class TestAgainstARoughSmoker:
    def test_the_plain_controller_overshoots_a_lot(self):
        assert simulate(PID, (5, 0.005, 0)) > 5

    def test_anti_windup_removes_the_overshoot(self):
        assert simulate(AntiWindupPID, (5, 0.005, 0)) < 1


class TestGainsFromConfig:
    def make_app(self, **overrides):
        config = dict(Config(test=True).defaultConfig(), **overrides)
        return create_app(test_config={'config': config, 'start_worker': False})

    def test_the_defaults_are_the_old_hardcoded_gains(self):
        defaults = Config(test=True).defaultConfig()
        assert (defaults['pid_kp'], defaults['pid_ki'], defaults['pid_kd']) == (1, 0.1, 0.05)

    def test_the_app_uses_the_anti_windup_controller_with_the_configured_gains(self):
        app = self.make_app(pid_kp=5, pid_ki=0.005, pid_kd=0)
        try:
            assert isinstance(app.smoker.pid, AntiWindupPID)
            assert app.smoker.pid.tunings == (5, 0.005, 0)
        finally:
            app.smoker.running = False

    def test_the_default_app_has_the_old_gains(self):
        app = self.make_app()
        try:
            assert app.smoker.pid.tunings == (1, 0.1, 0.05)
        finally:
            app.smoker.running = False
