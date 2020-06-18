from flask import (Flask)
from flask_socketio import SocketIO, emit
import logging
import atexit
from logging.handlers import RotatingFileHandler
from flask import json
from werkzeug.exceptions import InternalServerError
from .hardware.blower import Blower
from .hardware.max31855 import MAX31855

app = Flask(__name__, static_folder='../../build', static_url_path='/')

logging.basicConfig(filename='./log/app.log',level=logging.DEBUG)

app.logger.info("### NEW STARTUP Version 0.1")
app.config['SECRET_KEY'] = 'smokerpi-secret!'
socketio = SocketIO()
socketio.init_app(app, cors_allowed_origins="*")

app.smokerpi_temperature = 220
app.smokerpi_blower = Blower()
app.smokerpi_max31855 = MAX31855(20, 21, 16)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@socketio.on('connect')
def ws_connect():
    app.logger.info("Connect")

@socketio.on('message')
def message(data):    
    socketio.emit('message', data)    
    
@socketio.on('getState')
def getState(data):    
    pushState()
    
@socketio.on('toggleBlower')
def toggleBlower(data):
    app.smokerpi_blower.toggleState()
    pushState()

def pushState():
    if (app.smokerpi_blower.state == True):
        value = 100
    else:
        value = 0
    socketio.send({ 'temperature': app.smokerpi_max31855.get(), 'blower': value })

@app.errorhandler(InternalServerError)
def handle_500(e):
    original = getattr(e, "original_exception", None)
    app.logger.error(e.message)
    raise

def cleanupHardware():
    app.logger.info('Cleaning up')
    app.smokerpi_blower.cleanup()    
    app.smokerpi_max31855.cleanup()   

#Register the cleanup function to be called on exit
atexit.register(cleanupHardware)