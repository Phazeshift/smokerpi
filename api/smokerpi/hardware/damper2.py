import time

try:
    import pigpio
except (RuntimeError, ModuleNotFoundError):
    pigpio = None

from . import fakepigpio

class Damper:    
    def __init__(self, pin = 13, min = 500, max = 2500, invert = False, pigpioModule = None, settle = 1):
        # pigpioModule replaces the real pigpio (see emulatedDamper); settle is how long a
        # move pulses the servo before stopping, in seconds.
        self.pigpioModule = pigpioModule
        self.settle = settle
        self.min = min
        self.max = max
        # Some linkages open the damper at the smaller pulse width. Position 100 always means
        # open; invert only changes which end of the pulse range it is sent as.
        self.invert = invert
        self.pi = None
        self.pin = pin
        self.state = -1
        self.open(100)

    def connect(self):
        # pigpiod can be restarted or crash while we run, which leaves an old connection
        # failing for good, so a connection is dropped on any error and made again on the
        # next move. pigpio.pi() does not raise when the daemon is down; it returns an
        # object with connected False.
        if self.pi is None:
            pi = (self.pigpioModule or pigpio).pi()
            if not pi.connected:
                pi.stop()
                raise ConnectionError('Cannot connect to pigpiod')
            self.pi = pi
        return self.pi

    def disconnect(self):
        pi, self.pi = self.pi, None
        if pi is not None:
            try:
                pi.stop()
            except Exception:
                pass

    def cleanup(self):
        try:
            if self.pi is not None:
                self.pi.set_servo_pulsewidth(self.pin, 0)
        finally:
            self.disconnect()

    def reposition(self):
        # Send the current position again, e.g. after invert changed. If the move fails the
        # position is left unknown (-1) so the next open() of the same value is sent rather
        # than skipped as a no-op.
        value, self.state = self.state, -1
        if value != -1:
            self.open(value)

    def open(self, value):        
        if (value == self.state):
            return
        travel = (100 - value) if self.invert else value
        pos = (((self.max - self.min) / 100) * travel) + self.min
        try:
            pi = self.connect()
            pi.set_servo_pulsewidth(self.pin, pos)
            time.sleep(self.settle)
            pi.set_servo_pulsewidth(self.pin, 0)
        except Exception:
            self.disconnect()
            raise
        self.state = value            

def emulatedDamper(pin, min, max, invert = False):
    """The real Damper against the fake pigpio, without waiting for a servo to settle: what
    the app uses off the Pi, so the pulse mapping, invert and reconnect logic run there too."""
    return Damper(pin, min, max, invert, pigpioModule=fakepigpio, settle=0)

if __name__ == "__main__":        
    damper = Damper()
    try:
        while(True):        
            damper.open(0)
            time.sleep(self.settle)
            damper.open(100)
            time.sleep(self.settle)
    except KeyboardInterrupt:
        pass        
    damper.cleanup()
    print('done')