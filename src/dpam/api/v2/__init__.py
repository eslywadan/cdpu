
# src/dpam/api/v2/__init__.py
from flask import Blueprint, jsonify, request
from common.api.blueprints import create_versioned_blueprint, versioned_route
from dpam.db_access import select_accounts_for_admin

dpam_v2 = create_versioned_blueprint('v2', 'dpam')

@dpam_v2.route('/accounts', methods=['GET'])
def get_accounts_v2():
    """Get accounts - v2 format"""
    accounts = select_accounts_for_admin()
    
    # Transform to v2 format
    transformer = VersionTransformer()
    accounts_v2 = transformer.transform(accounts, 'v1', 'v2')
    
    return jsonify({
        'success': True,
        'data': accounts_v2,
        'version': 'v2',
        'timestamp': datetime.now().isoformat()
    })

@dpam_v2.route('/accounts/<client_id>', methods=['GET'])
def get_account_v2(client_id):
    """Get single account - v2 format with camelCase"""
    account = {
        'clientId': client_id,
        'userId': 'USER001',
        'createdAt': '2024-01-01T10:00:00Z',
        'permission': ['QUERY', 'DEBUG'],
        'registry': ['/ds', '/ml'],
        'apiVersion': 'v2'
    }
    return jsonify(account)