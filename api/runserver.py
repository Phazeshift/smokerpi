#!/usr/bin/env python

from flask import Flask
from smokerpi import app, cleanupHardware
import os
import signal

def handler(signal, frame):
  print('CTRL-C pressed!')
  cleanupHardware()
  os._exit(0)

signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

if __name__ == '__main__':
    # Pass debug and load_dotenv explicitly. Flask 2.0's app.run() otherwise loads .flaskenv
    # and, if it sets FLASK_ENV, re-enables debug mode over `app.debug = False`, which exposes
    # the interactive Werkzeug debugger (/console) and the reloader on the network.
    app.debug = False
    app.run(host='0.0.0.0', debug=False, load_dotenv=False)
