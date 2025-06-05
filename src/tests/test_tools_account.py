from dpam.tools.account_util import *
# Test transform table
init_account_table()

validate_base_groups()
validate_base_roles()
validate_typical_users()
validate_resource_clients()
validate_group_clients()
validate_role_clients()
validate_user_clients()

test_find_best_match_res()