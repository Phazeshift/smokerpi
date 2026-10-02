from smokerpi.hardware.RPi import GPIO
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


class TestBlowerUnderRealGpioRules:
    """The off-Pi GPIO shim enforces the real library's rules (tests/test_gpio_shim.py), which
    is how a blower that never set its pins up as outputs is caught here and not on the Pi."""

    def test_construction_sets_both_pins_up_as_outputs_driven_low(self):
        Blower(26, 19)
        assert (GPIO.gpio_function(26), GPIO.gpio_function(19)) == (GPIO.OUT, GPIO.OUT)
        assert (GPIO.input(26), GPIO.input(19)) == (0, 0)

    def test_the_very_first_on_works(self):
        blower = Blower(26, 19)
        blower.on()          # used to raise RuntimeError: not set up as an OUTPUT
        assert blower.state == 100
        assert (GPIO.input(26), GPIO.input(19)) == (1, 0)

    def test_off_drives_both_pins_low(self):
        blower = Blower(26, 19)
        blower.on()
        blower.off()
        assert blower.state == 0
        assert (GPIO.input(26), GPIO.input(19)) == (0, 0)

    def test_can_be_switched_repeatedly(self):
        blower = Blower(26, 19)
        for _ in range(3):
            blower.on()
            blower.off()
        assert blower.state == 0

    def test_pwm_works_straight_after_construction(self):
        blower = Blower(26, 19)
        blower.pwm(42)
        assert blower.state == 42
        assert blower.p.dc == 42

    def test_on_after_pwm_takes_the_pins_back_out_of_pwm(self):
        blower = Blower(26, 19)
        blower.pwm(42)
        blower.on()
        GPIO.PWM(26, 100)    # the blower's PWM was stopped, so the channel is free again
        assert (GPIO.input(26), GPIO.input(19)) == (1, 0)

    def test_cleanup_releases_the_pins(self):
        blower = Blower(26, 19)
        blower.cleanup()
        assert (GPIO.gpio_function(26), GPIO.gpio_function(19)) == (GPIO.IN, GPIO.IN)
