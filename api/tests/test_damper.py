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
