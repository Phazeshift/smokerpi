import logging
import os
import threading
import time
from contextlib import contextmanager

from .config import applyConfig
from .hardware.blower import Blower
from .hardware.damper2 import Damper, emulatedDamper
from .hardware.max31855 import MAX31855, TestMAX31855
from .hardware.pitcontroller import PitController
from .history import History, GRAPH_POINTS
from .pid import AntiWindupPID

log = logging.getLogger('smokerpi')


class ControlBusy(Exception):
    """The control lock was not free in time: the loop is stuck in a hardware call."""


class DamperNotMoved(Exception):
    """A setting was saved but the damper could not be moved to match it."""


class Smoker:
    """Everything SmokerPi knows and controls: the settings, the hardware, the PID, whether the
    PID is in control, and the graph.

    The routes and the worker (worker.py) run on different threads, so anything that changes
    the hardware or the control mode does it under self.lock. The control operations here take
    it themselves and raise ControlBusy if it is not free within lockTimeout seconds; the worker
    holds it for its whole pass."""

    def __init__(self, config, configFile, home, test, clock=time.monotonic):
        self.config = config
        self.configFile = configFile
        self.home = home
        self.test = test                # emulated hardware (off the Pi)
        self.clock = clock
        self.lock = threading.Lock()
        # A worker pass holds the lock for about a second when the damper moves.
        self.lockTimeout = 5
        self.running = True             # False once cleanup() has released the hardware

        self.temperature = 0
        # Whether the PID is in control. This is the only switch: pid.auto_mode follows it.
        self.automatic = False
        # Paused like the rest of manual mode (simple_pid starts in auto mode, so it used to
        # build up an integral before the first switch to automatic).
        self.pid = AntiWindupPID(1, 0.1, 0.05, setpoint=100, auto_mode=False)
        self.pid.sample_time = 0.1
        self.pid.output_limits = (0, 100)

        makeDamper = emulatedDamper if test else Damper
        self.damper = makeDamper(config['damper_pin'], config['damper_minimum'], config['damper_maximum'],
                                 bool(config.get('damper_invert', False)))
        self.blower = Blower(config['blower_pin1'], config['blower_pin2'])
        applyConfig(self)
        self.pitController = PitController(self.blower, self.damper)
        if test:
            self.thermocouple = TestMAX31855(self.damper)
        else:
            self.thermocouple = MAX31855(config['cs_pin'], config['clock_pin'], config['data_pin'])

        # The graph survives a restart: its points are kept in data/history.csv (next to
        # config.json and log/, which update.sh leaves alone), and the newest are loaded back
        # here, keeping their point numbers so the numbering carries on.
        self.history = History(os.path.join(home, 'data', 'history.csv'),
                               int(float(config.get('history_max_mb', 5)) * 1024 * 1024))
        self.graphData = self.history.recent(GRAPH_POINTS)
        self.graphIndex = self.graphData[-1]['i'] + 1 if self.graphData else 0
        self.graphLast = 0

    @contextmanager
    def control(self):
        """Hold the control lock, or raise ControlBusy rather than wait for ever."""
        if not self.lock.acquire(timeout=self.lockTimeout):
            raise ControlBusy('The control loop is busy or stuck; nothing was changed. Try again.')
        try:
            yield
        finally:
            self.lock.release()

    def _manual(self):
        self.automatic = False
        self.pid.auto_mode = False

    def setAutomatic(self, enabled):
        with self.control():
            if enabled:
                self.automatic = True
                self.pid.auto_mode = True
            else:
                self._manual()
                self.blower.off()

    def setBlower(self, on):
        """Manual control: takes the PID out of the loop."""
        with self.control():
            self._manual()
            if on:
                self.blower.on()
            else:
                self.blower.off()

    def setDamper(self, open):
        """Manual control: takes the PID out of the loop."""
        with self.control():
            self._manual()
            self.damper.open(100 if open else 0)

    def updateConfig(self, values):
        """Apply and save validated settings. Raises DamperNotMoved if damper_invert changed
        and the damper could not be moved to match; the setting is kept either way."""
        with self.control():
            self.config.update(values)
            invertChanged = applyConfig(self)
            self.configFile.saveConfig(self.config)
            if invertChanged:
                # The PID would not re-send an unchanged position, so move it now.
                try:
                    self.damper.reposition()
                except Exception as e:
                    log.exception('Could not move the damper after changing damper_invert')
                    raise DamperNotMoved('Saved, but the damper could not be moved to match: %s' % e)

    def publicConfig(self):
        return {key: value for key, value in self.config.items() if key != 'password'}

    def snapshot(self):
        """The current state, as /api/state reports it (less the worker's health)."""
        return {
            'temperature': self.temperature,
            'targetTemperature': self.config['set_temperature'],
            'blower': self.blower.state,
            'pid': self.automatic,
            'damper': self.damper.state,
        }

    def graphSince(self, fromIndex):
        # Copy first: the worker appends to the list and trims its front meanwhile, and walking
        # a list that shifts underneath skips points. list() copies it in one step.
        return [point for point in list(self.graphData) if point['i'] >= fromIndex]

    def cleanup(self):
        """Release the hardware. Waits for a pass in progress so it cannot move the hardware
        afterwards, but not for ever: a stuck loop must not stop the cleanup."""
        print("Cleanup")
        log.info('Cleaning up')
        locked = self.lock.acquire(timeout=self.lockTimeout)
        try:
            self.running = False
            self.blower.cleanup()
            self.thermocouple.cleanup()
            self.damper.cleanup()
        finally:
            if locked:
                self.lock.release()
