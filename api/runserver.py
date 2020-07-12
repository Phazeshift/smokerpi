#!/usr/bin/env python

from flask import Flask
from smokerpi import app, socketio, cleanupHardware
import os
import signal

def handler(signal, frame):
  cleanupHardware()    
  os._exit(0)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

if __name__ == '__main__':
    app.debug = False
    socketio.run(app, host='0.0.0.0')    