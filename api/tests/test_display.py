"""The OLED display shows the smoker's state on a 128x64 screen.

It is read-only and must never reach the control loop: it takes no lock, and a display that is
missing, unplugged or failing is logged and ignored. The drawing is checked through describe()
(the text that goes on the screen) and by comparing the images; the Pi's real SH1106 is not
needed, tests give it a device that records what it is shown."""
import logging

import pytest

from smokerpi.config import Config
from smokerpi.display import Display, describe, openDevice, render


def state(**changes):
    values = {'temperature': 104.5, 'targetTemperature': 105, 'blower': 0, 'pid': True, 'damper': 99}
    values.update(changes)
    return values


class FakeDevice:
    """Stands in for a luma device: records what it is shown."""
    size = (128, 64)

    def __init__(self):
        self.images = []
        self.cleared = False
        self.broken = None

    def display(self, image):
        if self.broken:
            raise self.broken
        self.images.append(image.copy())

    def clear(self):
        self.cleared = True


class TestDescribe:
    def test_shows_temperature_and_target(self):
        text = describe(state(temperature=104.5, targetTemperature=105), None)
        assert text['temperature'] == '104.5C'
        assert text['target'] == 'Set 105'

    def test_temperature_has_one_decimal(self):
        assert describe(state(temperature=24.25), None)['temperature'] == '24.2C'
        assert describe(state(temperature=100), None)['temperature'] == '100.0C'

    def test_mode_follows_the_pid(self):
        assert describe(state(pid=True), None)['mode'] == 'AUTO'
        assert describe(state(pid=False), None)['mode'] == 'MANUAL'

    def test_blower_and_damper(self):
        text = describe(state(blower=100, damper=99), None)['outputs']
        assert text == 'Blower ON  Damper 99%'

    def test_blower_off_and_damper_closed(self):
        assert describe(state(blower=0, damper=0), None)['outputs'] == 'Blower OFF  Damper 0%'

    def test_partial_blower_speed_is_a_percentage(self):
        assert describe(state(blower=40), None)['outputs'].startswith('Blower 40%')

    def test_unknown_damper_position(self):
        # The damper's state is -1 until it has been moved once.
        assert describe(state(damper=-1), None)['outputs'].endswith('Damper ?')

    def test_a_worker_error_replaces_the_outputs(self):
        text = describe(state(), 'temperature read: boom')
        assert text['outputs'] == '! temperature read: boom'


class TestRender:
    def test_image_fits_the_screen(self):
        image = render(state(), None, (128, 64))
        assert image.size == (128, 64)
        assert image.mode == '1'

    def test_something_is_drawn(self):
        assert render(state(), None, (128, 64)).getbbox() is not None

    def test_the_image_changes_with_the_state(self):
        base = render(state(), None, (128, 64)).tobytes()
        assert render(state(temperature=250.0), None, (128, 64)).tobytes() != base
        assert render(state(blower=100), None, (128, 64)).tobytes() != base
        assert render(state(pid=False), None, (128, 64)).tobytes() != base
        assert render(state(), 'boom', (128, 64)).tobytes() != base

    def test_a_very_long_error_still_fits(self):
        image = render(state(), 'temperature read: ' + 'x' * 500, (128, 64))
        assert image.size == (128, 64)


class TestDisplay:
    @pytest.fixture
    def display(self, app):
        device = FakeDevice()
        return Display(app.smoker, app.worker, device, interval=0.01)

    def test_update_shows_the_current_state(self, app, display):
        app.smoker.temperature = 88.0
        assert display.update() is True
        shown = display.device.images[-1]
        assert shown.tobytes() == render(app.smoker.snapshot(), None, (128, 64)).tobytes()

    def test_update_shows_the_worker_error(self, app, display):
        app.worker.stepErrors['temperature read'] = 'boom'
        display.update()
        shown = display.device.images[-1]
        assert shown.tobytes() == render(app.smoker.snapshot(), app.worker.error(), (128, 64)).tobytes()

    def test_update_takes_no_lock(self, app, display):
        # A control loop stuck in a hardware call holds the lock; the display must still draw.
        with app.smoker.lock:
            assert display.update() is True

    def test_a_failing_device_is_logged_not_raised(self, display, caplog):
        display.device.broken = OSError('i2c gone')
        with caplog.at_level(logging.WARNING, logger='smokerpi'):
            assert display.update() is False
        assert 'i2c gone' in caplog.text

    def test_a_failure_is_logged_once_not_every_pass(self, display, caplog):
        display.device.broken = OSError('i2c gone')
        with caplog.at_level(logging.WARNING, logger='smokerpi'):
            display.update()
            display.update()
            display.update()
        assert caplog.text.count('i2c gone') == 1

    def test_it_recovers_when_the_device_comes_back(self, display):
        display.device.broken = OSError('i2c gone')
        display.update()
        display.device.broken = None
        assert display.update() is True

    def test_cleanup_clears_the_screen(self, display):
        display.cleanup()
        assert display.device.cleared

    def test_cleanup_survives_a_dead_device(self, display):
        display.device.clear = lambda: (_ for _ in ()).throw(OSError('gone'))
        display.cleanup()       # must not raise

    def test_the_thread_keeps_drawing_until_the_smoker_stops(self, app, display):
        import time
        display.start()
        deadline = time.time() + 2
        while len(display.device.images) < 3 and time.time() < deadline:
            time.sleep(0.01)
        app.smoker.running = False
        display.thread.join(2)
        assert len(display.device.images) >= 3
        assert not display.thread.is_alive()


class TestOpenDevice:
    def config(self, **changes):
        values = Config(test=True).defaultConfig()
        values.update(changes)
        return values

    def test_disabled_gives_no_device(self):
        assert openDevice(self.config(oled_enabled=False)) is None

    def test_an_unknown_driver_gives_no_device(self, caplog):
        with caplog.at_level(logging.WARNING, logger='smokerpi'):
            assert openDevice(self.config(oled_driver='nonsense')) is None
        assert 'nonsense' in caplog.text

    @pytest.mark.parametrize('address', ['0x3c', '0X3C', '60', 60])
    def test_the_address_may_be_hex_or_decimal(self, address, monkeypatch):
        import smokerpi.display as display
        assert display.parseAddress(address) == 0x3c

    @pytest.mark.parametrize('address', ['', 'banana', None, '0x', -1, '0x100'])
    def test_a_bad_address_gives_no_device(self, address, caplog):
        with caplog.at_level(logging.WARNING, logger='smokerpi'):
            assert openDevice(self.config(oled_address=address)) is None
        assert 'oled_address' in caplog.text

    def test_a_missing_display_gives_no_device(self, caplog):
        # No I2C bus here (or no luma installed): the app must carry on without a display.
        with caplog.at_level(logging.WARNING, logger='smokerpi'):
            assert openDevice(self.config()) is None
        assert caplog.text


class TestConfig:
    def test_defaults_match_the_pi(self):
        config = Config(test=True).defaultConfig()
        assert config['oled_enabled'] is True
        assert config['oled_driver'] == 'sh1106'
        assert config['oled_address'] == '0x3c'

    def test_the_oled_settings_are_shown_but_not_editable(self, client):
        # They need a restart, like the pins: the Config page lists them as disabled boxes.
        import json
        fields = {field['name']: field for field in json.loads(client.get('/api/config').data)['fields']}
        for name in ('oled_enabled', 'oled_driver', 'oled_address'):
            assert fields[name]['label']
            assert fields[name]['kind'] is None

    def test_posting_does_not_change_them(self, client):
        import json
        current = json.loads(client.get('/api/config').data)
        current.pop('fields')
        current.update(oled_enabled=False, oled_driver='ssd1306', oled_address='0x3d')
        client.post('/api/config', json=current)
        after = json.loads(client.get('/api/config').data)
        assert (after['oled_enabled'], after['oled_driver'], after['oled_address']) == (True, 'sh1106', '0x3c')


class TestApp:
    def test_the_app_has_a_display(self, app):
        assert hasattr(app, 'display')

    def test_off_the_pi_there_is_no_device(self, app):
        # Emulated hardware: nothing to talk to, so the display does nothing and costs nothing.
        assert app.display.device is None
        assert app.display.update() is False
