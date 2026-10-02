'''Stand-in for the pigpio module, which the emulated damper talks to off the Pi.

It rejects what pigpio rejects, with pigpio's messages: a pin that is not a user GPIO
(0-31) and a servo pulse width other than 0 (off) or 500-2500 microseconds. Each connection
records the pulses it was sent, for the tests.'''


class error(Exception):
    pass


class pi(object):
    def __init__(self):
        self.connected = True
        self.pulses = []

    def set_servo_pulsewidth(self, user_gpio, pulsewidth):
        if not 0 <= user_gpio <= 31:
            raise error('GPIO not 0-31')
        if pulsewidth != 0 and not 500 <= pulsewidth <= 2500:
            raise error('pulsewidth not 0 or 500-2500')
        self.pulses.append((user_gpio, pulsewidth))
        return 0

    def stop(self):
        self.connected = False
