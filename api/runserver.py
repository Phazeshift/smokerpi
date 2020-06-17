#!/usr/bin/env python

from flask import Flask
from smokerpi import app, socketio

if __name__ == '__main__':
    app.debug = False
    socketio.run(app, host='0.0.0.0')