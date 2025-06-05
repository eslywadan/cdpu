# from flask import Flask
# import werkzeug 
# import tools.request_handler as req
from dpam.blueprint_create import create_app
from flask_cors import CORS

from dpam.tools.get_env import env
import os

print(f"current env is set as {env}")

if "PYTHONPATH" not in os.environ.keys(): cfg_path = os.path.join(os.getcwd(), "instance", "flask.cfg")
else:  cfg_path = os.path.join(os.environ["PYTHONPATH"], "instance", "flask.cfg")

app=create_app(cfg_path)
CORS(app)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8060)