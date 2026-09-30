import pytest

from smokerpi.hardware import blower as blower_module
from smokerpi.hardware.blower import Blower


class TestBlowerEmulated:
    def test_starts_off(self):
        blower = Blower(26, 19)
        assert blower.state == 0

    def test_on_sets_full_state(self):
        blower = Blower(26, 19)
        blower.on()
        assert blower.state == 100

    def test_off_after_on_resets_state(self):
        blower = Blower(26, 19)
        blower.on()
        blower.off()
        assert blower.state == 0

    def test_pwm_sets_duty_cycle_as_state(self):
        blower = Blower(26, 19)
        blower.pwm(42)
        assert blower.state == 42
        assert blower.pwmMode is True

    def test_on_after_pwm_switches_out_of_pwm_mode(self):
        blower = Blower(26, 19)
        blower.pwm(42)
        blower.on()
        assert blower.pwmMode is False
        assert blower.state == 100

    def test_cleanup_does_not_raise(self):
        blower = Blower(26, 19)
        blower.cleanup()


class FakePwm:
    def __init__(self, gpio, pin):
        self.gpio, self.pin = gpio, pin

    def start(self, duty):
        self.gpio.pwm_duty[self.pin] = duty

    def ChangeDutyCycle(self, duty):
        self.gpio.pwm_duty[self.pin] = duty

    def stop(self):
        self.gpio.pwm_duty.pop(self.pin, None)


class StrictGPIO:
    """Enforces the rules the real RPi.GPIO library does. The emulator shim used by the other
    tests accepts anything, which is how a blower that never set its pins up as outputs
    passed CI and then failed with a RuntimeError on the real Pi."""
    BCM, BOARD, OUT, IN, LOW, HIGH = 'BCM', 'BOARD', 'OUT', 'IN', 0, 1

    def __init__(self):
        self.direction = {}
        self.level = {}
        self.pwm_duty = {}

    def setmode(self, mode):
        self.mode = mode

    def setup(self, pin, direction, initial=None):
        self.direction[pin] = direction
        if direction == self.OUT and initial is not None:
            self.level[pin] = initial

    def output(self, pin, value):
        if self.direction.get(pin) != self.OUT:
            raise RuntimeError('The GPIO channel has not been set up as an OUTPUT')
        self.level[pin] = value

    def PWM(self, pin, frequency):
        if self.direction.get(pin) != self.OUT:
            raise RuntimeError('You must setup() the GPIO channel as an output first')
        return FakePwm(self, pin)


@pytest.fixture
def gpio(monkeypatch):
    strict = StrictGPIO()
    monkeypatch.setattr(blower_module, 'GPIO', strict)
    return strict


class TestBlowerUnderRealGpioRules:
    def test_construction_sets_both_pins_up_as_outputs_driven_low(self, gpio):
        Blower(26, 19)
        assert gpio.direction == {26: 'OUT', 19: 'OUT'}
        assert gpio.level == {26: 0, 19: 0}

    def test_the_very_first_on_works(self, gpio):
        blower = Blower(26, 19)
        blower.on()          # used to raise RuntimeError: not set up as an OUTPUT
        assert blower.state == 100
        assert gpio.level == {26: 1, 19: 0}

    def test_off_drives_both_pins_low(self, gpio):
        blower = Blower(26, 19)
        blower.on()
        blower.off()
        assert blower.state == 0
        assert gpio.level == {26: 0, 19: 0}

    def test_can_be_switched_repeatedly(self, gpio):
        blower = Blower(26, 19)
        for _ in range(3):
            blower.on()
            blower.off()
        assert blower.state == 0

    def test_pwm_works_straight_after_construction(self, gpio):
        blower = Blower(26, 19)
        blower.pwm(42)
        assert blower.state == 42
        assert gpio.pwm_duty == {26: 42}

    def test_on_after_pwm_takes_the_pins_back_out_of_pwm(self, gpio):
        blower = Blower(26, 19)
        blower.pwm(42)
        blower.on()
        assert gpio.pwm_duty == {}
        assert gpio.level[26] == 1 and gpio.level[19] == 0

    def test_cleanup_releases_the_pins(self, gpio):
        blower = Blower(26, 19)
        blower.cleanup()
        assert gpio.direction == {26: 'IN', 19: 'IN'}
