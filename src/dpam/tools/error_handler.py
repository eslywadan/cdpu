from flask import jsonify, Response, json
from dpam.tools.logger import Logger

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload


    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


class JSNError(Response):
    def __init__(self, payload, status_code=500):
        Response.__init__(self, json.dumps(payload))
        self.status_code = status_code
        self.mimetype = 'application/json'

        Logger.log(f'End request: {status_code}')
