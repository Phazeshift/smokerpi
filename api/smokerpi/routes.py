import os

from flask import Response, json, jsonify, request
from werkzeug.exceptions import InternalServerError, NotFound

from .config import Config, applyConfig, validateEditableConfig


def registerRoutes(app, worker):
    def publicConfig():
        return {key: value for key, value in app.smokerpi_config.items() if key != 'password'}

    def enabledFlag():
        """The `enabled` boolean of a control request, or None if the body is not valid."""
        payload = request.get_json(silent=True)
        if isinstance(payload, dict) and isinstance(payload.get('enabled'), bool):
            return payload['enabled']
        return None

    def badEnabled():
        return jsonify(error='Expected a JSON object with a true or false "enabled"'), 400

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.errorhandler(NotFound)
    def client_side_route(e):
        # The React app does its own routing (e.g. /config), so a page refresh or a
        # deep link asks the server for a path it has no file for. Serve the app shell
        # for those. API paths and requests for files (anything with an extension)
        # stay real 404s, as does everything when there is no build to serve.
        last_segment = request.path.rsplit('/', 1)[-1]
        has_build = os.path.isfile(os.path.join(app.static_folder, 'index.html'))
        if (request.method in ('GET', 'HEAD') and has_build
                and not request.path.startswith('/api/') and '.' not in last_segment):
            return app.send_static_file('index.html')
        return e

    @app.route('/api/graph')
    def graph():
        try:
            fromIndex = int(request.args.get("from", "0"))
        except ValueError:
            return jsonify(error='"from" must be a whole number'), 400
        return json.dumps([point for point in app.smokerpi_graphData if point['i'] >= fromIndex])

    @app.route('/api/history.csv')
    def history():
        return Response(app.smokerpi_history.read_all(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="smokerpi-history.csv"'})

    @app.route('/api/state')
    def state():
        app.smokerpi_currentState = { 'temperature': app.smokerpi_currentTemperature, 'targetTemperature': app.smokerpi_config['set_temperature'], 'blower': app.smokerpi_blower.state, 'pid': app.smokerpi_pidRunning, 'damper': app.smokerpi_damper.state, 'workerError': worker.error() }
        return json.dumps(app.smokerpi_currentState)

    @app.route('/api/config', methods = ['GET', 'POST'])
    def config():
        if request.method == "POST":
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                return jsonify(error='Expected a JSON object'), 400
            values, errors = validateEditableConfig(payload)
            if errors:
                message = 'Invalid configuration: ' + '; '.join('%s %s' % (k, v) for k, v in errors.items())
                return jsonify(error=message, errors=errors), 400
            app.smokerpi_config.update(values)
            invertChanged = applyConfig(app)
            Config(app.smokerpi_test).saveConfig(app.smokerpi_config)
            if invertChanged:
                # Move the damper to the mirrored position now; the PID would not re-send an
                # unchanged position. The setting is kept either way.
                try:
                    app.smokerpi_damper.reposition()
                except Exception as e:
                    app.logger.exception('Could not move the damper after changing damper_invert')
                    return jsonify(error='Saved, but the damper could not be moved to match: %s' % e), 500
        return json.dumps(publicConfig())

    def control(action):
        """Run a control request: validate `enabled`, then call action(enabled). Every manual
        control takes the PID out of the loop."""
        enabled = enabledFlag()
        if enabled is None:
            return badEnabled()
        action(enabled)
        return json.dumps(publicConfig())

    def stopPid():
        app.smokerpi_pidRunning = False
        app.smokerpi_pid.auto_mode = False

    @app.route('/api/blower', methods = ['POST'])
    def blower():
        def act(enabled):
            stopPid()
            if enabled:
                app.smokerpi_blower.on()
            else:
                app.smokerpi_blower.off()
        return control(act)

    @app.route('/api/damper', methods = ['POST'])
    def damper():
        def act(enabled):
            stopPid()
            app.smokerpi_damper.open(100 if enabled else 0)
        return control(act)

    @app.route('/api/pid', methods = ['POST'])
    def pid():
        def act(enabled):
            if enabled:
                app.smokerpi_pidRunning = True
                app.smokerpi_pid.auto_mode = True
            else:
                stopPid()
                app.smokerpi_blower.off()
        return control(act)

    @app.errorhandler(InternalServerError)
    def handle_500(e):
        app.logger.error('Unhandled error: %s', e.original_exception or e, exc_info=e.original_exception)
        return e
