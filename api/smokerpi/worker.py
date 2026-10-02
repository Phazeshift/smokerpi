import threading
import time
from datetime import datetime

from .history import GRAPH_POINTS, GRAPH_TIME


class Worker:
    """The control loop: polls the temperature, runs the PID and records graph points.

    The live state stays on the app (app.smokerpi_*), where the routes and the tests read it."""

    def __init__(self, app):
        self.app = app

    def monitorTemp(self):
        # The thermocouple sometimes fails to answer one check and answers the next, so a
        # failed read keeps the last good temperature. Only a sensor that has been silent
        # for sensor_timeout seconds is a failure, which stops the PID and the blower.
        app = self.app
        try:
            app.smokerpi_currentTemperature = app.smokerpi_max31855.get()
            app.smokerpi_lastReading = app.smokerpi_clock()
        except Exception as e:
            silent = app.smokerpi_clock() - app.smokerpi_lastReading
            if silent >= app.smokerpi_config['sensor_timeout']:
                raise
            app.logger.warning('Temperature read failed (%r), using the last reading; no good reading for %.0fs', e, silent)

    def updatePid(self):
        app = self.app
        output = app.smokerpi_pid(app.smokerpi_currentTemperature)
        if (app.smokerpi_pidRunning):
            app.smokerpi_pitController.set(output)

    def graphData(self):
        app = self.app
        graphLast = time.time()
        if (graphLast - app.smokerpi_graphLast < app.smokerpi_config['graph_interval']):
            return 0
        now = datetime.now()
        point = { 'i': app.smokerpi_graphIndex, 'x': now.strftime(GRAPH_TIME), 't': app.smokerpi_currentTemperature, 'b': app.smokerpi_blower.state,'d': app.smokerpi_damper.state, 's': app.smokerpi_config['set_temperature'] }
        app.smokerpi_graphData.append(point)
        while (len(app.smokerpi_graphData) > GRAPH_POINTS):
            del app.smokerpi_graphData[0]
        app.smokerpi_graphIndex = app.smokerpi_graphIndex + 1
        app.smokerpi_graphLast = graphLast
        # Never raises: a disk problem is logged and must not touch the control loop.
        app.smokerpi_history.append(point['i'], now, point['t'], point['b'], point['d'], point['s'])

    def runStep(self, name, step):
        app = self.app
        try:
            step()
            app.smokerpi_stepErrors.pop(name, None)
            return True
        except Exception as e:
            app.logger.exception('Worker step failed: %s', name)
            app.smokerpi_stepErrors[name] = str(e) or type(e).__name__
            return False

    def failSafe(self):
        # After a hardware or sensor error leave the blower off rather than running unsupervised.
        try:
            self.app.smokerpi_blower.off()
        except Exception:
            self.app.logger.exception('Fail-safe could not switch the blower off')

    def step(self):
        """One pass of the control loop. It never raises.

        An exception here used to kill the worker thread silently, which froze the
        temperature reading and the PID and left the blower in whatever state it was in."""
        app = self.app
        sensorOk = self.runStep('temperature read', self.monitorTemp)
        # Do not act on a reading that could not be taken.
        controlOk = self.runStep('PID update', self.updatePid) if sensorOk else False
        self.runStep('graph update', self.graphData)
        if not (sensorOk and controlOk):
            self.failSafe()
        app.smokerpi_lastPass = app.smokerpi_clock()

    def error(self):
        """Why the control loop is not working, or None. Shown to the user, who would
        otherwise only see a frozen temperature."""
        app = self.app
        silent = app.smokerpi_clock() - app.smokerpi_lastPass
        if silent > max(30, 3 * app.smokerpi_workerInterval):
            return 'Control loop has stopped (no pass for %d seconds)' % silent
        if app.smokerpi_stepErrors:
            return '; '.join('%s: %s' % item for item in app.smokerpi_stepErrors.items())
        return None

    def run(self):
        app = self.app
        while app.smokerpi_running:
            self.step()
            time.sleep(app.smokerpi_workerInterval)
        print("Worker complete")

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        return thread
