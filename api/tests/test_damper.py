import types

import pytest

from smokerpi.hardware import damper2
from smokerpi.hardware.damper2 import Damper, TestDamper


class TestDamperEmulator:
    def test_starts_closed(self):
        damper = TestDamper()
        assert damper.state == -1

    def test_open_sets_state(self):
        damper = TestDamper()
        damper.open(75)
        assert damper.state == 75

    def test_cleanup_does_not_raise(self):
        damper = TestDamper()
        damper.cleanup()


class FakePi:
    """Records what the real Damper would send to the pigpio daemon."""
    def __init__(self):
        self.pulses = []
        self.stopped = False
        self.connected = True

    def set_servo_pulsewidth(self, pin, width):
        self.pulses.append((pin, width))

    def stop(self):
        self.stopped = True


@pytest.fixture
def fake_pi(monkeypatch):
    pi = FakePi()
    # damper2 imports pigpio and time inside one try block, so neither exists off the Pi.
    monkeypatch.setattr(damper2, 'pigpio', types.SimpleNamespace(pi=lambda: pi), raising=False)
    monkeypatch.setattr(damper2, 'time', types.SimpleNamespace(sleep=lambda seconds: None), raising=False)
    return pi


class TestServoDamper:
    def test_drives_the_configured_pin(self, fake_pi):
        damper = Damper(pin=17, min=600, max=2400)
        damper.open(50)
        assert damper.pin == 17
        assert {pin for pin, _ in fake_pi.pulses} == {17}

    def test_defaults_to_gpio_13(self, fake_pi):
        Damper()
        assert {pin for pin, _ in fake_pi.pulses} == {13}

    def test_maps_the_position_onto_the_pulse_width_range(self, fake_pi):
        damper = Damper(pin=13, min=600, max=2400)
        fake_pi.pulses.clear()   # ignore the initial fully-open move made by the constructor
        for position, expected in [(0, 600), (50, 1500), (100, 2400)]:
            damper.open(position)
            assert fake_pi.pulses[-2] == (13, expected)

    def test_the_constructor_opens_it_fully(self, fake_pi):
        Damper(pin=13, min=500, max=1500)
        assert fake_pi.pulses[0] == (13, 1500)

    def test_stops_pulsing_after_each_move(self, fake_pi):
        damper = Damper(pin=13)
        damper.open(20)
        assert fake_pi.pulses[-1] == (13, 0)

    def test_repeating_the_current_position_sends_nothing(self, fake_pi):
        damper = Damper(pin=13)
        damper.open(30)
        count = len(fake_pi.pulses)
        damper.open(30)
        assert len(fake_pi.pulses) == count

    def test_cleanup_stops_pulses_on_the_configured_pin(self, fake_pi):
        damper = Damper(pin=17)
        damper.cleanup()
        assert fake_pi.pulses[-1] == (17, 0)
        assert fake_pi.stopped


class Daemon:
    """Stands in for pigpiod: hands out connections, and can be 'restarted' (every
    existing connection then fails) or taken down (new connections are refused)."""
    def __init__(self):
        self.connections = []
        self.down = False

    def connect(self):
        pi = ConnectionPi(self)
        self.connections.append(pi)
        return pi

    def restart(self):
        for pi in self.connections:
            pi.dead = True


class ConnectionPi(FakePi):
    def __init__(self, daemon):
        super().__init__()
        self.dead = daemon.down
        self.connected = not daemon.down

    def set_servo_pulsewidth(self, pin, width):
        if self.dead:
            raise OSError('connection to pigpiod lost')
        super().set_servo_pulsewidth(pin, width)


@pytest.fixture
def daemon(monkeypatch):
    daemon = Daemon()
    monkeypatch.setattr(damper2, 'pigpio', types.SimpleNamespace(pi=daemon.connect), raising=False)
    monkeypatch.setattr(damper2, 'time', types.SimpleNamespace(sleep=lambda seconds: None), raising=False)
    return daemon


class TestReconnecting:
    """pigpiod can be restarted or crash while SmokerPi runs. The damper must then recover
    on its own rather than fail until SmokerPi itself is restarted."""

    def test_a_failed_move_raises_and_does_not_record_the_new_position(self, daemon):
        damper = Damper(pin=13)
        daemon.restart()
        with pytest.raises(OSError):
            damper.open(20)
        assert damper.state == 100

    def test_the_next_move_reconnects_and_works(self, daemon):
        damper = Damper(pin=13)
        daemon.restart()
        with pytest.raises(OSError):
            damper.open(20)

        damper.open(20)

        assert damper.state == 20
        assert len(daemon.connections) == 2
        assert daemon.connections[-1].pulses[0] == (13, 500 + (2000 / 100) * 20)

    def test_the_dead_connection_is_closed(self, daemon):
        damper = Damper(pin=13)
        old = daemon.connections[0]
        daemon.restart()
        with pytest.raises(OSError):
            damper.open(20)
        assert old.stopped

    def test_a_daemon_that_is_still_down_is_a_clear_error_and_retried_later(self, daemon):
        damper = Damper(pin=13)
        daemon.restart()
        daemon.down = True
        for _ in range(2):
            with pytest.raises(OSError):
                damper.open(20)
        daemon.down = False

        damper.open(20)

        assert damper.state == 20

    def test_a_healthy_connection_is_kept(self, daemon):
        damper = Damper(pin=13)
        damper.open(20)
        damper.open(40)
        assert len(daemon.connections) == 1

