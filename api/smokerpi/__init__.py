from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
from .config import Config
from .display import Display, openDevice
from .auth import registerAuth
from .routes import registerRoutes
from .smoker import Smoker
from .worker import Worker
import platform
import os


def configureLogging(logDir):
    """Log to <logDir>/app.log, capped at 4 x 1 MB so it cannot fill the Pi's SD card.

    Replaces any handler a previous call added, so creating the app more than once (as the
    tests do) does not log every line twice."""
    root = logging.getLogger()
    for old in [h for h in root.handlers if getattr(h, 'smokerpi', False)]:
        root.removeHandler(old)
        old.close()
    handler = RotatingFileHandler(os.path.join(logDir, 'app.log'), maxBytes=1024 * 1024, backupCount=3)
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
    """Build the app. All live state is on app.smoker (a Smoker: settings, hardware, PID,
    graph); app.worker is the control loop. test_config may hold 'config' (a config dict to use
    instead of reading config.json) and 'start_worker' (False to leave the loop stopped)."""
    app = Flask(__name__, static_folder='../../build', static_url_path='/')

    # config.json, log/ and data/ all live here: SMOKERPI_HOME, or the directory the app was
    # started from (api/ on the Pi, where runserver.sh runs it). Made absolute once, so a later
    # change of working directory cannot split them up.
    home = os.path.abspath(os.environ.get('SMOKERPI_HOME') or os.getcwd())
    logDir = os.path.join(home, 'log')
    os.makedirs(logDir, exist_ok=True)
    configureLogging(logDir)

    app.logger.info("### NEW STARTUP Version %s", readVersion())

    test = platform.system() == 'Windows' or os.environ.get('SMOKERPI_TEST') == '1'
    configFile = Config(test, os.path.join(home, 'config.json'))
    if test_config is not None and 'config' in test_config:
        config = test_config['config']
    else:
        config = configFile.loadConfig()

    app.smoker = Smoker(config, configFile, home, test)
    app.worker = Worker(app.smoker)
    # Off the Pi (emulated hardware) there is no screen to open.
    app.display = Display(app.smoker, app.worker, None if test else openDevice(config))
    registerAuth(app, app.smoker)
    registerRoutes(app, app.smoker, app.worker)

    if test_config is None or test_config.get('start_worker', True):
        app.worker.start()
        app.display.start()
    if not config.get('password'):
        app.logger.warning('No password set in config.json: anyone on the network can control the smoker')

    return app
