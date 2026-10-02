from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
from .hardware.blower import Blower
from .hardware.damper2 import Damper, emulatedDamper
from .hardware.pitcontroller import PitController
from .hardware.max31855 import MAX31855, TestMAX31855
from .config import Config, applyConfig
from .pid import AntiWindupPID
from .history import History, GRAPH_POINTS
from .auth import registerAuth
from .routes import registerRoutes
from .worker import Worker
import platform
import threading
import time
import os


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


def readVersion(path=os.path.join(os.path.dirname(__file__), '..', '..', 'VERSION')):
    """The release the Pi is running: update.sh writes its tag to VERSION in the install
    directory, next to api/. A checkout has no such file."""
    try:
        with open(path) as versionfile:
            return versionfile.read().strip() or 'unknown'
    except OSError:
        return 'unknown'


def create_app(test_config=None):
    app = Flask(__name__, static_folder='../../build', static_url_path='/')

    os.makedirs('./log', exist_ok=True)
    configureLogging()

    app.logger.info("### NEW STARTUP Version %s", readVersion())

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
    # Held while the hardware or the control mode changes: by each worker pass and by the
    # control and config routes, which run on their own threads. A route waits at most
    # smokerpi_lockTimeout seconds for it (a pass holds it for about a second when the damper
    # moves) and then answers 503 rather than hang behind a stuck loop.
    app.smokerpi_lock = threading.Lock()
    app.smokerpi_lockTimeout = 5
    app.smokerpi_clock = time.monotonic
    app.smokerpi_lastReading = app.smokerpi_clock()
    app.smokerpi_lastPass = app.smokerpi_clock()
    app.smokerpi_stepErrors = {}
    app.smokerpi_config = { }

    def configure():
        config = app.smokerpi_config
        makeDamper = emulatedDamper if app.smokerpi_test else Damper
        app.smokerpi_damper = makeDamper(config['damper_pin'], config['damper_minimum'], config['damper_maximum'], bool(config.get('damper_invert', False)))
        app.smokerpi_blower = Blower(config['blower_pin1'], config['blower_pin2'])
        applyConfig(app)
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
            app.worker = worker.start()
            app.watchdog = worker.startWatchdog()

    def cleanupHardware():
        print("Cleanup")
        app.logger.info('Cleaning up')
        # Wait for a step in progress so it cannot move the hardware after it is released, but
        # not for ever: a stuck loop must not stop the hardware being cleaned up.
        locked = app.smokerpi_lock.acquire(timeout=app.smokerpi_lockTimeout)
        try:
            app.smokerpi_running = False
            app.smokerpi_blower.cleanup()
            app.smokerpi_max31855.cleanup()
            app.smokerpi_damper.cleanup()
        finally:
            if locked:
                app.smokerpi_lock.release()

    app.cleanupHardware = cleanupHardware

    worker = Worker(app)
    app.smokerpi_workerStep = worker.step
    app.smokerpi_watchdogCheck = worker.checkWatchdog
    registerAuth(app)
    registerRoutes(app, worker)

    setup()
    if not app.smokerpi_config.get('password'):
        app.logger.warning('No password set in config.json: anyone on the network can control the smoker')

    return app
