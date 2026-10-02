import time
import types

import pytest

from smokerpi.hardware import damper2, fakepigpio
from smokerpi.hardware.damper2 import Damper, emulatedDamper


class TestFakePigpio:
    """What the emulated damper talks to instead of pigpiod. It rejects what pigpio rejects."""

    def test_records_the_pulses_sent(self):
        pi = fakepigpio.pi()
        pi.set_servo_pulsewidth(13, 1500)
        assert pi.pulses == [(13, 1500)]

    @pytest.mark.parametrize('width', [0, 500, 1500, 2500])
    def test_accepts_off_and_the_servo_range(self, width):
        fakepigpio.pi().set_servo_pulsewidth(13, width)

    @pytest.mark.parametrize('width', [100, 499, 2501])
    def test_a_pulse_width_outside_the_servo_range_is_an_error(self, width):
        with pytest.raises(fakepigpio.error, match='pulsewidth not 0 or 500-2500'):
            fakepigpio.pi().set_servo_pulsewidth(13, width)

    def test_a_pin_that_is_not_a_user_gpio_is_an_error(self):
        with pytest.raises(fakepigpio.error, match='GPIO not 0-31'):
            fakepigpio.pi().set_servo_pulsewidth(32, 1500)

    def test_is_connected_until_stopped(self):
        pi = fakepigpio.pi()
        assert pi.connected
        pi.stop()
        assert not pi.connected


class TestEmulatedDamper:
    """Off the Pi the app runs the real Damper against the fake pigpio, so the pulse mapping,
    invert and reconnect logic run in the emulator too (there used to be a separate
    TestDamper that only stored the position)."""

    def test_is_the_real_damper(self):
        assert type(emulatedDamper(13, 500, 2500)) is Damper

    def test_does_not_wait_for_the_servo_to_settle(self):
        damper = emulatedDamper(13, 500, 2500)
        started = time.monotonic()
        for position in (10, 20, 30):
            damper.open(position)
        assert time.monotonic() - started < 0.5

    def test_sends_the_mapped_and_mirrored_pulse(self):
        damper = emulatedDamper(13, 600, 2400, invert=True)
        damper.open(0)
        assert damper.pi.pulses[-2:] == [(13, 2400), (13, 0)]

    def test_a_pulse_range_pigpio_would_reject_fails_as_on_the_pi(self):
        damper = emulatedDamper(13, 100, 2500)
        with pytest.raises(fakepigpio.error):
            damper.open(0)

    def test_the_app_uses_it(self, app):
        assert type(app.smoker.damper) is Damper

    def test_changing_invert_in_the_app_really_moves_it(self, app, client):
        app.smoker.damper.open(20)
        response = client.post('/api/config', json={
            'set_temperature': 105, 'damper_minimum': 500, 'damper_maximum': 2500, 'damper_invert': True})
        assert response.status_code == 200
        assert app.smoker.damper.pi.pulses[-2] == (13, 500 + (2000 / 100) * 80)
        assert app.smoker.damper.state == 20


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



class TestInvert:
    """Some linkages open the damper at the smaller pulse width. With invert, position 100
    (open) is sent as damper_minimum and 0 (closed) as damper_maximum, so everything above
    the Damper (the PID, the API, the UI) keeps meaning 100 = open."""

    def test_the_position_is_mirrored_onto_the_pulse_width_range(self, fake_pi):
        damper = Damper(pin=13, min=600, max=2400, invert=True)
        fake_pi.pulses.clear()
        for position, expected in [(0, 2400), (50, 1500), (100, 600)]:
            damper.open(position)
            assert fake_pi.pulses[-2] == (13, expected)

    def test_not_inverted_by_default(self, fake_pi):
        damper = Damper(pin=13, min=600, max=2400)
        assert damper.invert is False

    def test_the_constructor_still_opens_it_fully(self, fake_pi):
        Damper(pin=13, min=500, max=1500, invert=True)
        assert fake_pi.pulses[0] == (13, 500)

    def test_the_reported_position_is_not_mirrored(self, fake_pi):
        damper = Damper(pin=13, invert=True)
        damper.open(30)
        assert damper.state == 30

    def test_reposition_sends_the_current_position_with_the_new_mapping(self, fake_pi):
        damper = Damper(pin=13, min=600, max=2400)
        damper.open(20)
        fake_pi.pulses.clear()

        damper.invert = True
        damper.reposition()

        assert fake_pi.pulses[0] == (13, 600 + (1800 / 100) * 80)
        assert damper.state == 20

    def test_a_failed_reposition_leaves_the_position_unknown_so_the_next_move_is_sent(self, daemon):
        damper = Damper(pin=13)
        damper.open(20)
        daemon.restart()
        damper.invert = True
        with pytest.raises(OSError):
            damper.reposition()
        assert damper.state == -1

        damper.open(20)                      # the same position as before: must still move

        assert damper.state == 20
        assert daemon.connections[-1].pulses[0][1] == 500 + (2000 / 100) * 80
