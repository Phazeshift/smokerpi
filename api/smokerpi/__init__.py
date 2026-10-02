from flask import (Flask, Response, request, jsonify)
import logging
from logging.handlers import RotatingFileHandler
from flask import json
from werkzeug.exceptions import InternalServerError, NotFound
from .hardware.blower import Blower
from .hardware.damper2 import Damper, TestDamper
from .hardware.pitcontroller import PitController
from .hardware.max31855 import MAX31855, TestMAX31855, MAX31855Error
from .config import Config, validateEditableConfig
from .pid import AntiWindupPID
from .history import History, GRAPH_TIME
from datetime import datetime
import array
import platform
import time
import os
import json
import threading
import base64
import binascii
import hmac


def configureLogging():
    """Log to ./log/app.log, capped at 4 x 1 MB so it cannot fill the Pi's SD card.

    Replaces any handler a previous call added, so creating the app more than once (as the
    tests do) does not log every line twice."""
    root = logging.getLogger()
    for old in [h for h in root.handlers if getattr(h, 'smokerpi', False)]:
        root.removeHandler(old)
        old.close()
    handler = RotatingFileHandler('./log/app.log', maxBytes=1024 * 1024, backupCount=3)
    handler.smokerpi = True
    handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


GRAPH_POINTS = 2000   # how many points the graph keeps in memory, and restores after a restart


def create_app(test_config=None):
    app = Flask(__name__, static_folder='../../build', static_url_path='/')

    os.makedirs('./log', exist_ok=True)
    configureLogging()

    app.logger.info("### NEW STARTUP Version 0.1")

    app.smokerpi_test = platform.system() == 'Windows' or os.environ.get('SMOKERPI_TEST') == '1'
    app.smokerpi_currentTemperature = 0
    app.smokerpi_currentState = {}
    app.smokerpi_pidRunning = False
    app.smokerpi_workerInterval = 10
    app.smokerpi_graphLast = 0
    app.smokerpi_pid = AntiWindupPID(1, 0.1, 0.05, setpoint=100)
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

    def applyConfig():
        """Push the settings in the config onto the PID and the damper. Used at startup and
        after a POST /api/config, so the two cannot drift apart. Returns True if the damper
        direction changed."""
        config = app.smokerpi_config
        app.smokerpi_pid.setpoint = config['set_temperature']
        app.smokerpi_pid.tunings = (float(config['pid_kp']), float(config['pid_ki']), float(config['pid_kd']))
        damper = app.smokerpi_damper
        damper.min = config['damper_minimum']
        damper.max = config['damper_maximum']
        invert = bool(config.get('damper_invert', False))
        invertChanged = damper.invert != invert
        damper.invert = invert
        return invertChanged

    def configure():
        config = app.smokerpi_config
        if (app.smokerpi_test):
            app.smokerpi_damper = TestDamper()
        else:
            app.smokerpi_damper = Damper(config['damper_pin'], config['damper_minimum'], config['damper_maximum'], bool(config.get('damper_invert', False)))
        app.smokerpi_blower = Blower(config['blower_pin1'], config['blower_pin2'])
        applyConfig()
        app.smokerpi_pitController = PitController(app.smokerpi_blower, app.smokerpi_damper)
        if (app.smokerpi_test):
            app.smokerpi_max31855 = TestMAX31855(app.smokerpi_damper)
        else:
            app.smokerpi_max31855 = MAX31855(config['cs_pin'], config['clock_pin'], config['data_pin'])

    def setup():
        if test_config is not None and 'config' in test_config:
            app.smokerpi_config = test_config['config']
        else:
            app.smokerpi_config = Config(app.smokerpi_test).loadConfig()
        app.smokerpi_workerInterval = app.smokerpi_config['worker_interval']
        configure()
        # The graph survives a restart: its points are kept in data/history.csv (next to config.json
        # and log/, which update.sh leaves alone), and the newest are loaded back here, keeping their point numbers so the numbering carries on.
        app.smokerpi_history = History(os.path.join('data', 'history.csv'),
                                       int(float(app.smokerpi_config.get('history_max_mb', 5)) * 1024 * 1024))
        app.smokerpi_graphData = app.smokerpi_history.recent(GRAPH_POINTS)
        app.smokerpi_graphIndex = app.smokerpi_graphData[-1]['i'] + 1 if app.smokerpi_graphData else 0
        if test_config is None or test_config.get('start_worker', True):
            app.worker = threading.Thread(target=worker)
            app.worker.daemon = True
            app.worker.start()

    def passwordSupplied():
        """The password from an HTTP Basic Authorization header, or None. Any username."""
        scheme, _, token = request.headers.get('Authorization', '').partition(' ')
        if scheme.lower() != 'basic':
            return None
        try:
            _, colon, password = base64.b64decode(token.strip(), validate=True).decode('utf-8').partition(':')
        except (binascii.Error, UnicodeDecodeError):
            return None
        return password if colon else None

    @app.before_request
    def requirePassword():
        # Protects the page and the API alike. With no password configured everything is open.
        expected = app.smokerpi_config.get('password', '')
        if not expected:
            return None
        supplied = passwordSupplied()
        if supplied is not None and hmac.compare_digest(supplied.encode('utf-8'), expected.encode('utf-8')):
            return None
        return Response('Password required', 401, {'WWW-Authenticate': 'Basic realm="SmokerPi", charset="UTF-8"'})

    def publicConfig():
        return {key: value for key, value in app.smokerpi_config.items() if key != 'password'}

    def enabledFlag():
        """The `enabled` boolean of a control request, or None if the body is not valid."""
        payload = request.get_json(silent=True)
        if isinstance(payload, dict) and isinstance(payload.get('enabled'), bool):
            return payload['enabled']
        return None

    def badEnabled():
        return jsonify(error='Expected a JSON object with a true or false "enabled"'), 400

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

    @app.route('/api/history.csv')
    def history():
        return Response(app.smokerpi_history.read_all(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="smokerpi-history.csv"'})

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
            invertChanged = applyConfig()
            Config(app.smokerpi_test).saveConfig(app.smokerpi_config)
            if invertChanged:
                # Move the damper to the mirrored position now; the PID would not re-send an
                # unchanged position. The setting is kept either way.
                try:
                    app.smokerpi_damper.reposition()
                except Exception as e:
                    app.logger.exception('Could not move the damper after changing damper_invert')
                    return jsonify(error='Saved, but the damper could not be moved to match: %s' % e), 500
        return json.dumps(publicConfig())

    @app.route('/api/blower', methods = ['POST'])
    def blower():
        enabled = enabledFlag()
        if enabled is None:
            return badEnabled()
        app.smokerpi_pidRunning = False
        app.smokerpi_pid.auto_mode = False
        if (enabled):
          app.smokerpi_blower.on()
        else:
          app.smokerpi_blower.off()
        return json.dumps(publicConfig())

    @app.route('/api/damper', methods = ['POST'])
    def damper():
        enabled = enabledFlag()
        if enabled is None:
            return badEnabled()
        app.smokerpi_pidRunning = False
        app.smokerpi_pid.auto_mode = False
        if (enabled):
          app.smokerpi_damper.open(100)
        else:
          app.smokerpi_damper.open(0)
        return json.dumps(publicConfig())

    @app.route('/api/pid', methods = ['POST'])
    def pid():
        enabled = enabledFlag()
        if enabled is None:
            return badEnabled()
        if (enabled):
            app.smokerpi_pidRunning = True
            app.smokerpi_pid.auto_mode = True
        else:
            app.smokerpi_pidRunning = False
            app.smokerpi_pid.auto_mode = False
            app.smokerpi_blower.off()
        return json.dumps(publicConfig())

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
        now = datetime.now()
        point = { 'i': app.smokerpi_graphIndex, 'x': now.strftime(GRAPH_TIME), 't': app.smokerpi_currentTemperature, 'b': app.smokerpi_blower.state,'d': app.smokerpi_damper.state, 's': app.smokerpi_config['set_temperature'] }
        app.smokerpi_graphData.append(point)
        while (len(app.smokerpi_graphData) > GRAPH_POINTS):
            del app.smokerpi_graphData[0]
        app.smokerpi_graphIndex = app.smokerpi_graphIndex + 1
        app.smokerpi_graphLast = graphLast
        # Never raises: a disk problem is logged and must not touch the control loop.
        app.smokerpi_history.append(point['i'], now, point['t'], point['b'], point['d'], point['s'])

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
    if not app.smokerpi_config.get('password'):
        app.logger.warning('No password set in config.json: anyone on the network can control the smoker')

    return app
