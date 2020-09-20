from flask import (Flask, request)
import logging
from logging.handlers import RotatingFileHandler
from flask import json
from werkzeug.exceptions import InternalServerError
from .hardware.blower import Blower
from .hardware.damper2 import Damper, TestDamper
from .hardware.pitcontroller import PitController
from .hardware.max31855 import MAX31855, TestMAX31855, MAX31855Error
from .config import Config
from simple_pid import PID
from datetime import datetime
import array
import platform
import time
import os
import json
import threading

app = Flask(__name__, static_folder='../../build', static_url_path='/')

logging.basicConfig(filename='./log/app.log',level=logging.DEBUG)

app.logger.info("### NEW STARTUP Version 0.1")
app.config['SECRET_KEY'] = 'smokerpi-secret!'

app.smokerpi_test = False
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
app.smokerpi_config = { }

if (platform.system() == 'Windows'):
    app.smokerpi_test = True

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
    app.smokerpi_config = Config(app.smokerpi_test).loadConfig()
    app.smokerpi_workerInterval = app.smokerpi_config['worker_interval']
    configure()      
    app.worker = threading.Thread(target=worker)
    app.worker.daemon = True
    app.worker.start()
    
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/graph')
def graph():
    fromIndex = int(request.args.get("from", "0"))
    graphData = []
    for val in app.smokerpi_graphData:
        if (val['i'] >= fromIndex):
            graphData.append(val)     
    return json.dumps(graphData)

@app.route('/api/state')
def state():    
    app.smokerpi_currentState = { 'temperature': app.smokerpi_currentTemperature, 'targetTemperature': app.smokerpi_config['set_temperature'], 'blower': app.smokerpi_blower.state, 'pid': app.smokerpi_pidRunning, 'damper': app.smokerpi_damper.state }
    return json.dumps(app.smokerpi_currentState)

@app.route('/api/config', methods = ['GET', 'POST'])
def config(): 
    if request.method == "POST":
        print(request.json)
        app.smokerpi_config['set_temperature'] = int(request.json['set_temperature'])
        app.smokerpi_config['blower_minimum'] = int(request.json['blower_minimum'])
        app.smokerpi_config['damper_minimum'] = int(request.json['damper_minimum'])
        app.smokerpi_config['damper_maximum'] = int(request.json['damper_maximum'])
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
    try:
        app.smokerpi_currentTemperature = app.smokerpi_max31855.get()
    except (MAX31855Error):
        pass
        
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

def worker():
    while app.smokerpi_running:        
        monitorTemp()
        updatePid()        
        graphData()
        time.sleep(app.smokerpi_workerInterval)                   
    print("Worker complete")     

@app.errorhandler(InternalServerError)
def handle_500(e):    
    app.logger.error(e.message)    

def cleanupHardware():
    print("Cleanup")  
    app.logger.info('Cleaning up')
    app.smokerpi_running = False    
    app.smokerpi_blower.cleanup()    
    app.smokerpi_max31855.cleanup() 
    app.smokerpi_damper.cleanup()

setup()

