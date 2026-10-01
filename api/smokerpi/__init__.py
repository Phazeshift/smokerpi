from flask import (Flask, request, jsonify)
import logging
from logging.handlers import RotatingFileHandler
from flask import json
from werkzeug.exceptions import InternalServerError, NotFound
from .hardware.blower import Blower
from .hardware.damper2 import Damper, TestDamper
from .hardware.pitcontroller import PitController
from .hardware.max31855 import MAX31855, TestMAX31855, MAX31855Error
from .config import Config, validateEditableConfig
from simple_pid import PID
from datetime import datetime
import array
import platform
import time
import os
import json
import threading


def create_app(test_config=None):
    app = Flask(__name__, static_folder='../../build', static_url_path='/')

    os.makedirs('./log', exist_ok=True)
    logging.basicConfig(filename='./log/app.log',level=logging.DEBUG)

    app.logger.info("### NEW STARTUP Version 0.1")
    app.config['SECRET_KEY'] = 'smokerpi-secret!'

    app.smokerpi_test = platform.system() == 'Windows' or os.environ.get('SMOKERPI_TEST') == '1'
    app.smokerpi_currentTemperature = 0
    app.smokerpi_currentState = {}
    app.smokerpi_pidRunning = False
    app.smokerpi_workerInterval = 10
    app.smokerpi_graphLast = 0
    app.smokerpi_pid = PID(1, 0.1, 0.05, setpoint=100)
    app.smokerpi_pid.sample_time = 0.1
    app.smokerpi_pid.output_limits = (0, 100)

    app.smokerpi_graphData = []
    app.smokerpi_graphIndex = 0
    app.smokerpi_running = True
    app.smokerpi_clock = time.monotonic
    app.smokerpi_lastReading = app.smokerpi_clock()
    app.smokerpi_lastPass = app.smokerpi_clock()
    app.smokerpi_stepErrors = {}
    app.smokerpi_config = { }

    def configure():
        if (app.smokerpi_test):
            app.smokerpi_damper = TestDamper()
        else:
            app.smokerpi_damper = Damper(app.smokerpi_config['damper_pin'], app.smokerpi_config['damper_minimum'], app.smokerpi_config['damper_maximum'])
        app.smokerpi_blower = Blower(app.smokerpi_config['blower_pin1'], app.smokerpi_config['blower_pin2'])
        app.smokerpi_pid.setpoint = app.smokerpi_config['set_temperature']
        app.smokerpi_pitController = PitController(app.smokerpi_blower, app.smokerpi_damper)
        if (app.smokerpi_test):
            app.smokerpi_max31855 = TestMAX31855(app.smokerpi_damper)
        else:
            app.smokerpi_max31855 = MAX31855(app.smokerpi_config['cs_pin'], app.smokerpi_config['clock_pin'], app.smokerpi_config['data_pin'])

    def setup():
        if test_config is not None and 'config' in test_config:
            app.smokerpi_config = test_config['config']
        else:
            app.smokerpi_config = Config(app.smokerpi_test).loadConfig()
        app.smokerpi_workerInterval = app.smokerpi_config['worker_interval']
        configure()
        if test_config is None or test_config.get('start_worker', True):
            app.worker = threading.Thread(target=worker)
            app.worker.daemon = True
            app.worker.start()

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.errorhandler(NotFound)
    def client_side_route(e):
        # The React app does its own routing (e.g. /config), so a page refresh or a
        # deep link asks the server for a path it has no file for. Serve the app shell
        # for those. API paths and requests for files (anything with an extension)
        # stay real 404s, as does everything when there is no build to serve.
        last_segment = request.path.rsplit('/', 1)[-1]
        has_build = os.path.isfile(os.path.join(app.static_folder, 'index.html'))
        if (request.method in ('GET', 'HEAD') and has_build
                and not request.path.startswith('/api/') and '.' not in last_segment):
            return app.send_static_file('index.html')
        return e

    @app.route('/api/graph')
    def graph():
        fromIndex = int(request.args.get("from", "0"))
        graphData = []
        for val in app.smokerpi_graphData:
            if (val['i'] >= fromIndex):
                graphData.append(val)
        return json.dumps(graphData)

    def workerError():
        """Why the control loop is not working, or None. Shown to the user, who would
        otherwise only see a frozen temperature."""
        silent = app.smokerpi_clock() - app.smokerpi_lastPass
        if silent > max(30, 3 * app.smokerpi_workerInterval):
            return 'Control loop has stopped (no pass for %d seconds)' % silent
        if app.smokerpi_stepErrors:
            return '; '.join('%s: %s' % item for item in app.smokerpi_stepErrors.items())
        return None

    @app.route('/api/state')
    def state():
        app.smokerpi_currentState = { 'temperature': app.smokerpi_currentTemperature, 'targetTemperature': app.smokerpi_config['set_temperature'], 'blower': app.smokerpi_blower.state, 'pid': app.smokerpi_pidRunning, 'damper': app.smokerpi_damper.state, 'workerError': workerError() }
        return json.dumps(app.smokerpi_currentState)

    @app.route('/api/config', methods = ['GET', 'POST'])
    def config():
        if request.method == "POST":
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                return jsonify(error='Expected a JSON object'), 400
            values, errors = validateEditableConfig(payload)
            if errors:
                message = 'Invalid configuration: ' + '; '.join('%s %s' % (k, v) for k, v in errors.items())
                return jsonify(error=message, errors=errors), 400
            app.smokerpi_config.update(values)
            app.smokerpi_pid.setpoint = app.smokerpi_config['set_temperature']
            app.smokerpi_damper.min = app.smokerpi_config['damper_minimum']
            app.smokerpi_damper.max = app.smokerpi_config['damper_maximum']
            Config(app.smokerpi_test).saveConfig(app.smokerpi_config)
        return json.dumps(app.smokerpi_config)

    @app.route('/api/blower', methods = ['POST'])
    def blower():
        app.smokerpi_pidRunning = False
        app.smokerpi_pid.auto_mode = False
        if (bool(request.json['enabled'])):
          app.smokerpi_blower.on()
        else:
          app.smokerpi_blower.off()
        return json.dumps(app.smokerpi_config)

    @app.route('/api/damper', methods = ['POST'])
    def damper():
        app.smokerpi_pidRunning = False
        app.smokerpi_pid.auto_mode = False
        if (bool(request.json['enabled'])):
          app.smokerpi_damper.open(100)
        else:
          app.smokerpi_damper.open(0)
        return json.dumps(app.smokerpi_config)

    @app.route('/api/pid', methods = ['POST'])
    def pid():
        if (request.json['enabled']):
            app.smokerpi_pidRunning = True
            app.smokerpi_pid.auto_mode = True
        else:
            app.smokerpi_pidRunning = False
            app.smokerpi_pid.auto_mode = False
            app.smokerpi_blower.off()
        return json.dumps(app.smokerpi_config)

    def monitorTemp():
        # The thermocouple sometimes fails to answer one check and answers the next, so a
        # failed read keeps the last good temperature. Only a sensor that has been silent
        # for sensor_timeout seconds is a failure, which stops the PID and the blower.
        try:
            app.smokerpi_currentTemperature = app.smokerpi_max31855.get()
            app.smokerpi_lastReading = app.smokerpi_clock()
        except Exception as e:
            silent = app.smokerpi_clock() - app.smokerpi_lastReading
            if silent >= app.smokerpi_config['sensor_timeout']:
                raise
            app.logger.warning('Temperature read failed (%r), using the last reading; no good reading for %.0fs', e, silent)

    def updatePid():
        output = app.smokerpi_pid(app.smokerpi_currentTemperature)
        if (app.smokerpi_pidRunning):
          app.smokerpi_pitController.set(output)

    def graphData():
        graphLast = time.time()
        if (graphLast - app.smokerpi_graphLast < app.smokerpi_config['graph_interval']):
            return 0
        app.smokerpi_graphData.append({ 'i': app.smokerpi_graphIndex, 'x': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 't': app.smokerpi_currentTemperature, 'b': app.smokerpi_blower.state,'d': app.smokerpi_damper.state, 's': app.smokerpi_config['set_temperature'] })
        while (len(app.smokerpi_graphData) > 2000):
            del app.smokerpi_graphData[0]
        app.smokerpi_graphIndex = app.smokerpi_graphIndex + 1
        app.smokerpi_graphLast = graphLast

    def runStep(name, step):
        try:
            step()
            app.smokerpi_stepErrors.pop(name, None)
            return True
        except Exception as e:
            app.logger.exception('Worker step failed: %s', name)
            app.smokerpi_stepErrors[name] = str(e) or type(e).__name__
            return False

    def failSafe():
        # After a hardware or sensor error leave the blower off rather than running unsupervised.
        try:
            app.smokerpi_blower.off()
        except Exception:
            app.logger.exception('Fail-safe could not switch the blower off')

    def workerStep():
        """One pass of the control loop. It never raises.

        An exception here used to kill the worker thread silently, which froze the
        temperature reading and the PID and left the blower in whatever state it was in."""
        sensorOk = runStep('temperature read', monitorTemp)
        # Do not act on a reading that could not be taken.
        controlOk = runStep('PID update', updatePid) if sensorOk else False
        runStep('graph update', graphData)
        if not (sensorOk and controlOk):
            failSafe()
        app.smokerpi_lastPass = app.smokerpi_clock()

    app.smokerpi_workerStep = workerStep

    def worker():
        while app.smokerpi_running:
            workerStep()
            time.sleep(app.smokerpi_workerInterval)
        print("Worker complete")

    @app.errorhandler(InternalServerError)
    def handle_500(e):
        app.logger.error('Unhandled error: %s', e.original_exception or e, exc_info=e.original_exception)
        return e

    def cleanupHardware():
        print("Cleanup")
        app.logger.info('Cleaning up')
        app.smokerpi_running = False
        app.smokerpi_blower.cleanup()
        app.smokerpi_max31855.cleanup()
        app.smokerpi_damper.cleanup()

    app.cleanupHardware = cleanupHardware

    setup()

    return app


app = create_app()
cleanupHardware = app.cleanupHardware
