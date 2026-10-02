import os

from flask import Response, json, jsonify, request
from werkzeug.exceptions import InternalServerError, NotFound

from .config import describeFields, validateEditableConfig
from .smoker import ControlBusy, DamperNotMoved


def registerRoutes(app, smoker, worker):
    def enabledFlag():
        """The `enabled` boolean of a control request, or None if the body is not valid."""
        payload = request.get_json(silent=True)
        if isinstance(payload, dict) and isinstance(payload.get('enabled'), bool):
            return payload['enabled']
        return None

    def badEnabled():
        return jsonify(error='Expected a JSON object with a true or false "enabled"'), 400

    def busy(e):
        app.logger.error('Control request %s gave up waiting for the control loop', request.path)
        return jsonify(error=str(e)), 503

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
        return json.dumps(smoker.graphSince(fromIndex))

    @app.route('/api/history.csv')
    def history():
        return Response(smoker.history.read_all(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="smokerpi-history.csv"'})

    @app.route('/api/state')
    def state():
        return json.dumps(dict(smoker.snapshot(), workerError=worker.error()))

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

            try:
                smoker.updateConfig(values)
            except ControlBusy as e:
                return busy(e)
            except DamperNotMoved as e:
                return jsonify(error=str(e)), 500
        return json.dumps(dict(smoker.publicConfig(), fields=describeFields(smoker.config)))

    def control(action):
        """Run a control request: validate `enabled`, then call action(enabled)."""
        enabled = enabledFlag()
        if enabled is None:
            return badEnabled()
        try:
            action(enabled)
        except ControlBusy as e:
            return busy(e)
        return json.dumps(smoker.publicConfig())

    @app.route('/api/blower', methods = ['POST'])
    def blower():
        return control(smoker.setBlower)

    @app.route('/api/damper', methods = ['POST'])
    def damper():
        return control(smoker.setDamper)

    @app.route('/api/pid', methods = ['POST'])
    def pid():
        return control(smoker.setAutomatic)

    @app.errorhandler(InternalServerError)
    def handle_500(e):
        app.logger.error('Unhandled error: %s', e.original_exception or e, exc_info=e.original_exception)
        return e
