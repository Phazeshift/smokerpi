import json
import math
import re

# Settings the API lets a client change. Everything else in the config (pins, intervals)
# is read-only over the API: it needs a restart to take effect, so edit config.json.
EDITABLE_FIELDS = ('set_temperature', 'damper_minimum', 'damper_maximum')

# PID gains are also editable, but optional in a POST so a client that only knows the three
# settings above keeps working. Sanity limits, not tuning advice.
PID_FIELDS = {'pid_kp': 100, 'pid_ki': 10, 'pid_kd': 100}

# Limits, from the hardware code: the damper maps 0-100 onto a servo pulse width between
# damper_minimum and damper_maximum, which pigpio only accepts between 500 and 2500
# microseconds.
SERVO_MIN, SERVO_MAX = 500, 2500


def _whole_number(value):
    if isinstance(value, bool):
        raise ValueError(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r'\s*-?\d+\s*', value):
        return int(value)
    raise ValueError(value)


def _gain(value):
    if isinstance(value, bool):
        raise ValueError(value)
    try:
        number = float(value.strip() if isinstance(value, str) else value)
    except (TypeError, ValueError):
        raise ValueError(value)
    if not math.isfinite(number):
        raise ValueError(value)
    return number


def validateEditableConfig(payload):
    """Check the editable settings in a POSTed config.

    Returns (values, errors): values maps each valid field to an int, errors maps each
    invalid or missing field to a message. Numeric strings are accepted because that is
    how the web form sends them."""
    bounds = {
        'set_temperature': (1, None, 'must be a whole number above 0'),
        'damper_minimum': (SERVO_MIN, SERVO_MAX, 'must be a whole number between %d and %d' % (SERVO_MIN, SERVO_MAX)),
        'damper_maximum': (SERVO_MIN, SERVO_MAX, 'must be a whole number between %d and %d' % (SERVO_MIN, SERVO_MAX)),
    }
    values, errors = {}, {}
    for field in EDITABLE_FIELDS:
        low, high, message = bounds[field]
        if field not in payload:
            errors[field] = 'is required'
            continue
        try:
            number = _whole_number(payload[field])
        except ValueError:
            errors[field] = message
            continue
        if number < low or (high is not None and number > high):
            errors[field] = message
        else:
            values[field] = number
    for field, high in PID_FIELDS.items():
        if field not in payload:
            continue
        try:
            number = _gain(payload[field])
        except ValueError:
            number = None
        if number is None or number < 0 or number > high:
            errors[field] = 'must be a number between 0 and %g' % high
        else:
            values[field] = number
    if 'damper_invert' in payload:
        if isinstance(payload['damper_invert'], bool):
            values['damper_invert'] = payload['damper_invert']
        else:
            errors['damper_invert'] = 'must be true or false'
    if 'damper_minimum' in values and 'damper_maximum' in values             and values['damper_minimum'] >= values['damper_maximum']:
        errors['damper_minimum'] = 'must be less than damper_maximum'
        del values['damper_minimum']
    return values, errors


class Config:    
    def __init__(self, test):
        self.test = test

    def applyTestConfig(self, data):
        if (self.test):     
            testspeed = 10
            data['worker_interval'] = data['worker_interval'] / testspeed
            data['graph_interval'] = data['graph_interval'] / testspeed

    def saveConfig(self, data):
        # Save a copy: the caller passes the live config, which must not change as a
        # side effect of saving.
        data = dict(data)
        # The intervals are not editable over the API, and in test mode the live values
        # are scaled down. Keep whatever is already persisted (falling back to the
        # defaults) so a save never rewrites them, hand-edited values included.
        persisted = self.readConfigFile()
        defaults = self.defaultConfig()
        for key in ('worker_interval', 'graph_interval'):
            data[key] = persisted.get(key, defaults[key])
        self.writeConfigFile(data)

    def readConfigFile(self):
        try:
            with open('config.json') as configfile:
                return json.load(configfile)
        except (FileNotFoundError):
            return {}

    def loadConfig(self):
        data = self.readConfigFile()
        defaultdata = self.defaultConfig()
        defaultdata.update(data)
        if (defaultdata != data):
            self.writeConfigFile(defaultdata)
        self.applyTestConfig(defaultdata)  
        return defaultdata

    def writeConfigFile(self, data):
        with open('config.json', 'w') as configfile:
            json.dump(data, configfile)

    def defaultConfig(self):
        return  { 'cs_pin': 20, 'clock_pin': 21, 'data_pin': 16, 'blower_pin1': 26, 'blower_pin2': 19, 'damper_pin': 13, 'set_temperature': 105, 'graph_interval': 10, 'worker_interval': 10, 'sensor_timeout': 60, 'password': '', 'pid_kp': 1, 'pid_ki': 0.1, 'pid_kd': 0.05, 'damper_invert': False, 'history_max_mb': 5, 'damper_minimum': 500, 'damper_maximum': 2500 }        