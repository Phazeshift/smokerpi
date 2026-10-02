"""The off-Pi RPi.GPIO stand-in enforces the rules the real library does.

It used to accept any call, so a blower that wrote to pins it had never set up as outputs
passed CI and then returned 500 on the Pi. Every message here is the real library's."""
import pytest

from smokerpi.hardware.RPi import GPIO


@pytest.fixture
def bcm():
    GPIO.setmode(GPIO.BCM)


class TestConstants:
    def test_match_the_real_library(self):
        assert (GPIO.BOARD, GPIO.BCM) == (10, 11)
        assert (GPIO.OUT, GPIO.IN) == (0, 1)
        assert (GPIO.LOW, GPIO.HIGH) == (0, 1)


class TestNumberingMode:
    def test_setup_before_setmode_is_an_error(self):
        with pytest.raises(RuntimeError, match='set pin numbering mode'):
            GPIO.setup(26, GPIO.OUT)

    def test_setting_the_same_mode_again_is_fine(self, bcm):
        GPIO.setmode(GPIO.BCM)

    def test_changing_the_mode_is_an_error(self, bcm):
        with pytest.raises(ValueError, match='different mode'):
            GPIO.setmode(GPIO.BOARD)

    def test_an_unknown_mode_is_an_error(self):
        with pytest.raises(ValueError, match='invalid mode'):
            GPIO.setmode('BCM')


class TestSetup:
    def test_a_channel_that_does_not_exist_is_an_error(self, bcm):
        with pytest.raises(ValueError, match='channel sent is invalid'):
            GPIO.setup(40, GPIO.OUT)

    def test_an_unknown_direction_is_an_error(self, bcm):
        with pytest.raises(ValueError, match='invalid direction'):
            GPIO.setup(26, 'OUT')

    def test_records_the_direction(self, bcm):
        GPIO.setup(26, GPIO.OUT)
        GPIO.setup(16, GPIO.IN)
        assert GPIO.gpio_function(26) == GPIO.OUT
        assert GPIO.gpio_function(16) == GPIO.IN

    def test_an_output_starts_at_its_initial_level(self, bcm):
        GPIO.setup(26, GPIO.OUT, initial=GPIO.HIGH)
        assert GPIO.input(26) == GPIO.HIGH


class TestOutputAndInput:
    def test_writing_a_channel_that_was_never_set_up_is_an_error(self, bcm):
        with pytest.raises(RuntimeError, match='not been set up as an OUTPUT'):
            GPIO.output(26, GPIO.HIGH)

    def test_writing_an_input_is_an_error(self, bcm):
        GPIO.setup(26, GPIO.IN)
        with pytest.raises(RuntimeError, match='not been set up as an OUTPUT'):
            GPIO.output(26, GPIO.HIGH)

    def test_an_output_reads_back_what_was_written(self, bcm):
        GPIO.setup(26, GPIO.OUT)
        GPIO.output(26, 1)
        assert GPIO.input(26) == GPIO.HIGH

    def test_reading_a_channel_that_was_never_set_up_is_an_error(self, bcm):
        with pytest.raises(RuntimeError, match='setup\\(\\) the GPIO channel first'):
            GPIO.input(16)

    def test_an_input_reads_low(self, bcm):
        GPIO.setup(16, GPIO.IN)
        assert GPIO.input(16) == GPIO.LOW


class TestPwm:
    def test_pwm_on_a_channel_that_is_not_an_output_is_an_error(self, bcm):
        with pytest.raises(RuntimeError, match='as an output first'):
            GPIO.PWM(26, 100)

    def test_a_second_pwm_on_the_same_channel_is_an_error(self, bcm):
        GPIO.setup(26, GPIO.OUT)
        GPIO.PWM(26, 100)
        with pytest.raises(RuntimeError, match='already exists'):
            GPIO.PWM(26, 100)

    def test_a_stopped_pwm_frees_the_channel(self, bcm):
        GPIO.setup(26, GPIO.OUT)
        GPIO.PWM(26, 100).stop()
        GPIO.PWM(26, 100)

    @pytest.mark.parametrize('duty', [-1, 101])
    def test_a_duty_cycle_outside_0_to_100_is_an_error(self, bcm, duty):
        GPIO.setup(26, GPIO.OUT)
        pwm = GPIO.PWM(26, 100)
        with pytest.raises(ValueError, match='dutycycle'):
            pwm.ChangeDutyCycle(duty)


class TestCleanup:
    def test_cleanup_forgets_the_mode_and_the_channels(self, bcm):
        GPIO.setup(26, GPIO.OUT)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BOARD)
        with pytest.raises(RuntimeError):
            GPIO.output(26, 1)
