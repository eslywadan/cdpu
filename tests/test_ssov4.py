from flask import request, make_response, redirect
import requests
import urllib.parse as urltool
from tools.config_loader import ConfigLoader
from tools.logger import Logger

from tools.validate_user import validate_user, redirect_to_login, UserSessions

import os

os.environ["api_account_env"] = "test"

from tools.validate_user import get_env

assert get_env == "test"


os.environ["api_account_env"] = "prod"

from tools.validate_user import get_env

assert get_env == "prod"

