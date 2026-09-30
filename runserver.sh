#!/bin/bash

cd api
source "./venv/bin/activate"
# exec so the init script's PID file tracks python itself; otherwise
# `service smokerpiboot restart` kills only this wrapper and leaves the old
# server holding the port.
exec python runserver.py
