from flask import Flask, render_template, request, json, make_response, redirect
import dpam.db_access as db
import dpam.tools.validate_user as validate_user
from dpam.tools.account import check_client_id_password, verify_token_clientid
from flask import Blueprint
from flask_restx import Api, Resource, fields
from dpam.tools.logger import Logger
from dpam.tools.request_handler import validate_ds_permission
from dpam.tools.crypto import get_account_token

# app = Flask(__name__)
acctapi_bp = Blueprint('acctapi_bp', __name__)

account_api = Api(acctapi_bp)

# Verification Model
apikeyverification_model = account_api.model('ApiKeyVerification', {
    'projectId': fields.String(required=False, description='Project ID', default=''),
    'clientId': fields.String(required=True, description='Client ID'),
    'apiKey': fields.String(required=True, description='Api Key')
})

# request api key by clientid/password Model
clientidpassword_model = account_api.model('ClientIdPassword', {
    'projectId': fields.String(required=False, description='Project ID', default=''),
    'clientId': fields.String(required=True, description='Client ID'),
    'passWord': fields.String(required=True, description='Pass Word')
})

@account_api.route('/vapikey')
class VerifyApiKey(Resource):
    @account_api.doc(description='Post client id and apikey to verify')
    @account_api.expect(apikeyverification_model)
    def post(self):
        data = request.get_json()
        #projectid = data.get('projectId') 
        client = data.get('clientId')
        apikey = data.get('apiKey')
        validation = verify_token_clientid(token=apikey,_clientid= client)
        return validation, 200

@account_api.route('/apikey')
class GetApiKey(Resource):
    @account_api.doc(description='Post client id and password to get the api key')
    @account_api.expect(clientidpassword_model)
    def post(self):
        data = request.get_json()
        #projectid = data.get('projectId') 
        client = data.get('clientId')
        password = data.get('passWord')
        apikey = check_client_id_password(client_id= client, password=password)
        return apikey, 200

# Setup Security Definition for Swagger/Open API
account_api.authorizations = {
     'ssotoken':{
          'type': 'apiKey',
          'in': 'header',
          'name': 'Authorization',
          'description': 'Format: Bearer <API Key>'          
     }
}

@account_api.route('/user')
class ValidateSSOtoken(Resource):
    @account_api.doc(security='ssotoken', description='get user id by sso token')
    def get(self):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith('Bearer '):
            # Extract apikey from header
            given_token = auth_header.split(" ")[1]
            Logger.log(f"giveb token is via auth header in Bearer {given_token}")
            (user_id, sess_key) = validate_user.validate_user(token_required=True, token=given_token)
            if user_id is None: return {"message": "Given token is not correct",
                                        "received": f"given token: {given_token} "}, 401
            return user_id, 200


@account_api.route('/user/clients')
class UserClients(Resource):
    @account_api.doc(security='ssotoken', description="get user's client ids by sso token")
    def get(self):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith('Bearer '):
            # Extract apikey from header
            given_token = auth_header.split(" ")[1]
            Logger.log(f"giveb token is via auth header in Bearer {given_token}")
            (user_id, sess_key) = validate_user.validate_user(token_required=True, token=given_token)
            
            if user_id is None: return {"message": "Given token is not correct",
                                        "received": f"given token: {given_token} "}, 401
            accounts = db.select_accounts_for_owner(user_id)
            Logger.log(f"list accounts created by {user_id}/accounts: {accounts}")
            return accounts, 200


account_parser = account_api.parser()
account_parser.add_argument('request_permit', type=str, help='Optional to update default /ds/carux/apds')
@account_api.route('/user/permits/client')
class UserPermitsClient(Resource):
    """
        The class find one client that has requested permite or none
        The requested permits has type '/ds' as data servrice or .. 
    """
    @account_api.doc(security='ssotoken', description="get one from user's clients that has requested permits")
    @account_api.expect(account_parser)
    def get(self):
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith('Bearer '):
            # Extract apikey from header
            given_token = auth_header.split(" ")[1]
            Logger.log(f"giveb token is via auth header in Bearer {given_token}")
            (user_id, sess_key) = validate_user.validate_user(token_required=True, token=given_token)
        else:
            return {"message": "Given token is not correct",
                                    "received": f"given token: zzz"}, 401 
        self._get_client(user_id)
        
        if self.client is []:
            Logger.log(f"user {self.user_id} has not owned client granted the requested permits {self.request_permits} ")
            return {"clientid":None,"msg": f"user {self.user_id} has not owned client granted the requested permits {self.request_permits} "}, 200
        Logger.log(f"list accounts {self.client} created by {self.user_id} has requested permissoin{self.request_permits}")
        return {"clientid":self.client}, 200
    
    def _get_client(self, user_id):        
        self.user_id = user_id
        self.request_permits=self.get_request_permits()
        self.client = self.get_client_with_permit(self.user_id, self.request_permits)
        
    def get_request_permits(self):
        _request_permit = request.args.get('request_permit')
        if _request_permit: request_permit = _request_permit
        else: request_permit = '/ds/carux/apds'
        return request_permit
    
    def get_client_with_permit(self,user_id, request_permits):
            accounts_ = db.select_accounts_registry_for_owner(user_id, resp_type="records")
            _clients = []
            for account in accounts_:
                if account['REGISTRY'] is not None:
                    if validate_ds_permission(account['REGISTRY'], request_permits)=="Permit": _clients.append(account['CLIENT_ID'])
            return _clients

@account_api.route('/user/permits/client/apikey')
class UserPermitClientApikey(UserPermitsClient):
    """
        Select one client id has the required permits from the user's client ids. 
    """
    @account_api.doc(security='ssotoken', description="get api key if user owns a client id with requested permit")
    @account_api.expect(account_parser)
    def get(self):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith('Bearer '):
            # Extract apikey from header
            given_token = auth_header.split(" ")[1]
            Logger.log(f"giveb token is via auth header in Bearer {given_token}")
            (user_id, sess_key) = validate_user.validate_user(token_required=True, token=given_token)
            
            if user_id is None: return {"message": "Given token is not correct",
                                        "received": f"given token: {given_token} "}, 401
            self._get_client(user_id)
            if len(self.client)>0: 
                apikey = check_client_id_password(self.client[0], "", rpsw=False)
                Logger.log(f"accounts {self.client[0]} created by {user_id}/has grant the apikey: {apikey}")
                return apikey, 200
            else:     
                Logger.log(f"accounts {user_id}/has not client with requsted permit {self.request_permits}")
                return f"accounts {user_id}/has not client with requsted permit {self.request_permits}", 200
            

@account_api.route('/<string:client>/apikey')
class UserClients(Resource):
    @account_api.doc(security='ssotoken', description="get api key by user's client id")
    def get(self, client):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith('Bearer '):
            # Extract apikey from header
            given_token = auth_header.split(" ")[1]
            Logger.log(f"giveb token is via auth header in Bearer {given_token}")
            (user_id, sess_key) = validate_user.validate_user(token_required=True, token=given_token)
            
            if user_id is None: return {"message": "Given token is not correct",
                                        "received": f"given token: {given_token} "}, 401
            
            apikey = check_client_id_password(client,"", rpsw=False)
            Logger.log(f"accounts {client} created by {user_id}/has grant the apikey: {apikey}")
            return apikey, 200



def get_index_page():
    (user_id, sess_key) = validate_user.validate_user(token_required=True)
    if user_id is None: return validate_user.redirect_to_login()
    
    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    response = make_response(render_template('index.html', user_id=user_id, is_admin=validate_user.is_admin(user_id), msg_type=msg_type, message = message))
    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

#@account_api.route('/ssov4')
def ssov4():
    """
    base route require token attached with the request. If a user has not the token attached, it will be redirect
    to sso's log-in page. SSO will check if exist the effective token and reuse it or let user re-log-in to get a fresh token
    """
    (user_id, sess_key) = validate_user.validate_user(token_required=True)
    if user_id is None: return validate_user.redirect_to_login()
    Logger.log(f"ssov4: user_id is {user_id} type: {type(user_id)}")
    response = make_response(render_template('ssov4_simple.html', user_id=user_id ))
    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

#@account_api.route('/session')
def session():
    """
    base route is not require token attached with the request. 
    it will reuse the cookie's data as well. 
    """
    (user_id, sess_key) = validate_user.validate_user(token_required=False)
    if user_id is None: return validate_user.redirect_to_login()
    Logger.log(f"ssov4: user_id is {user_id} type: {type(user_id)}")
    response = make_response(render_template('ssov4_simple.html', user_id=user_id ))
    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

#@account_api.route('/accounts_for_admin')
def browse_accounts():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = "/account/accounts_for_admin"
    
    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_accounts_for_admin()
    response = make_response(render_template('accounts_for_admin.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

        
#@account_api.route('/accounts_for_owner')
def browse_owner_accounts():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = "/account/accounts_for_owner"

    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_accounts_for_owner(user_id)
    Logger.log(f"list accounts created by {user_id}/accounts: {accounts}")
    response = make_response(render_template('accounts_for_owner.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message, user_id=user_id))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response


#@account_api.route('/create')
def create_account():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('create_account.html', client_id = "", error = "", user_id = user_id, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

#@account_api.route('/insert' , methods=['POST'])
def insert_account():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        password = request.form["txt_password"] if "txt_password" in request.form else ""
        password2 = request.form["txt_password2"] if "txt_password2" in request.form else ""
        user_id = request.form["txt_user_id"] if "txt_user_id" in request.form else ""
            
        error = "Client ID cannot be blank! " if client_id == "" else ""
        error += "Please confirm your password again!" if password != password2 or password == "" else ""
        list_page = validate_user.get_list_page()
        if error == "":
            db_result = db.insert_account(client_id, password, user_id)
            return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
            
    except Exception as err:
        error = err.args[0]

    return render_template('create_account.html', client_id = client_id, error = error, user_id = user_id, list_page = list_page)


#@account_api.route('/edit/<string:client_id>')
def edit_account_for_admin(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    account = db.select_account_for_admin(client_id)
    if account is None:
        account = {'CLIENT_ID':'', 'EXPIRY':'', 'PERMISSION':'', 'OBSOLETE':False, 'REGISTRY':''}
        error = "Client Account not found!"
    else:
        error = ""

    response = make_response(render_template('edit_account.html', account = account, error = error, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response
        
#@account_api.route('/update', methods=['POST'])
def update_account_for_admin():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        expiry = request.form["txt_expiry"] if "txt_expiry" in request.form else ""
        registry = request.form["txt_registry"] if "txt_registry" in request.form else ""
        permissions = []
        if "chk_perm_query" in request.form:
            permissions.append("QUERY") 
        if "chk_perm_debug" in request.form:
            permissions.append("DEBUG") 
        if "chk_perm_admin" in request.form:
            permissions.append("ADMIN") 
        permission = "|".join(permissions)

        obsolete = "chk_obsolete" in request.form
        
        db_result = db.update_account(client_id, expiry, permission, obsolete, registry)

        return redirect("/account/accounts_for_admin?msg_type=success&db_result="+db_result.name)

    except Exception as err:
        account = db.select_account_for_admin(client_id)
        return render_template('edit_account.html', account = account, error = err.args[0], list_page = validate_user.get_list_page())


#@account_api.route('/delete/<string:client_id>')
def delete_account(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('delete_account.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response
        
#@account_api.route('/db_delete', methods=['POST'])
def db_delete_account():
    try:
        list_page = validate_user.get_list_page()
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        db_result = db.delete_account(client_id)
        return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
    except Exception as err:
        return render_template('delete_account.html', client_id = client_id, error = err.args[0], list_page = list_page)

#@account_api.route('/change_password/<string:client_id>')
def change_password(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('change_password.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

#@account_api.route('/db_change_password', methods=['POST'])
def db_change_password():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        password = request.form["txt_password"] if "txt_password" in request.form else ""
        password2 = request.form["txt_password2"] if "txt_password2" in request.form else ""

        error = "Please confirm your password again!" if password != password2 or password == "" else ""
        if error == "":
            db_result = db.change_password(client_id, password)
            return redirect("/account/accounts_for_owner?msg_type=success&db_result="+db_result.name)
        
    except Exception as err:
        error = err.args[0]

    return render_template('change_password.html', client_id = client_id, error = error, list_page = validate_user.get_list_page())


#@account_api.route('/request_apikey/<string:client_id>')
def request_apikey(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('request_apikey.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

#@account_api.route('/grpc_get_apikey', methods=['POST'])
def grpc_get_apikey():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        password = request.form["txt_password"] if "txt_password" in request.form else ""
        apikey = ""
        error = "Please confirm your password again!" if password == "" else ""
        if error == "":
            
            apikey = account.get_client_apikey_grpc(client_id, password)
            print("%s,%s,%s", apikey.clientid, apikey.apikey, apikey.expiry)
            # return redirect("/accounts_for_owner?msg_type=success&db_result="+db_result.name)
            # apikey = "YuGoTahaPP"
            return render_template('request_apikey.html', client_id = client_id, apikey = apikey.apikey, list_page = validate_user.get_list_page())
        
    except Exception as err:
        error = err.args[0]

    return render_template('request_apikey.html', client_id = client_id, error = error, list_page = validate_user.get_list_page())

#@account_api.route('/copy_demo')
def copy_demo():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('copy_demo.html'))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response


if __name__ == '__main__':
    account_api.run(host='0.0.0.0', port=3400)