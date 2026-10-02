import base64
import binascii
import hmac

from flask import Response, request


def passwordSupplied():
    """The password from an HTTP Basic Authorization header, or None. Any username."""
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    if scheme.lower() != 'basic':
        return None
    try:
        _, colon, password = base64.b64decode(token.strip(), validate=True).decode('utf-8').partition(':')
    except (binascii.Error, UnicodeDecodeError):
        return None
    return password if colon else None


def registerAuth(app, smoker):
    @app.before_request
    def requirePassword():
        # Protects the page and the API alike. With no password configured everything is open.
        expected = smoker.config.get('password', '')
        if not expected:
            return None
        supplied = passwordSupplied()
        if supplied is not None and hmac.compare_digest(supplied.encode('utf-8'), expected.encode('utf-8')):
            return None
        return Response('Password required', 401, {'WWW-Authenticate': 'Basic realm="SmokerPi", charset="UTF-8"'})
