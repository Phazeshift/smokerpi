"""The OLED display: the smoker's state on a small I2C screen.

It only reads. It takes no lock and never touches the hardware the control loop drives, and any
trouble with the screen (not fitted, unplugged, a bad contact) is logged and ignored, so it
cannot get in the way of the blower or the PID."""
import logging
import threading
import time

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger('smokerpi')

# luma.oled device classes by the name used in config.json ('oled_driver').
DRIVERS = ('sh1106', 'ssd1306', 'ssd1309')


def describe(state, error):
    """The text for each part of the screen, from Smoker.snapshot() and Worker.error()."""
    blower = state['blower']
    if blower >= 100:
        blowerText = 'ON'
    elif blower <= 0:
        blowerText = 'OFF'
    else:
        blowerText = '%d%%' % blower
    damper = state['damper']
    damperText = '?' if damper < 0 else '%d%%' % damper
    return {
        'mode': 'AUTO' if state['pid'] else 'MANUAL',
        'target': 'Set %s' % state['targetTemperature'],
        # Truncate rather than round, so 24.25 reads 24.2 as the thermocouple's step does.
        'temperature': '%.1fC' % (int(state['temperature'] * 10) / 10),
        'outputs': '! %s' % error if error else 'Blower %s  Damper %s' % (blowerText, damperText),
    }


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:       # Pillow before 10.1 has only the one fixed-size font
        return ImageFont.load_default()


def _fit(draw, text, font, width):
    """text, shortened with '...' until it is no wider than width."""
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + '...', font=font) > width:
        text = text[:-1]
    return text + '...'


def render(state, error, size):
    """The screen as a 1-bit image of the given size."""
    width, height = size
    text = describe(state, error)
    image = Image.new('1', size, 0)
    draw = ImageDraw.Draw(image)
    small, big = _font(10), _font(height // 2 - 4)

    draw.text((0, 0), text['mode'], font=small, fill=1)
    target = _fit(draw, text['target'], small, width // 2)
    draw.text((width - draw.textlength(target, font=small), 0), target, font=small, fill=1)

    temperature = _fit(draw, text['temperature'], big, width)
    centred = (width - draw.textlength(temperature, font=big)) / 2
    draw.text((centred, height // 5), temperature, font=big, fill=1)

    draw.text((0, height - 12), _fit(draw, text['outputs'], small, width), font=small, fill=1)
    return image


def parseAddress(value):
    """An I2C address from config.json: '0x3c' (as i2cdetect shows it) or a plain number.
    Raises ValueError if it is not a valid 7-bit address."""
    address = int(value, 0) if isinstance(value, str) else int(value)
    if not 0 <= address <= 0x7f:
        raise ValueError(value)
    return address


def openDevice(config):
    """The luma device for the screen in config.json, or None if it is switched off, unknown, or
    cannot be opened (luma not installed, I2C off, nothing fitted)."""
    if not config.get('oled_enabled', True):
        return None
    driver = config.get('oled_driver', 'sh1106')
    if driver not in DRIVERS:
        log.warning('Unknown oled_driver %r (use one of %s); the display is off', driver, ', '.join(DRIVERS))
        return None
    try:
        address = parseAddress(config.get('oled_address', '0x3c'))
    except (TypeError, ValueError):
        log.warning('Invalid oled_address %r (use e.g. "0x3c"); the display is off', config.get('oled_address'))
        return None
    try:
        from luma.core.interface.serial import i2c
        from luma.oled import device
        return getattr(device, driver)(i2c(port=1, address=address))
    except Exception as e:
        log.warning('OLED display not available (%r); carrying on without it', e)
        return None


class Display:
    """Redraws the screen every `interval` seconds from the smoker's state. `device` is a luma
    device, or None when there is no screen, in which case this does nothing."""

    def __init__(self, smoker, worker, device, interval=2):
        self.smoker = smoker
        self.worker = worker
        self.device = device
        self.interval = interval
        self.thread = None
        self.failure = None         # the last error logged, so a stuck screen is logged once

    def update(self):
        """Draw the current state. Returns whether it was drawn; never raises."""
        if self.device is None:
            return False
        try:
            self.device.display(render(self.smoker.snapshot(), self.worker.error(), self.device.size))
        except Exception as e:
            if repr(e) != self.failure:
                log.warning('OLED display update failed: %r', e)
                self.failure = repr(e)
            return False
        self.failure = None
        return True

    def cleanup(self):
        """Blank the screen, e.g. at shutdown, so it does not show a frozen reading."""
        if self.device is None:
            return
        try:
            self.device.clear()
        except Exception:
            log.exception('Could not clear the OLED display')

    def run(self):
        while self.smoker.running:
            self.update()
            time.sleep(self.interval)

    def start(self):
        if self.device is not None:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
