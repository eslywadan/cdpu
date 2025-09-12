# src/dpam/api/v1/__init__.py
from flask import Blueprint, jsonify, request
from common.api.blueprints import create_versioned_blueprint, versioned_route
from dpam.db_access import select_accounts_for_admin

# Create v1 blueprint for DPAM
dpam_v1 = create_versioned_blueprint('v1', 'dpam')

@dpam_v1.route('/accounts', methods=['GET'])
@versioned_route(['v1', 'v2'])
def get_accounts():
    """Get accounts - v1 format"""
    accounts = select_accounts_for_admin()
    return jsonify({
        'success': True,
        'data': accounts,
        'version': 'v1'
    })

@dpam_v1.route('/accounts/<client_id>', methods=['GET'])
def get_account(client_id):
    """Get single account - v1 format"""
    # Original format with underscores
    account = {
        'client_id': client_id,
        'user_id': 'USER001',
        'create_dttm': '2024-01-01 10:00:00',
        'permission': 'QUERY|DEBUG',
        'registry': '/ds,/ml'
    }
    return jsonify(account)
