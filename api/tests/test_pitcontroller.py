from smokerpi.hardware.blower import Blower
from smokerpi.hardware.damper2 import emulatedDamper
from smokerpi.hardware.pitcontroller import PitController


def make_controller():
    return PitController(Blower(26, 19), emulatedDamper(13, 500, 2500))


class TestPitController:
    def test_set_opens_damper_to_the_given_value(self):
        controller = make_controller()
        controller.set(55)
        assert controller.state == 55
        assert controller.damper.state == 55

    def test_set_rounds_to_two_decimal_places(self):
        controller = make_controller()
        controller.set(12.3456)
        assert controller.state == 12.35

    def test_blower_turns_off_at_or_below_99(self):
        controller = make_controller()
        controller.set(99)
        assert controller.blower.state == 0

    def test_blower_turns_on_above_99(self):
        controller = make_controller()
        controller.set(99.5)
        assert controller.blower.state == 100
