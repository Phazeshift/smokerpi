try:
    import pigpio
    import time
except (RuntimeError, ModuleNotFoundError):
    pass

class Damper:    
    def __init__(self, pin = 13, min = 500, max = 2500, invert = False):
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
            pi = pigpio.pi()
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
            time.sleep(1)
            pi.set_servo_pulsewidth(self.pin, 0)
        except Exception:
            self.disconnect()
            raise
        self.state = value            

class TestDamper():
    def __init__(self):
        self.state = -1
        self.invert = False
        pass

    def reposition(self):
        pass

    def open(self, value):
        self.state = value
        pass

    def cleanup(self):
        pass

if __name__ == "__main__":        
    damper = Damper()
    try:
        while(True):        
            damper.open(0)
            time.sleep(1)
            damper.open(100)
            time.sleep(1)
    except KeyboardInterrupt:
        pass        
    damper.cleanup()
    print('done')