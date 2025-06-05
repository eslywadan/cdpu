from flask import Flask
from flask import Blueprint
import os


acct_bp = Blueprint('acct_bp', __name__)
acctapi_bp = Blueprint('acctapi_bp', __name__)
acctclog_bp = Blueprint('acctclog_bp', __name__)

def create_app(config_filename=None):
  app = Flask(__name__, instance_relative_config=True)
  
  basedir = app.config['BASEDIR']
  dbpath = os.path.join(basedir, 'clogs.db')
  
  app.config.from_pyfile(config_filename)
  app = register_blueprint(app)
  return app

def register_blueprint(app):
  app.register_blueprint(acct_bp, url_prefix='/account')
  app.register_blueprint(acctapi_bp, url_prefix='/api')
  app.register_blueprint(acctclog_bp, url_prefix='/clog')
  return app