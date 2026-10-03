#!/usr/bin/env python

from smokerpi import create_app
import os
import signal


def main():
    app = create_app()

    def handler(signal, frame):
        print('CTRL-C pressed!')
        app.smoker.cleanup()
        app.display.cleanup()
        os._exit(0)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    # Pass debug and load_dotenv explicitly. Flask 2.0's app.run() otherwise loads .flaskenv
    # and, if it sets FLASK_ENV, re-enables debug mode over `app.debug = False`, which exposes
    # the interactive Werkzeug debugger (/console) and the reloader on the network.
    app.debug = False
    app.run(host='0.0.0.0', debug=False, load_dotenv=False)


if __name__ == '__main__':
    main()
