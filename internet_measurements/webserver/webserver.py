#!/usr/bin/python3

import sys
import time
import flask
import argparse

usage_string = """
===============================================================
 Wecome to the spinbit test webserver!

 Available url's:
     /file/<path>   : serves a anything in the `file' directory
     /zero/<int>  : serves <int> MiB worth of ASCII zeros

     every URL accepts a delay parameter, which specifies the
     delay before serving the request resource in seconds.

     e.g. http://localhost:5000/file/cats/1.jpg?delay=1.5
     will serve the cat picture after a 1.5 second delay.
===============================================================
"""

parser = argparse.ArgumentParser()
parser.add_argument('-p',
                    dest = 'port',
                    type = int,
                    default = 5000,
                    help = "port to run the webserver on")
args = parser.parse_args()


app = flask.Flask(__name__)

def do_delay():
    try:
        time.sleep(float(flask.request.args['delay']))
    except KeyError:
        pass

@app.route('/')
def return_ussage():
    do_delay()
    return "<html><pre>" + usage_string + "</pre></html>"

@app.route('/file/<path:path>')
def serve_file(path):
    do_delay()
    return flask.send_from_directory('file', path)

@app.route('/zero/<int:size>')
def serve_zeros(size):
    def generate(size):
        for i in range(size):
            yield '0'*1024*1024

    do_delay()
    return flask.Response(generate(size))

if __name__ == "__main__":

    print(usage_string)
    app.run(host='0.0.0.0', port=args.port)

