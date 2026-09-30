from smokerpi.hardware.damper2 import TestDamper


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
