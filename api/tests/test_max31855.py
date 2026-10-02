import pytest

from smokerpi.hardware.RPi import GPIO
from smokerpi.hardware.max31855 import MAX31855, MAX31855Error, TestMAX31855


def make_reader():
    """A MAX31855 instance with only the pure decode methods exercised
    (no GPIO pins touched)."""
    reader = MAX31855.__new__(MAX31855)
    reader.units = 'c'
    return reader


class TestThermocoupleDecoding:
    def test_positive_temperature(self):
        reader = make_reader()
        # 100.0C == 400 steps of 0.25C, encoded in the top 14 bits (D31-D18)
        data = 400 << 18
        assert reader.data_to_tc_temperature(data) == 100.0

    def test_negative_temperature(self):
        reader = make_reader()
        # -10.0C == -40 steps of 0.25C, two's-complement encoded in 14 bits
        data = 0x3FD8 << 18
        assert reader.data_to_tc_temperature(data) == -10.0

    def test_zero_temperature(self):
        reader = make_reader()
        assert reader.data_to_tc_temperature(0) == 0.0


class TestReferenceJunctionDecoding:
    def test_positive_temperature(self):
        reader = make_reader()
        # 25.0C == 400 steps of 0.0625C, encoded in bits D15-D4
        data = 400 << 4
        assert reader.data_to_rj_temperature(data) == 25.0

    def test_negative_temperature(self):
        reader = make_reader()
        # -1.0C == -16 steps of 0.0625C, two's-complement encoded in 12 bits
        data = 0xFF0 << 4
        assert reader.data_to_rj_temperature(data) == -1.0


class TestErrorChecking:
    def test_no_connection_fault(self):
        reader = make_reader()
        with pytest.raises(MAX31855Error) as excinfo:
            reader.checkErrors(0x10000 | 1)
        assert excinfo.value.value == "No Connection"

    def test_short_to_ground_fault(self):
        reader = make_reader()
        with pytest.raises(MAX31855Error) as excinfo:
            reader.checkErrors(0x10000 | 2)
        assert excinfo.value.value == "Thermocouple short to ground"

    def test_short_to_vcc_fault(self):
        reader = make_reader()
        with pytest.raises(MAX31855Error) as excinfo:
            reader.checkErrors(0x10000 | 4)
        assert excinfo.value.value == "Thermocouple short to VCC"

    def test_no_fault_bit_does_not_raise(self):
        reader = make_reader()
        reader.checkErrors(0)  # should not raise


class TestUnitConversion:
    def test_celsius_to_kelvin(self):
        reader = make_reader()
        assert reader.to_k(0) == pytest.approx(273.15)

    def test_celsius_to_fahrenheit(self):
        reader = make_reader()
        assert reader.to_f(100) == pytest.approx(212.0)
        assert reader.to_f(0) == pytest.approx(32.0)


class FakePit:
    def __init__(self, state):
        self.state = state


class TestEmulatedThermocouple:
    def test_never_drops_below_ambient_floor_when_pit_is_cold(self):
        pit = FakePit(0)
        fake = TestMAX31855(pit)
        for _ in range(20):
            reading = fake.get()
        assert reading == 20

    def test_rises_when_pit_is_hot(self):
        pit = FakePit(100)
        fake = TestMAX31855(pit)
        reading = fake.get()
        # +5 degrees of heat input from a fully-open pit vs. -2 of drift
        assert reading == 23.0

    def test_cools_back_down_once_pit_closes_and_hits_the_floor(self):
        pit = FakePit(100)
        fake = TestMAX31855(pit)
        fake.get()  # 18 + 5 = 23
        pit.state = 0
        assert fake.get() == 21.0  # 23 - 2 + 0
        assert fake.get() == 20  # 21 - 2 + 0, clamped to the 20 floor


def word(celsius, rj=25.0):
    """A well-formed 32-bit MAX31855 word: thermocouple in D31-D18, junction in D15-D4."""
    return ((int(round(celsius * 4)) & 0x3FFF) << 18) | ((int(round(rj * 16)) & 0xFFF) << 4)


def slipped(data):
    """The word as read when the bit-banged read is one bit early: everything doubles."""
    return (data << 1) & 0xFFFFFFFF


def scripted_reader(*words, units='c'):
    """A reader whose read() returns the given words in turn (no GPIO touched)."""
    reader = MAX31855.__new__(MAX31855)
    reader.units = units
    reader.reads = 0
    queue = list(words)

    def read():
        reader.reads += 1
        if not queue:
            raise AssertionError('read more often than the test expected')
        reader.data = queue.pop(0)

    reader.read = read
    return reader


class TestGlitchedReads:
    """On the Pi a read was seen returning exactly double the true temperature (53.5 for
    26.75), a one-bit slip in the bit-banged SPI read that raised no fault. get() therefore
    only trusts a value that two reads agree on."""

    def test_two_agreeing_reads_return_the_value(self):
        reader = scripted_reader(word(26.75), word(26.75))
        assert reader.get() == 26.75
        assert reader.reads == 2

    def test_a_glitched_first_read_is_discarded(self):
        reader = scripted_reader(slipped(word(26.75)), word(26.75), word(26.75))
        assert reader.get() == 26.75

    def test_a_glitched_second_read_is_discarded(self):
        reader = scripted_reader(word(26.75), slipped(word(26.75)), word(26.75), word(26.75))
        assert reader.get() == 26.75

    def test_the_same_glitch_twice_but_not_back_to_back_is_not_trusted(self):
        reader = scripted_reader(slipped(word(26.75)), word(26.75), slipped(word(26.75)), word(26.75), word(26.75))
        assert reader.get() == 26.75

    def test_reads_that_never_agree_are_an_error_not_a_guess(self):
        reader = scripted_reader(*[word(t) for t in (20, 30, 40, 50, 60, 70)])
        with pytest.raises(MAX31855Error) as excinfo:
            reader.get()
        assert 'agree' in excinfo.value.value
        assert reader.reads <= 6

    def test_a_small_difference_between_reads_is_not_a_disagreement(self):
        # the sensor converts every 100 ms, so two quick reads can straddle an update
        reader = scripted_reader(word(100.0), word(100.5))
        assert reader.get() == 100.5

    @pytest.mark.parametrize('reserved', [1 << 17, 1 << 3])
    def test_a_word_with_a_reserved_bit_set_is_not_trusted(self, reserved):
        bad = word(26.75) | reserved       # D17 and D3 are always 0 on a good read
        reader = scripted_reader(bad, bad, word(26.75), word(26.75))
        assert reader.get() == 26.75

    def test_a_fault_still_raises_immediately(self):
        reader = scripted_reader(word(26.75) | 0x10000 | 1)
        with pytest.raises(MAX31855Error) as excinfo:
            reader.get()
        assert excinfo.value.value == 'No Connection'
        assert reader.reads == 1

    def test_the_agreed_value_is_converted_to_the_requested_units(self):
        reader = scripted_reader(word(100.0), word(100.0), units='f')
        assert reader.get() == 212.0


class TestTheRealReaderUnderGpioRules:
    """The bit-banged read runs against the off-Pi GPIO shim, which enforces the real library's
    rules, so a pin used before it is set up (or in the wrong direction) fails here."""

    def test_sets_up_its_pins_with_the_chip_deselected(self):
        MAX31855(20, 21, 16)
        assert [GPIO.gpio_function(pin) for pin in (20, 21, 16)] == [GPIO.OUT, GPIO.OUT, GPIO.IN]
        assert GPIO.input(20) == GPIO.HIGH

    def test_a_read_clocks_the_bus_and_deselects_the_chip_again(self):
        sensor = MAX31855(20, 21, 16)
        assert sensor.get() == 0.0          # the shim's data line reads low: 32 zero bits
        assert GPIO.input(20) == GPIO.HIGH
        assert GPIO.input(21) == GPIO.HIGH

    def test_cleanup_releases_the_output_pins(self):
        sensor = MAX31855(20, 21, 16)
        sensor.cleanup()
        assert [GPIO.gpio_function(pin) for pin in (20, 21)] == [GPIO.IN, GPIO.IN]
