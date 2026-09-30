import pytest

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
