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
