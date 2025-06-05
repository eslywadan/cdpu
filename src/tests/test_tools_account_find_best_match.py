from dpam.tools.account import Account
from dpam.db_access import delete_account
"""
The testing script is to ensure the Account.search_best_match() method will serve both the
registry maintaining and the request permit processes
"""

#            Arguments|_res:str               |candidates:list
#------------------------------------------------------------        
#  registry mainitain |resource to maintain   |resources ids with the same leading domain 
#  reguest permit     |resource to request    |registry value converted to list



## Scenario of registry maintaining, given testing example must include
# (1) a given validating resoure in domain path format
# (2) a given candidates list

## Ensure existence of resource id '/ds/retrain/*' and '/ds/retrain/cds'

def get_cids(type):    
    if type == 1:
        _clients = Account._get_resource_clients_all_info()
    if type == 2:
        _clients = Account._get_user_clients_all_info()
    _ids = [id for ix, id in _clients['CLIENT_ID'].items()]
    return _ids


def get_cid_exclude_test_cid(test_cid, type):
    rids = get_cids(type)
    if  test_cid in rids:  
        delete_account(test_rid, type)
    return get_cids(type)


test_rid = '/ds/retrain/abc'
rids = get_cid_exclude_test_cid(test_rid, type=1)
assert test_rid not in rids
assert '/ds/retrain' in rids
assert '/ds/retrain/cds' in rids
assert '/ds/retrain/*' in rids
assert Account.__search_best_match(_res=test_rid,candidates=rids) == '/ds/retrain/*'
assert Account.__search_best_match(_res=test_rid,candidates=rids) in Account._find_best_match_res(_res=test_rid)


test_rid = '/ds/retrain/cds/abc'
rids = get_cid_exclude_test_cid(test_rid, type=1)
assert test_rid not in rids
assert '/ds/retrain' in rids
assert '/ds/retrain/cds' in rids
assert '/ds/retrain/*' in rids
assert Account.__search_best_match(_res=test_rid,candidates=rids) == '/ds/retrain/cds'
assert Account.__search_best_match(_res=test_rid,candidates=rids) in Account._find_best_match_res(_res=test_rid)


test_uid = 'test_user'
test_reg1 = '/ds/retrain/cds,/ds/retrain/*'
Account._create_if_not_exist(client_id=test_uid, registry=test_reg1, type=2)
uid = Account(test_uid)
assert uid._registry == test_reg1
test_rid = '/ds/retrain/cds'
assert uid.__search_best_match(test_rid, uid.registry) == '/ds/retrain/cds'
test_rid = '/ds/retrain/cds/abc'
assert uid.__search_best_match(test_rid, uid.registry) == '/ds/retrain/cds'
test_rid = '/ds/retrain/abc'
assert uid.__search_best_match(test_rid, uid.registry) == '/ds/retrain/*'



# Scenario: the registry value has endwith '/*' but the request rid is in the exclude list '-/cds'
test_reg2 = '/ds/retrain/*'    # will set the new registry for the test user
get_cid_exclude_test_cid(test_cid=test_uid,type=2) # del the user if exist
Account._create_if_not_exist(client_id=test_uid, registry=test_reg2, type=2)
uid = Account(test_uid)
assert uid._registry == test_reg2
test_rid = '/ds/retrain/cds/abc'
bm = uid.__search_best_match(test_rid, uid.registry)
assert bm == '/ds/retrain/*'
rid = Account(bm,type=1)
subdomains = test_rid.removeprefix(bm.rstrip('/*'))
bm2 = Account.__search_best_match(subdomains,rid.registry)
if bm2.startswith('-'): f"{bm2} is a negative registry"

