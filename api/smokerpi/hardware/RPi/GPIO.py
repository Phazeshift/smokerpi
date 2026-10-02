#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Stand-in for the RPi.GPIO package off the Pi (the hardware modules fall back to it when the
real one will not import).

It enforces the rules the real library does, with the same constants and error messages:
a numbering mode before any setup, a pin set up as an output before it is written or used
for PWM, set up at all before it is read. It used to accept any call, so a blower that never
set its pins up as outputs passed CI and then returned 500 on the Pi.

Like the real library its state is process-wide; cleanup() clears it.
'''

BOARD = 10
BCM = 11

OUT = 0
IN = 1

LOW = 0
HIGH = 1

PUD_OFF = 20
PUD_DOWN = 21
PUD_UP = 22

RISING = 31
FALLING = 32
BOTH = 33

RPI_INFO = {'INFO': 'Fake GPIO', 'P1_REVISION': 3}

VERSION = '0.7.1'

# Print each call, so an emulated server shows what it would do to the pins.
VERBOSE = True

# The channels with a GPIO behind them on a 40-pin Pi, in each numbering mode.
_CHANNELS = {
    BCM: set(range(28)),
    BOARD: {3, 5, 7, 8, 10, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24, 26, 27, 28, 29,
            31, 32, 33, 35, 36, 37, 38, 40},
}

_mode = None
_direction = {}     # channel -> OUT or IN
_level = {}         # channel -> LOW or HIGH
_pwm = {}           # channel -> PWM


def print_data(func):
    def verbose(*args, **kwargs):
        if VERBOSE:
            print(func.__name__, args, kwargs)
        return func(*args, **kwargs)
    verbose.__name__ = func.__name__
    return verbose


def _channel(channel):
    if _mode is None:
        raise RuntimeError('Please set pin numbering mode using GPIO.setmode(GPIO.BOARD) or GPIO.setmode(GPIO.BCM)')
    if channel not in _CHANNELS[_mode]:
        raise ValueError('The channel sent is invalid on a Raspberry Pi')
    return channel


class PWM(object):

    @print_data
    def __init__(self, channel, frequency):
        _channel(channel)
        if _direction.get(channel) != OUT:
            raise RuntimeError('You must setup() the GPIO channel as an output first')
        if channel in _pwm:
            raise RuntimeError('A PWM object already exists for this GPIO channel')
        if frequency <= 0.0:
            raise ValueError('frequency must be greater than 0.0')
        self.channel = channel
        self.frequency = frequency
        self.dc = 0
        _pwm[channel] = self

    @staticmethod
    def _check(dc):
        if dc < 0.0 or dc > 100.0:
            raise ValueError('dutycycle must have a value from 0.0 to 100.0')

    @print_data
    def start(self, dc):
        self._check(dc)
        self.dc = dc

    @print_data
    def ChangeFrequency(self, freq):
        if freq <= 0.0:
            raise ValueError('frequency must be greater than 0.0')
        self.frequency = freq

    @print_data
    def ChangeDutyCycle(self, dc):
        self._check(dc)
        self.dc = dc

    @print_data
    def stop(self):
        if _pwm.get(self.channel) is self:
            del _pwm[self.channel]


@print_data
def setmode(mode):
    global _mode
    if mode not in _CHANNELS:
        raise ValueError('An invalid mode was passed to setmode()')
    if _mode is not None and mode != _mode:
        raise ValueError('A different mode has already been set!')
    _mode = mode


def getmode():
    return _mode


@print_data
def setwarnings(flag):
    pass


@print_data
def setup(channel, direction, pull_up_down=PUD_OFF, initial=None):
    for one in (channel if isinstance(channel, (list, tuple)) else [channel]):
        _channel(one)
        if direction not in (OUT, IN):
            raise ValueError('An invalid direction was passed to setup()')
        _direction[one] = direction
        if direction == OUT:
            _level[one] = HIGH if initial in (HIGH, True) else LOW
        else:
            _level[one] = LOW


def gpio_function(channel):
    return _direction.get(_channel(channel), IN)


@print_data
def output(channel, value):
    for one in (channel if isinstance(channel, (list, tuple)) else [channel]):
        _channel(one)
        if _direction.get(one) != OUT:
            raise RuntimeError('The GPIO channel has not been set up as an OUTPUT')
        _level[one] = HIGH if value else LOW


@print_data
def input(channel):
    _channel(channel)
    if channel not in _direction:
        raise RuntimeError('You must setup() the GPIO channel first')
    return _level[channel]


@print_data
def cleanup(channel=None):
    global _mode
    if channel is None:
        _mode = None
        _direction.clear()
        _level.clear()
        _pwm.clear()
        return
    for one in (channel if isinstance(channel, (list, tuple)) else [channel]):
        _direction.pop(one, None)
        _level.pop(one, None)
        _pwm.pop(one, None)
