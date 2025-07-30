from flask import Flask
from flask import Blueprint
from dpam.acctportal_route import account_bp as acct_bp
from dpam.acctapi import acctapi_bp

def create_app(config_filename=None):
  app = Flask(__name__, instance_relative_config=True)
  app.config.from_pyfile(config_filename)
  app = register_blueprint(app)
  return app

def register_blueprint(app):
  app.register_blueprint(acct_bp, url_prefix='/account')
  app.register_blueprint(acctapi_bp, url_prefix='/api')
  return app