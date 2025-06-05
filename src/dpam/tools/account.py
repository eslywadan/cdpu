from dpam.dbtools.db_connection import DbConnection
import dpam.tools.crypto as crypto
import pandas as pd
import re
from dpam.dbtools.sql_buffer import SqlBuffer
from dsbase.tools.redis_db import RedisDb
from dpam.tools.logger import Logger, LogLevel
from datetime import datetime
from dpam.grpc_cust import clientapival_client as grpc_client
from dpam.db_access import insert_account, delete_account, update_account_registry

def get_client_info(client_id,type=2):
    sql = '''
    SELECT CLIENT_ID, PASSWORD, TYPE, EXPIRY, REGISTRY,PERMISSION,OWNER_USER_ID,BIND_GROUP,BIND_ROLE 
      FROM ACCOUNT'''
    buf = SqlBuffer(sql).add("CLIENT_ID", client_id)
    buf.add("TYPE", type)
    cn = DbConnection.default()
    df = pd.read_sql_query(buf.sql, cn)

    info = df.to_dict()
    
    return info

def get_clients_info(client_ids:list, type=2):
    sql = '''
    SELECT CLIENT_ID, PASSWORD, TYPE, EXPIRY, REGISTRY,PERMISSION,OWNER_USER_ID 
      FROM ACCOUNT'''
    buf = SqlBuffer(sql).add_in("CLIENT_ID", client_ids)
    buf = SqlBuffer(sql).add("TYPE", type)
    cn = DbConnection.default()
    df = pd.read_sql_query(buf.sql, cn)
    info = df.to_dict()
    return info

def get_client_info_grpc(client_id):
    
    info = grpc_client.get_clientinfo(client_id)
    
    return info

def get_client_apikey_grpc(client_id,password):
    
    apikey = grpc_client.get_clientapikey(client_id, password)
    
    return apikey

def verified_client_apikey_grpc(apikey):
    
    verified_apikey = grpc_client.get_verified_apikey(apikey)
    
    return verified_apikey

def check_client_id_password(client_id, password,rpsw=True):
    """
        If rpsw (required password flag), return apikey after verifying password and client id is effective
        If not rpsw, return apikey if client id is effective   
    """
    info = get_client_info(client_id)
    type = int(info["TYPE"][0])
    expiry = info["EXPIRY"][0]
    permission = info["PERMISSION"][0]
    registry = info["REGISTRY"][0]    

    # 1st step check if require password, if True, validate pass 
    if rpsw :
        assert len(info["PASSWORD"]) > 0
        Logger.log(f'2.Client info: {info}')
        password_correct = info["PASSWORD"][0]
        check_ok = (password_correct == crypto.crypto_password(type, password))
        Logger.log(f'{client_id} requestes apikey required password checked {check_ok}')
    
    elif not rpsw: 
        check_ok = True
        Logger.log(f'{client_id} requestes apikey pass password checked {check_ok}')
    else: 
        check_ok = False
        Logger.log(f'{client_id} requestes apikey required password checked {check_ok}')

    if check_ok:
        today = datetime.today().strftime("%Y-%m-%d")
        check_ok = expiry > today
        Logger.log(f'{client_id} requestes apikey not expiry checked {check_ok}')

    if check_ok:
        token = crypto.get_account_token(client_id)
        redis = RedisDb.default()
        redis.set(token, f"{client_id}:{permission}:{registry}", expiry_hours=24)
        client_api_key = {"clientid":client_id,"apikey":token,"expiry":24}
        Logger.log(f'{client_id} requestes apikey genereated and cahced at {redis._host}:{redis._port}')
        return client_api_key

    return None

def check_and_log(token=None):

    if token is not None:
        redis = RedisDb.default()
        client_info = redis.get(token)
    if client_info is not None:
        client_id = client_info.split(":")[0]
        permission = client_info.split(":")[1]
        registry = client_info.split(":")[2]
        if permission:
            permission_list = permission.split("|")
            if "QUERY" in permission_list:
                Logger.log(f'Issue request: @{client_id} {token} {registry}')
                return client_info

    Logger.log(f'Deny request: {token}')
    return False

def verify_token_clientid(token, _clientid):
    client_info = check_and_log(token=token)
    if client_info:
        client_id = client_info.split(":")[0]
        if client_id == _clientid: return True
        else: return False
    else: return False


def get_resource_permission(_rres:str,reg:list):
        bm = Account.__search_best_match(_rres,reg)
        if bm.endswith("/*"): # For those may contains registry value with negative sign
            rid = Account(bm, type=1)
            subdomains = _rres.removepredix(bm.strip('/*'))
            sub_bm = Account.__search_best_match(subdomains, rid.registry)
            if sub_bm.startswith('-'): f"{sub_bm} is negave sign"
            
            



class Account():
    """account table is used for maintaing the users' previledges on accessing the resources. All resources are expressed in the
    form of servies with type 1, and the user has type2. Generally, user can has registry values directly by service's id, but it 
    is not uncommon to use the group and role to define indirectly to link with resources 
    [Doc Reference](/dpam/docs/account_table.md)
    """
    registry = []
    base_resources = [{'CLIENT_ID': '/ds', 'TYPE': 1,'REGISTRY': '/retrain,/ml,/carux,/*'},
                      {'CLIENT_ID': '/ds/retrain', 'TYPE': 1,'REGISTRY': '/cds,/*'},
                      {'CLIENT_ID': '/ds/retrain/cds', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/ds/retrain/*', 'TYPE': 1,'REGISTRY': '-/cds'},
                      {'CLIENT_ID': '/ds/ml', 'TYPE': 1,'REGISTRY': '/regression,/class'},
                      {'CLIENT_ID': '/ds/ml/regression', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/ds/ml/class', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/ds/carux', 'TYPE': 1,'REGISTRY': '/apds'},
                      {'CLIENT_ID': '/ds/carux/apds', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/ds/*', 'TYPE': 1,'REGISTRY': '-/retrain,-/ml,-/carux'},
                      {'CLIENT_ID': '/cds', 'TYPE': 1,'REGISTRY': '/$clientid'},
                      {'CLIENT_ID': '/inocld', 'TYPE': 1,'REGISTRY': '/inx,/carux'},
                      {'CLIENT_ID': '/inocld/inx', 'TYPE': 1,'REGISTRY': '/prd,/tst'},
                      {'CLIENT_ID': '/inocld/inx/prd', 'TYPE': 1,'REGISTRY': '/retrain'},
                      {'CLIENT_ID': '/inocld/inx/prd/retrain', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/inocld/inx/tst', 'TYPE': 1,'REGISTRY': '/datastudio-ci-dev'},
                      {'CLIENT_ID': '/inocld/inx/tst/datastudio-ci-dev', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/inocld/carux', 'TYPE': 1,'REGISTRY': '/prd,/tst'},
                      {'CLIENT_ID': '/inocld/carux/prd', 'TYPE': 1,'REGISTRY': '/[TBD]'},
                      {'CLIENT_ID': '/inocld/carux/prd/retrain', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/inocld/carux/tst', 'TYPE': 1,'REGISTRY': '/datastudio-ci-dev'},
                      {'CLIENT_ID': '/inocld/carux/tst/datastudio-ci-dev', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/inodrv', 'TYPE': 1,'REGISTRY': '/inx,/carux'},
                      {'CLIENT_ID': '/inodrv/inx', 'TYPE': 1,'REGISTRY': '/APDRV_DATASTUDIO'},
                      {'CLIENT_ID': '/inodrv/inx/APDRV_DATASTUDIO', 'TYPE': 1,'REGISTRY': '*'},
                      {'CLIENT_ID': '/inodrv/carux', 'TYPE': 1,'REGISTRY': '*'}]
    
    base_groups =    [{'CLIENT_ID': 'inx', 'TYPE': 3,'REGISTRY': '/inocld/inx,/inodrv/inx'},
                      {'CLIENT_ID': 'carux', 'TYPE': 3,'REGISTRY': '/inocld/carux,/inodrv/carux'}]

    base_roles =    [{'CLIENT_ID': 'retrain', 'TYPE': 4,'REGISTRY': '/ds/retrain/*'},
                     {'CLIENT_ID': 'retrain_cds', 'TYPE': 4,'REGISTRY': '/ds/retrain/cds'},
                     {'CLIENT_ID': 'ml', 'TYPE': 4,'REGISTRY': '/ds/ml'},
                     {'CLIENT_ID': 'carux_apds', 'TYPE': 4,'REGISTRY': '/ds/carux/apds'}]
    
    typical_users = [{'CLIENT_ID': 'inx_retrain_user', 'TYPE': 2,'REGISTRY': '','BIND_GROUP': 'inx','BIND_ROLE': 'retrain'},
                     {'CLIENT_ID': 'inx_retrain_cds_user', 'TYPE': 2,'REGISTRY': '','BIND_GROUP': 'inx','BIND_ROLE': 'retrain_cds'},
                     {'CLIENT_ID': 'inx_ml', 'TYPE': 2,'REGISTRY': '','BIND_GROUP': 'inx','BIND_ROLE': 'ml'},
                     {'CLIENT_ID': 'carux_pd_user', 'TYPE': 2,'REGISTRY': '','BIND_GROUP': 'carux','BIND_ROLE': 'carux_apds'},]
    
    base_resources_id = [res['CLIENT_ID'] for res in base_resources]
    
    @classmethod
    def cur_switch(cls, cur):
        """cur 'On' -> Create a connection
                 None -> commit and close
        """    
        if cur:
            cls.cn = DbConnection.default()
            cls.cur = cls.cn.cursor()
        else: 
            cls.cur.close()
            cls.cn.commit()
            cls.cn.close()
    
    @classmethod
    def _convert_account_table(cls,temp_table_ = "account_old",move_legacy_data=True):
        cls.drop_table_if_exists(temp_table_)
        cls.alter_table_name(temp_table_)
        cls.create_table()
        if move_legacy_data:  cls.insert_legacy_data()
        
    @classmethod
    def alter_table_name(cls, ntable):
        new_table_name = ntable
        cls.cur_switch('On')
        cls.cur.execute(f"ALTER TABLE account RENAME TO {new_table_name}")
        cls.cur_switch(None)
            
    @classmethod
    def create_table(cls):  
        cls.cur_switch('On')  
        cls.cur.execute("""
                    CREATE TABLE account (
                        CLIENT_ID TEXT,
                        PASSWORD TEXT,
                        TYPE INTEGER,
                        EXPIRY TEXT,
                        PERMISSION TEXT,
                        OBSOLETE INTEGER,
                        OWNER_USER_ID TEXT,
                        CREATE_DTTM TEXT,
                        REGISTRY VARCHAR,
                        BIND_ROLE TEXT,
                        BIND_GROUP TEXT,
                        PRIMARY KEY (CLIENT_ID, OWNER_USER_ID, TYPE));
                    """)
        cls.cur_switch(None)
        
    @classmethod
    def drop_table_if_exists(cls, tablename):
        cls.cur_switch('On')
        cls.cur.execute(
            f"""DROP TABLE IF EXISTS {tablename}"""
        )
        cls.cur_switch(None)
        
    @classmethod    
    def insert_legacy_data(cls, legacy_table='account_old', exclude_system_owner_data=True):
        cls.cur_switch('On') 
        if exclude_system_owner_data: OWNER_CRITERION = "system"
        else:  OWNER_CRITERION = "TBD"
        cls.cur.execute(f"""
                    INSERT INTO account (CLIENT_ID, OWNER_USER_ID, TYPE, 
                    PASSWORD, EXPIRY, PERMISSION, OBSOLETE, CREATE_DTTM,
                    REGISTRY, BIND_ROLE, BIND_GROUP) SELECT CLIENT_ID, 
                    OWNER_USER_ID, TYPE, PASSWORD, EXPIRY, PERMISSION,
                    OBSOLETE, CREATE_DTTM, REGISTRY, BIND_ROLE, BIND_GROUP
                    from {legacy_table} where OWNER_USER_ID <> "{OWNER_CRITERION}";
                    """)
        cls.cur_switch(None)
    
    @classmethod
    def _create_if_not_exist(cls, client_id, registry, type=1, user_id="system", bind_group=None, bind_role=None):
        """
        private method to create if not existed the client id and update the registry by the passing value.
        Default TYPE=1, user_id = 'system' are allowed to be overwritten and also allowed to pass the bind_group and bind_role values
        """
        _info = get_client_info(client_id, type=type)
        if _info['CLIENT_ID'] == {}:
            insert_account(client_id,password="",user_id=user_id,type=type, bind_group=bind_group, bind_role=bind_role)
        update_account_registry(client_id, registry=registry, type=type)
    
        
    @classmethod
    def _recreate_if_exist(cls, client_id, registry, type=1, user_id="system", bind_group=None, bind_role=None):
        """
        Auto recreate if existed in the account table.
        TYPE=1 
        """
        _info = get_client_info(client_id,type=type)
        if _info['CLIENT_ID'] != {}: delete_account(client_id=client_id,type=type)
        if _info['CLIENT_ID'] == {}:
            insert_account(client_id,password="",user_id=user_id,type=type, bind_group=bind_group, bind_role=bind_role)
        update_account_registry(client_id, registry=registry,type=type)
    
    @classmethod
    def _create_base_account_data(cls):
        cls._create_base_resources()
        cls._create_base_group()
        cls._create_base_role()
        cls._create_typical_user()
       
    @classmethod
    def _create_base_resources(cls):
        """
        check if base resources existed in table, create automatically if not.
        """
        for base_resouce in cls.base_resources:
            cls._create_if_not_exist(client_id=base_resouce['CLIENT_ID'],registry=base_resouce["REGISTRY"],type=base_resouce['TYPE'])

    @classmethod
    def _create_base_group(cls):
        """
        check if base group existed in table, create automatically if not.
        """
        for base_group in cls.base_groups:
            cls._recreate_if_exist(client_id=base_group['CLIENT_ID'],registry=base_group["REGISTRY"],type=base_group['TYPE'])

    @classmethod
    def _create_base_role(cls):
        """
        check if base role existed in table, create automatically if not.
        """
        for base_role in cls.base_roles:
            cls._recreate_if_exist(client_id=base_role['CLIENT_ID'],registry=base_role["REGISTRY"],type=base_role['TYPE'])

    @classmethod
    def _create_typical_user(cls):
        """
        check if typical user existed in table, create automatically if not.
        """
        for typical_user in cls.typical_users:
            cls._recreate_if_exist(client_id=typical_user['CLIENT_ID'],registry=typical_user["REGISTRY"],type=typical_user['TYPE'],
                                     bind_group=typical_user['BIND_GROUP'],bind_role=typical_user['BIND_ROLE'])

    @classmethod
    def _create_resource_client_by_user_client_registry(cls):
        cls._get_user_clients_all_info
        cls.ucs["REGISTRY"]
        cls._get_resource_clients_all_info
    
    @classmethod
    def _get_resource_clients_all_info(cls):
        return cls._get_clients_all_info_by_type(1)
    
    @classmethod
    def _get_user_clients_all_info(cls):
        return cls._get_clients_all_info_by_type(2)
    
    @classmethod
    def _get_group_clients_all_info(cls):
        return cls._get_clients_all_info_by_type(3)

    @classmethod
    def _get_role_clients_all_info(cls):
        return cls._get_clients_all_info_by_type(4)
        
    @classmethod
    def _get_clients_all_info_by_type(cls, type):
        type=type
        sql = '''
        SELECT CLIENT_ID, TYPE, EXPIRY, REGISTRY,PERMISSION 
        FROM ACCOUNT'''
        buf = SqlBuffer(sql).add("TYPE", type)
        cn = DbConnection.default()
        df = pd.read_sql_query(buf.sql, cn)
        info = df.to_dict()
        cls.rcs = info
        return info
    
    @classmethod
    def _get_resource_client_info(self,clientid):
        return self._get_client_info_by_type(clientid=clientid, type= 1)
    
    @classmethod
    def _get_user_client_info(self,clientid):
        return self._get_client_info_by_type(clientid=clientid, type= 2)

    @classmethod
    def _get_group_client_info(self,clientid):
        return self._get_client_info_by_type(clientid=clientid, type= 3)    

    @classmethod
    def _get_role_client_info(self,clientid):
        return self._get_client_info_by_type(clientid=clientid, type= 4)
    
    @classmethod
    def _get_client_info_by_type(cls, clientid, type):
        type=type
        sql = '''
        SELECT CLIENT_ID, TYPE, EXPIRY, REGISTRY,PERMISSION 
        FROM ACCOUNT'''
        buf = SqlBuffer(sql).add("TYPE", type)
        buf.add("CLIENT_ID",clientid)
        cn = DbConnection.default()
        df = pd.read_sql_query(buf.sql, cn)
        info = df.to_dict()
        cls.rcs = info
        return info
    
    @classmethod
    def _get_res_client_registry_info(cls,clientId):
        info = cls._get_client_registry_info(clientId=clientId,type=1)
        return info

    @classmethod
    def _get_user_client_registry_info(cls,clientId):
        info = cls._get_client_registry_info(clientId=clientId,type=2)
        return info
    
    @classmethod
    def _get_grp_client_registry_info(cls,clientId):
        info = cls._get_client_registry_info(clientId=clientId,type=3)
        return info
    
    @classmethod
    def _get_role_client_registry_info(cls,clientId):
        info = cls._get_client_registry_info(clientId=clientId,type=4)
        return info
    
    @classmethod
    def _get_client_registry_info(cls,clientId,type):
        sql = '''
        SELECT REGISTRY 
        FROM ACCOUNT'''
        buf = SqlBuffer(sql).add("CLIENT_ID", clientId)
        buf.add("TYPE", type)
        cn = DbConnection.default()
        df = pd.read_sql_query(buf.sql, cn)
        info = df.to_dict()
        cls.rcs = info
        return info
    
    @classmethod
    def _resource_clientid_reg_value(cls, clientid, _reg):
        """
        utility function  
                 handling on removing the common part
                 clientid is usually started with the begining domain and end on partial or full domain name
                 _reg is usually the full domain name or start with sub domain.
                 The function will find the common part and then reserve the client id as the leading domain, 
                 the _reg will be replaced by eliminating the common part.
        Examples: 
               1. given(clientid = '/ds/retrain/cds', _reg = '/cds') -> return ('/ds/retrain/cds','*')
               2. given(clientid = '/ds/retrain', _reg = '/cds') -> return ('/ds/retrain','/cds')
               3. given(clientid = '/ds/retrain', _reg = '/retrain/cds') -> return ('/ds/retrain','/cds')
               4. given(clientid = '/ds/retrain', _reg = '/retrain/abc') -> return ('/ds/retrain','/abc')
               5. given(clientid = '/ds/retrain', _reg = '/abc') -> return ('/ds/retrain','/abc')
        """
        path1 = cls._normalize_path(clientid)
        path2 = cls._normalize_path(_reg)
        parts1 = path1.strip('/').split('/')
        parts2 = path2.strip('/').split('/')
        # Find common prefix
        common = []
        for p1, p2 in zip(parts1, parts2):
            if p1 == p2:
                common.append(p1)
            else:
                break
        common_len = len(common)
        base_path = '/' + '/'.join(common)
        # Determin what remains
        remaining1 = parts1[common_len:]
        remaining2 = parts2[common_len:]
        if not remaining2 and remaining1:
            # Full path is already represented in path1
            return (path1, '*')
        elif not remaining1 and remaining2:
            return (path1, '/' + '/'.join(remaining2))
        elif not remaining1 and not remaining2:
            return (path1, '*') # Exact the same path
        else:
            return (base_path, '/' + '/'.join(remaining2))
    
    @classmethod
    def _normalize_path(cls,path:str) -> str:
        """Ensure a single leading slash, no trailing slash
        """
        return '/' + re.sub(r'/{2,}', '/', path.strip('/'))
    
    @classmethod
    def _find_best_match_res(cls, _res):
        """
        If return value is None, there is not the best matched res
        If return value is a tuple with two elements , the firt element is the res and the 2nd element is the reg value
        """   
        res_info = Account._get_resource_clients_all_info()
        candidates = [p for _, p in res_info['CLIENT_ID'].items()]
                
        best_match = None
                
        best_match_client = cls.__search_best_match(_res, candidates)
        
        if best_match_client:
            _match_ix = next((ix for ix, res_client in res_info['CLIENT_ID'].items() if res_client == best_match_client ), None)
            if _match_ix: best_match = (best_match_client, res_info['REGISTRY'][_match_ix])
            else: best_match = (best_match_client,None)          
                 
        return best_match

    @classmethod
    def __search_best_match(cls, _res:str, candidates:list):
        res_segments = _res.strip("/").split("/")
        longest_common_segments = 0
        best_match_client = None
        
        negative = False
        for candiate in candidates:
            if candiate.startswith('-'): 
                negative = True
                candiate = candiate.removeprefix('-') # Remove the negative sign to do match
            candiate_segments = candiate.strip("/").split("/")
            # Except client id is endwith '/*' is allowed to be the best matched parent 
            if len(candiate_segments) > len(res_segments): continue
            if (len(candiate_segments) == len(res_segments)) and not (candiate_segments[-1] != "/*"): continue
            common = 0
            for i in range(len(candiate_segments)):
                if candiate_segments[i] == res_segments[i]: common += 1
                elif candiate_segments[i] == "*" and res_segments[i] != "*": common += 1
                elif candiate_segments[i] != res_segments[i]:
                    common = 0 
                    break
            if common > longest_common_segments:
                best_match_client = candiate
                longest_common_segments = common
        
        prefix = ""
        if negative: prefix = '-' # Add back the negative sign to prefix
        return f"{prefix}{best_match_client}"
    
    
    def __init__(self, clientId, type=2):
        """
        type=2 is user by default
        """
        self.clientid = clientId
        self.type = type
        return self.set_client_registry()
       
    def set_client_registry(self):
        """
        set basic related info according to given client
        """
        clientinfo = self._get_client_info()
        self.clientinfo = clientinfo
        if clientinfo["status"]:
            self._registry = clientinfo["clientinfo"]['REGISTRY'][self.client_index]
            self._bindGrp = clientinfo["clientinfo"]['BIND_GROUP'][self.client_index]
            self._bindRole = clientinfo["clientinfo"]['BIND_ROLE'][self.client_index]
            if self._bindGrp != 'None': self._add_group_registry()
            if self._bindRole != 'None': self._add_role_registry()
            self._merge_registry() # generate self.registry
        else: return {"status":False,"message": f"Given client {self.clientid} with {self.type} has not the client info"}
    
    def auto_correct_none_resource_client_registry_value(self,log=None):
        """
        This function will do registry validation via .validate_non_resource_client_registry_value method and
        auto update only the pass resources. 
        """
        if log: Logger_ = log
        else: Logger_ = Logger
        
        if self.type not in [2, 3, 4]: return {"status":False,"message":f"Givev client type {self.type} is not none resource"}
        Logger_.log(f"Auto correct none resource account {self.clientid} type {self.type}")
        
        validate_ = self.validate_none_resource_client_registry_value()
        
        if validate_['status'] and len(validate_['pass'])>0:
            update_account_registry(client_id=self.clientid, registry=",".join(validate_['pass']), type=self.type)
            Logger_.log(f" Auto update the registry by validating pass resources: {validate_['pass']} ")
            self.set_client_registry()
            return {"status":validate_['status'],"pass":validate_['pass'], "invalid":validate_['invalid']}
        elif validate_['status'] and len(validate_['pass']) == 0:
            Logger_.log(f"status: {validate_['status']}, pass: {validate_['pass']}, invalid: {validate_['invalid']}, message : has not pass res to be updated")
            return {"status":validate_['status'],"pass":validate_['pass'], "invalid":validate_['invalid'], "message":"has not pass res to be updated"}
        else:
            Logger_.log(f"status: {validate_['status']}, message: has not res to be updated")
            return {"status":validate_['status'],"message":"has not res to be updated"}
    
    def validate_none_resource_client_registry_value(self,temp=[], autoupdate=True, log=None):
        """
        If temp is not [], given list will be treated to simulate the registry value.
        If autoupdate, then will try to find the best match and create the un-existed item automatilcally
        The registry value is validated to ouput 3 possible cases:
        1. The registry value matched exactly that existed in the resource client list
        2. The registry value has not any  best matched resource client id thus is forbideen to create automatically 
        3. The registry value though does not exist in resource client but has a best matched resource client thus can be created automatically
        Ref: `matched exactly` is totally the same, best matched is partially matched from the beginging domain, the domain 
        name must matched exactly, the best matched resource client id is the one has the most number of matched domains
        Please note that, if the autoupdate=False, will do only the 1. to check if existed the registry value
        """
        if log:
            Logger_ = log
        else:
            Logger_ = Logger
        
        if self.registry == []: self.set_client_registry()
        
        if not isinstance(temp, list): 
            return {"status": False, "message":f"Given temp registry value shoud be in list type"}  
        if len(temp) == 0 and self.registry == []:
            Logger_.log(f"Given temp or self.registry is None") 
            return {"status": False, "message":f"Given user client {self.clientid} has not any registry value"}
        elif isinstance(temp, list) and (len(temp) >= 1) : _registry = temp
        else: _registry = self.registry
            
        message = ""
        pass_res = []
        invalid_res = []
        for res in _registry:
            res_info = Account._get_res_client_registry_info(res)
            if res_info["REGISTRY"] == {} and autoupdate:  # Verified res does not exist
                _bm_res = self._find_best_match_res(res)
                if _bm_res:                #case 3 can be appended to an existed resource 
                    Account._create_if_not_exist(client_id=res,registry='*')
                    _reg = Account._resource_clientid_reg_value(_bm_res[0],res)[1]
                    append_reg =   f"{_bm_res[1]},{_reg}"
                    update_account_registry(client_id=_bm_res[0],registry=append_reg,type=1)
                    pass_res.append(res) 
                    message = f"{message}\n Given {res} has matched res pattern {_bm_res}, auto created and append registry value automatically"
                    Logger_.log(f"Give {res} does not exist, while found best matched res  {_bm_res}, auto create {res} and updte the registry of {_bm_res}")
                else:
                    invalid_res.append(res) 
                    message = f"{message}\n Given {res} has not matched res pattern, cannot create automatically"
                    Logger_.log(f"Give {res} does not exist, neither found best matched res, try to manually correct")    
            elif res_info["REGISTRY"] == {} and not autoupdate:
                invalid_res.append(res) 
                message = f"{message}\n Give {res} does not exist without autoupdate" # case 1
                Logger_.log(f"Give {res} does not exist without autoupdate") 
            elif len(res_info["REGISTRY"]) >= 1 :
                pass_res.append(res) 
                message = f"{message}\n Give {res} exist" # case 1
                Logger_.log(f"Give {res} exist") 
        
        return {"status":True, "pass": pass_res, "invalid": invalid_res, "message":message}
            
    def validate_resource_client_reg_value(self, autoupdate=True, log=None):
        """
        resource type has registry values
        (1) end point : *
        (2) sub-domain : sub-domain name
        (3) all w/exception : /*
        If (1), the client id is the full api name
        If (2)/(3), the concating name should also existed in the resources. If it is not the case, 
        the validating function will create it automatically
        """
        if log:
            Logger_ = log
        else:
            Logger_ = Logger
        
        if self.type not in [1]:
            Logger_.log(f"Gievn client id {self.clientid} has type {self.type} that is not resoure") 
            return {"status" : False, "message":f"Gievn client id {self.clientid} has type {self.type} that is not resoure"}
        if self._registry == '*': 
            Logger_.log(f"Gievn client id {self.clientid} is endpoint")
            return {"status" : True, "message":f"Gievn client id {self.clientid} is endpoint"}
        _regs = self.registry
        message = ""
        pass_res = []
        invalid_res = []
        for reg in _regs:
            _sub_resource_id = f"{self.clientid.rstrip('/*')}{reg}"
            clientinfo = self._get_resource_client_info(_sub_resource_id)
            if len(clientinfo["CLIENT_ID"]) == 0:
                if autoupdate:
                    self._create_if_not_exist(client_id=_sub_resource_id,registry='*',type=1)
                    Logger_.log(f"CLIENT ID {self.clientid} validated on the registry value {reg} does not exist the {_sub_resource_id} has been created automatically")
                    message = f"{message} /n CLIENT ID {self.clientid} validated on the registry value {reg} does not exist the {_sub_resource_id} has been created automatically"
                    pass_res.append(reg)
                else:
                    Logger_.log(f"CLIENT ID {self.clientid} validated on the registry value {reg} does not exist the {_sub_resource_id} wo autoupdate")
                    invalid_res.append(reg) 
            if len(clientinfo["CLIENT_ID"]) == 1:    
                Logger_.log(f"CLIENT ID {self.clientid} validated on the registry value {reg} exist the {_sub_resource_id}")
                message = f"{message} /n CLIENT ID {self.clientid} validated on the registry value {reg} exist the {_sub_resource_id}"
                pass_res.append(reg)
    
    
    def _get_client_info(self):
        
        clientinfo = get_client_info(self.clientid, self.type)
        if len(clientinfo['CLIENT_ID']) == 0: 
            return {"status":False,"message":f"Given client id : {self.clientid} & type {self.type} does not exist"}
        self.client_index = 0
        return {"status":True,"message":f"Given client id : {self.clientid} has client info","clientinfo":clientinfo}
            
    def _add_group_registry(self):
        """
        A user client's registry is a collection of registry value from its direct registry, bind role and bind group.
        The functionn is to add the group registry to the user's registry
        """
        if not self._bindGrp: 
            return
        for grp in self._bindGrp.split(","):
            reg_info = Account._get_grp_client_registry_info(grp.strip()) 
            if len(reg_info['REGISTRY']) > 0:
                self._registry = f"{self._registry},{reg_info['REGISTRY'][0]}"
                
    def _add_role_registry(self):
        """
        A user client's registry is a collection of registry value from its direct registry, bind role and bind group.
        The functionn is to add the role registry to the user's registry
        """
        if not self._bindRole: return
        for role in self._bindRole.split(","):
            reg_info = Account._get_role_client_registry_info(role.strip()) 
            if len(reg_info['REGISTRY']) > 0:
                self._registry = f"{self._registry},{reg_info['REGISTRY'][0]}"
    
    def _merge_registry(self):
        regs = []
        if isinstance(self._registry, str):
            for reg in self._registry.strip(",").split(","):
                if reg not in regs: regs.append(reg)
        self.registry = regs