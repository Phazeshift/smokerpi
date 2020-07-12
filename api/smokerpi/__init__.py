from flask import (Flask)
from flask_socketio import SocketIO, emit
import logging
from logging.handlers import RotatingFileHandler
from flask import json
from werkzeug.exceptions import InternalServerError
from .hardware.blower import Blower
from .hardware.max31855 import MAX31855, TestMAX31855, MAX31855Error
from simple_pid import PID
from datetime import datetime
import array
import platform
import time
import os
import json

app = Flask(__name__, static_folder='../../build', static_url_path='/')

logging.basicConfig(filename='./log/app.log',level=logging.DEBUG)

app.logger.info("### NEW STARTUP Version 0.1")
app.config['SECRET_KEY'] = 'smokerpi-secret!'
socketio = SocketIO()
socketio.init_app(app, cors_allowed_origins="*")

app.smokerpi_test = False
app.smokerpi_currentTemperature = 0
app.smokerpi_currentState = {}
app.smokerpi_pidRunning = False
app.smokerpi_workerInterval = 0.1
app.smokerpi_graphLast = 0
app.smokerpi_pushLast = 0
app.smokerpi_pid = PID(1, 0.1, 0.05, setpoint=100)
app.smokerpi_pid.sample_time = 0.1
app.smokerpi_pid.output_limits = (0, 100)

app.smokerpi_graphData = []
app.smokerpi_graphIndex = 0
app.smokerpi_running = True
app.smokerpi_config = { }

if (platform.system() == 'Windows'):
    app.smokerpi_test = True

def configure():
    app.smokerpi_max31855 = MAX31855(app.smokerpi_config['cs_pin'], app.smokerpi_config['clock_pin'], app.smokerpi_config['data_pin'])
    app.smokerpi_blower = Blower(app.smokerpi_config['blower_pin1'], app.smokerpi_config['blower_pin2'])
    app.smokerpi_pid.setpoint = app.smokerpi_config['set_temperature']

def saveConfig():
    with open('config.json', 'w') as configfile:
        json.dump(app.smokerpi_config, configfile)

def loadConfig():
    try: 
        with open('config.json') as configfile:
            app.smokerpi_config = json.load(configfile)
    except (FileNotFoundError):
        app.smokerpi_config = { 'cs_pin': 20, 'clock_pin': 21, 'data_pin': 16, 'blower_pin1': 19, 'blower_pin2': 26, 'set_temperature': 220, 'graph_interval': 10, 'push_interval': 10, 'blower_minimum': 40 }
        saveConfig()

def setup():
    loadConfig()
    configure()
    if (app.smokerpi_test):     
        app.smokerpi_max31855 = TestMAX31855(app.smokerpi_blower)   
        app.smokerpi_workerInterval = 0.1    
    
@app.route('/')
def index():
    return app.send_static_file('index.html')

@socketio.on('connect')
def ws_connect():
    app.logger.info("Connect")    
    pushState(True)

@socketio.on('message')
def message(data):    
    socketio.emit('message', data)    
    
@socketio.on('getState')
def getState(data):    
    pushState(True)
    
def pushState(force = False):   
    pushTime = time.time()
    if (force == False and (pushTime - app.smokerpi_pushLast) < app.smokerpi_config['push_interval']):
        return 0      
    app.smokerpi_pushLast = pushTime  
    state = { 'temperature': app.smokerpi_currentTemperature, 'targetTemperature': app.smokerpi_config['set_temperature'], 'blower': app.smokerpi_blower.state, 'pid': app.smokerpi_pidRunning }
    #if (state != app.smokerpi_currentState):
    app.smokerpi_currentState = state
    socketio.send(app.smokerpi_currentState)        

@socketio.on('getConfig')
def getConfig(data):        
    socketio.send({ 'config': app.smokerpi_config })    

@socketio.on('updateConfig')
def updateConfig(data):        
    print(data)
    app.smokerpi_config['set_temperature'] = data['set_temperature']
    app.smokerpi_config['blower_minimum'] = data['blower_minimum']
    app.smokerpi_pid.setpoint = app.smokerpi_config['set_temperature']
    pushState(True)

@socketio.on('getAllGraph')
def getAllGraph(data):              
    socketio.send({ 'graphData': app.smokerpi_graphData })        

@socketio.on('toggleBlower')
def toggleBlower(data):
    app.smokerpi_pidRunning = False
    app.smokerpi_blower.toggleState()
    pushState(True)    

@socketio.on('toggleAutomatic')
def switchAutomatic(data):    
    if(app.smokerpi_pidRunning == True):
        app.smokerpi_pidRunning = False 
        app.smokerpi_pid.auto_mode = False
        app.smokerpi_blower.off()        
    else:
        app.smokerpi_pidRunning = True
        app.smokerpi_pid.auto_mode = True        
    pushState(True)

def monitorTemp():    
    try:
        app.smokerpi_currentTemperature = app.smokerpi_max31855.get()
    except (MAX31855Error):
        app.smokerpi_currentTemperature = -1        
        
def pid():     
    output = app.smokerpi_pid(app.smokerpi_currentTemperature)  
    if (output > 0):
        min = app.smokerpi_config['blower_minimum']
        output = (output * ((100 - min) / 100)) + min
    output = round(output, 2)  
    if (app.smokerpi_pidRunning):        
        app.smokerpi_blower.pwm(output)                   
    
def graphData():
    graphLast = time.time()
    if (graphLast - app.smokerpi_graphLast < app.smokerpi_config['graph_interval']):
        return 0    
    app.smokerpi_graphData.append({ 'i': app.smokerpi_graphIndex, 'x': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 't': app.smokerpi_currentTemperature, 'b': app.smokerpi_blower.state, 's': app.smokerpi_config['set_temperature'] })
    while (len(app.smokerpi_graphData) > 2000):
        del app.smokerpi_graphData[0]
    app.smokerpi_graphIndex = app.smokerpi_graphIndex + 1  
    app.smokerpi_graphLast = graphLast

def worker():
    while app.smokerpi_running:        
        monitorTemp()
        pid()
        pushState(False)
        graphData()
        socketio.sleep(app.smokerpi_workerInterval)         
    print("Worker complete")     

@app.errorhandler(InternalServerError)
def handle_500(e):    
    app.logger.error(e.message)    

def cleanupHardware():
    app.smokerpi_running = False
    app.logger.info('Cleaning up')
    app.smokerpi_blower.cleanup()    
    app.smokerpi_max31855.cleanup() 

setup()
socketio.start_background_task(worker)
