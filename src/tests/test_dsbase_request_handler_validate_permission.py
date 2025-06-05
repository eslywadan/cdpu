from dsbase.tools.request_handler import validate_request_reg_permit, validate_permission, cate_service

# Test the cate_service

assert cate_service('http://10.53.200.183:34675/ds/retrain/')["serviceType"] == 'retrain'

