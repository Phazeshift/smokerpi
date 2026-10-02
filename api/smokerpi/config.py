import json
import math
import re
from collections import namedtuple

# Limits, from the hardware code: the damper maps 0-100 onto a servo pulse width between
# damper_minimum and damper_maximum, which pigpio only accepts between 500 and 2500
# microseconds.
SERVO_MIN, SERVO_MAX = 500, 2500


class Field(namedtuple('Field', 'name default kind low high')):
    """One setting in config.json: its default, and how a POST /api/config may change it.

    kind is 'whole' (a required whole number between low and high, high None for no upper
    limit), 'gain' (an optional number from 0 to high, so a client that only knows the
    'whole' settings keeps working), 'bool' (optional), or None for settings the API does
    not accept because they need a restart (pins, intervals): edit config.json for those."""
    __slots__ = ()

    def __new__(cls, name, default, kind=None, low=None, high=None):
        return super().__new__(cls, name, default, kind, low, high)


FIELDS = (
    Field('cs_pin', 20),
    Field('clock_pin', 21),
    Field('data_pin', 16),
    Field('blower_pin1', 26),
    Field('blower_pin2', 19),
    Field('damper_pin', 13),
    Field('set_temperature', 105, 'whole', 1, None),
    Field('graph_interval', 10),
    Field('worker_interval', 10),
    Field('sensor_timeout', 60),
    Field('password', ''),
    # PID gain limits are sanity limits, not tuning advice.
    Field('pid_kp', 1, 'gain', 0, 100),
    Field('pid_ki', 0.1, 'gain', 0, 10),
    Field('pid_kd', 0.05, 'gain', 0, 100),
    Field('damper_invert', False, 'bool'),
    Field('history_max_mb', 5),
    Field('damper_minimum', 500, 'whole', SERVO_MIN, SERVO_MAX),
    Field('damper_maximum', 2500, 'whole', SERVO_MIN, SERVO_MAX),
)


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


def _whole_number_message(field):
    if field.high is None:
        return 'must be a whole number above %d' % (field.low - 1)
    return 'must be a whole number between %d and %d' % (field.low, field.high)


def validateEditableConfig(payload):
    """Check the editable settings in a POSTed config.

    Returns (values, errors): values maps each valid field to its value, errors maps each
    invalid or missing field to a message. Numeric strings are accepted because that is
    how the web form sends them."""
    values, errors = {}, {}
    for field in FIELDS:
        if field.kind is None:
            continue
        name = field.name
        if name not in payload:
            if field.kind == 'whole':
                errors[name] = 'is required'
            continue
        value = payload[name]
        if field.kind == 'whole':
            try:
                number = _whole_number(value)
            except ValueError:
                number = None
            if number is None or number < field.low or (field.high is not None and number > field.high):
                errors[name] = _whole_number_message(field)
            else:
                values[name] = number
        elif field.kind == 'gain':
            try:
                number = _gain(value)
            except ValueError:
                number = None
            if number is None or number < field.low or number > field.high:
                errors[name] = 'must be a number between %g and %g' % (field.low, field.high)
            else:
                values[name] = number
        elif field.kind == 'bool':
            if isinstance(value, bool):
                values[name] = value
            else:
                errors[name] = 'must be true or false'
    if 'damper_minimum' in values and 'damper_maximum' in values and values['damper_minimum'] >= values['damper_maximum']:
        errors['damper_minimum'] = 'must be less than damper_maximum'
        del values['damper_minimum']
    return values, errors


def applyConfig(app):
    """Push the settings in app.smokerpi_config onto the PID and the damper. Used at startup
    and after a POST /api/config, so the two cannot drift apart. Returns True if the damper
    direction changed."""
    config = app.smokerpi_config
    app.smokerpi_pid.setpoint = config['set_temperature']
    app.smokerpi_pid.tunings = (float(config['pid_kp']), float(config['pid_ki']), float(config['pid_kd']))
    damper = app.smokerpi_damper
    damper.min = config['damper_minimum']
    damper.max = config['damper_maximum']
    invert = bool(config.get('damper_invert', False))
    invertChanged = damper.invert != invert
    damper.invert = invert
    return invertChanged


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
        return {field.name: field.default for field in FIELDS}
