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
    app.debug = False
    app.run(host='0.0.0.0')  
