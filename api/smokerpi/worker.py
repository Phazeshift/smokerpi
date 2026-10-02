import logging
import threading
import time
from datetime import datetime

from .history import GRAPH_POINTS, GRAPH_TIME

log = logging.getLogger('smokerpi')


class Worker:
    """The control loop: polls the temperature, runs the PID and records graph points on the
    Smoker (smoker.py), and keeps track of its own health for /api/state and the watchdog."""

    def __init__(self, smoker):
        self.smoker = smoker
        self.interval = smoker.config['worker_interval']
        self.lastReading = smoker.clock()       # the last good temperature read
        self.lastPass = smoker.clock()          # the last completed pass
        self.stepErrors = {}                    # step name -> message, while it is failing
        self.reportedStall = None
        self.thread = None
        self.watchdogThread = None

    def monitorTemp(self):
        # The thermocouple sometimes fails to answer one check and answers the next, so a
        # failed read keeps the last good temperature. Only a sensor that has been silent
        # for sensor_timeout seconds is a failure, which stops the PID and the blower.
        smoker = self.smoker
        try:
            smoker.temperature = smoker.thermocouple.get()
            self.lastReading = smoker.clock()
        except Exception as e:
            silent = smoker.clock() - self.lastReading
            if silent >= smoker.config['sensor_timeout']:
                raise
            log.warning('Temperature read failed (%r), using the last reading; no good reading for %.0fs', e, silent)

    def updatePid(self):
        smoker = self.smoker
        output = smoker.pid(smoker.temperature)
        if smoker.automatic:
            smoker.pitController.set(output)

    def graphData(self):
        smoker = self.smoker
        graphLast = time.time()
        if (graphLast - smoker.graphLast < smoker.config['graph_interval']):
            return 0
        now = datetime.now()
        point = { 'i': smoker.graphIndex, 'x': now.strftime(GRAPH_TIME), 't': smoker.temperature, 'b': smoker.blower.state,'d': smoker.damper.state, 's': smoker.config['set_temperature'] }
        smoker.graphData.append(point)
        while (len(smoker.graphData) > GRAPH_POINTS):
            del smoker.graphData[0]
        smoker.graphIndex = smoker.graphIndex + 1
        smoker.graphLast = graphLast
        # Never raises: a disk problem is logged and must not touch the control loop.
        smoker.history.append(point['i'], now, point['t'], point['b'], point['d'], point['s'])

    def runStep(self, name, step):
        try:
            step()
            self.stepErrors.pop(name, None)
            return True
        except Exception as e:
            log.exception('Worker step failed: %s', name)
            self.stepErrors[name] = str(e) or type(e).__name__
            return False

    def failSafe(self):
        # After a hardware or sensor error leave the blower off rather than running unsupervised.
        try:
            self.smoker.blower.off()
        except Exception:
            log.exception('Fail-safe could not switch the blower off')

    def step(self):
        """One pass of the control loop. It never raises.

        An exception here used to kill the worker thread silently, which froze the
        temperature reading and the PID and left the blower in whatever state it was in.

        The hardware is only touched under smoker.lock, which the control operations take
        too: otherwise a button press could land between this pass deciding the PID is
        running and moving the hardware, and be undone by it. The temperature read (slow,
        bit-banged) stays outside the lock."""
        smoker = self.smoker
        sensorOk = self.runStep('temperature read', self.monitorTemp)
        with smoker.lock:
            if not smoker.running:
                return          # Smoker.cleanup() has released the hardware
            # Do not act on a reading that could not be taken.
            controlOk = self.runStep('PID update', self.updatePid) if sensorOk else False
            self.runStep('graph update', self.graphData)
            if not (sensorOk and controlOk):
                self.failSafe()
        self.lastPass = smoker.clock()

    def stalledFor(self):
        """Seconds since the last completed pass if that is past the stall limit, else None."""
        silent = self.smoker.clock() - self.lastPass
        return silent if silent > max(30, 3 * self.interval) else None

    def error(self):
        """Why the control loop is not working, or None. Shown to the user, who would
        otherwise only see a frozen temperature."""
        silent = self.stalledFor()
        if silent is not None:
            return 'Control loop has stopped (no pass for %d seconds)' % silent
        if self.stepErrors:
            return '; '.join('%s: %s' % item for item in self.stepErrors.items())
        return None

    def checkWatchdog(self):
        """Switch the blower off if the loop has stalled, e.g. stuck in a hardware call where
        its own fail-safe can never run. A stuck loop usually holds the lock, so this does
        not take it: Blower.off() only writes two GPIO pins. Logged once per stall."""
        silent = self.stalledFor()
        if silent is None:
            return
        # Remember which pass the loop stalled after, so a recovery and a new stall between
        # two checks is still reported.
        if self.reportedStall != self.lastPass:
            log.error('Control loop has stopped (no pass for %d seconds); switching the blower off', silent)
            self.reportedStall = self.lastPass
        self.failSafe()

    def run(self):
        while self.smoker.running:
            self.step()
            time.sleep(self.interval)
        print("Worker complete")

    def watch(self):
        while self.smoker.running:
            time.sleep(min(5, self.interval))
            try:
                self.checkWatchdog()
            except Exception:
                log.exception('Watchdog check failed')

    def start(self):
        """Start the control loop and its watchdog, each on a daemon thread."""
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        self.watchdogThread = threading.Thread(target=self.watch, daemon=True)
        self.watchdogThread.start()
