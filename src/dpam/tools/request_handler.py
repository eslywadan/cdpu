from flask import request, Response, json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dsbase.tools.redis_db import RedisDb, CacheType
from dpam.tools.logger import Logger
import dpam.tools.reset_config as reset_config
from dpam.tools.cache_key import get_cache_key
import dpam.tools.account as account
from dpam.tools.error_handler import JSNError
from dsbase.tools.request_handler import validate_request_reg_permit
import re

#繼承Response，預設status code:200，預設mimetype:application/json
class JSNResponse(Response):
    def __init__(self, payload, status_code=200):
        Response.__init__(self, json.dumps(payload))
        self.status_code = status_code
        self.mimetype = 'application/json'

        Logger.log(f'End request: {status_code}')


def check_and_log(ignore_token=False, token=None):
    if ignore_token:
        Logger.log(f'Issue request: {request.method} {request.url}')
        return True

    if "apikey" in request.headers: 
        token = request.headers["apikey"]

    if request.args.get('token'):
        token = request.args.get('token')

    if token is not None:
        redis = RedisDb.default()
        client_info = redis.get(token)
    if client_info is not None:
        client_id = client_info[0:client_info.index(":")]
        permission = client_info[client_info.index(":")+1:]
        if permission:
            permission_list = permission.split("|")
            if "QUERY" in permission_list:
                Logger.log(f'Issue request: @{client_id} {request.method} {request.url}')
                return True

    Logger.log(f'Deny request: {request.method} {request.url}')
    return False


#region 讀寫cache
def find_cache():
    key = get_cache_key(request.full_path)
    redis = RedisDb.default()
    list = redis.get(key)
    if list is None: return None
    if list == '': return []
    return list.split(',')


def set_cache(list):
    try:
        key = get_cache_key(request.full_path)
        redis = RedisDb.default()
        expiry_hours=get_cache_expiry_hours()
        redis.set(key, ','.join(list), expiry_hours=expiry_hours)
    except Exception as err:
        logger = Logger.default()
        logger.error(f'"{err.args[0]}" on set_cache() in request_handler.py', exc_info=True)



#優先採用request.headers裡的cacheType，若沒有或無法解析再使用系統的cache_type
def get_cache_type():
    if "cacheType" in request.headers: 
        try:
            return CacheType[request.headers["cacheType"]]
        except:
            pass

    #200514:查詢eqpt，只使用cache，不查詢資料庫，即使當月
    #200515:只限CNVR
    #elif request.endpoint == "get_eqpt_list" and request.view_args['process'] == 'CNVR':
    #200520:不限CNVR
    elif request.endpoint == "get_eqpt_list" and "month" in request.args:
        return CacheType.READONLY

    return RedisDb.cache_type()

#採用request.headers裡的expiryHours，若沒有或無法解析回傳None(會使用預設的 expiry_hours)，若小於等於0則cache不會timeout
def get_cache_expiry_hours():
    if "expiryHours" in request.headers: 
        try:
            return float(request.headers["expiryHours"])
        except:
            pass
    
    #ch200513:如果查詢的區間是by month且是當月，非eqpt清單，cache一天
    elif 'month' in request.args and request.args['month'] == datetime.today().strftime('%Y-%m') and request.endpoint != "get_eqpt_list":
        return 24.0

    return None

def validate_ds_permission(registry, url):
    return validate_request_reg_permit(url, registry)

def validate_ds_permission_local(registry, url):
    """
        The validation function will consider the wild card in the reg string
        A registry may be empty or one to several reg string seperated in "," such as "/eng/ispec/define/F8,/eng/ispec/spec/F8"
    """
    print(f"request api name {url}")
    nde =url.partition("/ds")[2]
    permit = []
    # case registry value is empty
    if len(registry.strip())==0:  return "No Permit"
    # case registry is not empty and contains one or several regs
    for reg in registry.split(","): 
        if reg.startswith("-"): 
            reg_type = False
            reg_pat = reg.lstrip("-")
        else: 
            reg_type = True
            reg_pat = reg
        pat_match = re.search(reg_pat.removeprefix('/ds').replace("*",".+"),nde)    
        #else: pat_match = re.search(reg_pat.replace("*",".+"),nde) 
        print(f"reg_type: {reg_type}/ reg_pat:{reg_pat}")
        print(f"pat_match: {pat_match}")
        if pat_match is not None and pat_match.start() == 0: permit.append(reg_type)

    if permit.__len__() == 0 or permit.__contains__(False):
        return "No Permit"
    else :
        return "Permit"       