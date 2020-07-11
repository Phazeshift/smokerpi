from flask import (Flask)
from flask_socketio import SocketIO, emit
import logging
import atexit
import signal
from logging.handlers import RotatingFileHandler
from flask import json
from werkzeug.exceptions import InternalServerError
from .hardware.blower import Blower
from .hardware.max31855 import MAX31855, TestMAX31855, MAX31855Error
from simple_pid import PID
from datetime import datetime
import array
import platform

app = Flask(__name__, static_folder='../../build', static_url_path='/')

logging.basicConfig(filename='./log/app.log',level=logging.DEBUG)

app.logger.info("### NEW STARTUP Version 0.1")
app.config['SECRET_KEY'] = 'smokerpi-secret!'
socketio = SocketIO()
socketio.init_app(app, cors_allowed_origins="*")

app.smokerpi_test = False
app.smokerpi_setTemperature = 220
app.smokerpi_currentTemperature = 0
app.smokerpi_currentBlowerState = 0
app.smokerpi_currentState = {}
app.smokerpi_pidRunning = False
app.smokerpi_pidInterval = 0.1
app.smokerpi_tempInterval = 1
app.smokerpi_pid = PID(1, 0.1, 0.05, setpoint=app.smokerpi_setTemperature)
app.smokerpi_pid.sample_time = 0.1
app.smokerpi_pid.output_limits = (0, 100)
app.smokerpi_blower = Blower(19, 26)
app.smokerpi_graphData = []
app.smokerpi_graphIndex = 0
app.smokerpi_running = True

if (platform.system() == 'Windows'):
    app.smokerpi_test = True

if (app.smokerpi_test):
    app.smokerpi_max31855 = TestMAX31855(app.smokerpi_blower)
else:
    app.smokerpi_max31855 = MAX31855(20, 21, 16)

   
@app.route('/')
def index():
    return app.send_static_file('index.html')

@socketio.on('connect')
def ws_connect():
    app.logger.info("Connect")
    app.smokerpi_currentState = {}
    pushState()

@socketio.on('message')
def message(data):    
    socketio.emit('message', data)    
    
@socketio.on('getState')
def getState(data):    
    pushState()
    
def pushState():    
    state = { 'temperature': app.smokerpi_currentTemperature, 'targetTemperature': app.smokerpi_setTemperature, 'blower': app.smokerpi_currentBlowerState, 'pid': app.smokerpi_pidRunning }
    if (state != app.smokerpi_currentState):
        app.smokerpi_currentState = state
        socketio.send(app.smokerpi_currentState)

@socketio.on('getAllGraph')
def getAllGraph(data):    
    pushAllGraph()

def pushAllGraph():    
    app.logger.info(app.smokerpi_graphData)
    socketio.send({ 'graphData': app.smokerpi_graphData })        

@socketio.on('toggleBlower')
def toggleBlower(data):
    app.smokerpi_pidRunning = False
    app.smokerpi_blower.toggleState()
    pushState()

@socketio.on('toggleAutomatic')
def switchAutomatic(data):    
    if(app.smokerpi_pidRunning == True):
        app.smokerpi_pidRunning = False        
    else:
        app.smokerpi_pidRunning = True
        socketio.start_background_task(pid)
    pushState()

def monitorTemp():
    while app.smokerpi_running:
        try:
            app.smokerpi_currentTemperature = app.smokerpi_max31855.get()
        except (MAX31855Error):
            app.smokerpi_currentTemperature = -1
        app.smokerpi_currentBlowerState = app.smokerpi_blower.state
        app.smokerpi_graphData.append({ 'i': app.smokerpi_graphIndex, 'x': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 't': app.smokerpi_currentTemperature, 'b': app.smokerpi_blower.state, 's': app.smokerpi_setTemperature })
        while (len(app.smokerpi_graphData) > 2000):
            del app.smokerpi_graphData[0]
        app.smokerpi_graphIndex = app.smokerpi_graphIndex + 1
        pushState()
        socketio.sleep(app.smokerpi_tempInterval)
        
def pid():     
    while app.smokerpi_pidRunning:
        output = round(app.smokerpi_pid(app.smokerpi_currentTemperature), 2)
        app.smokerpi_blower.pwm(output)
        socketio.sleep(app.smokerpi_pidInterval)        
    app.smokerpi_blower.off()        
    pushState()

@app.errorhandler(InternalServerError)
def handle_500(e):
    original = getattr(e, "original_exception", None)
    app.logger.error(e.message)
    raise

def cleanupHardware():
    app.smokerpi_running = False
    app.logger.info('Cleaning up')
    app.smokerpi_blower.cleanup()    
    app.smokerpi_max31855.cleanup()   

#signal.signal(signal.SIGINT, cleanupHardware)
atexit.register(cleanupHardware)
socketio.start_background_task(monitorTemp)
