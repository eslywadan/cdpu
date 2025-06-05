import pytest
from flask import Flask
from acctapi import acctapi_bp, account_api

@pytest.fixture
def client():
    # Create a Flask app and register the blueprint for testing
    app = Flask(__name__)
    app.register_blueprint(acctapi_bp, url_prefix='/api')
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_validate_sso_token(client, mocker):
    # Mock validate_user.validate_user to simulate token validation
    mocker.patch('tools.validate_user.validate_user', return_value=('test_user', 'test_session_key'))

    # Simulate a GET request to /user with a valid Authorization header
    response = client.get('/api/user', headers={'Authorization': 'Bearer valid_token'})
    assert response.status_code == 200
    assert response.json == 'test_user'

    # Simulate a GET request to /user with an invalid Authorization header
    response = client.get('/api/user', headers={'Authorization': 'Bearer invalid_token'})
    assert response.status_code == 401
    assert 'Given token is not correct' in response.json['message']

def test_user_clients(client, mocker):
    # Mock validate_user.validate_user and db.select_accounts_for_owner
    mocker.patch('tools.validate_user.validate_user', return_value=('test_user', 'test_session_key'))
    mocker.patch('db_access.select_accounts_for_owner', return_value=['client1', 'client2'])

    # Simulate a GET request to /user/clients
    response = client.get('/api/user/clients', headers={'Authorization': 'Bearer valid_token'})
    assert response.status_code == 200
    assert response.json == ['client1', 'client2']

def test_user_clients_invalid_token(client, mocker):
    # Mock validate_user.validate_user to return None for invalid tokens
    mocker.patch('tools.validate_user.validate_user', return_value=(None, None))

    # Simulate a GET request to /user/clients with an invalid token
    response = client.get('/api/user/clients', headers={'Authorization': 'Bearer invalid_token'})
    assert response.status_code == 401
    assert 'Given token is not correct' in response.json['message']

def test_user_permits_client(client, mocker):
    # Mock validate_user.validate_user and db.select_accounts_registry_for_owner
    mocker.patch('tools.validate_user.validate_user', return_value=('test_user', 'test_session_key'))
    mocker.patch('db_access.select_accounts_registry_for_owner', return_value=[
        {'REGISTRY': '/ds/carux/apds', 'CLIENT_ID': 'client1'}
    ])
    mocker.patch('tools.request_handler.validate_ds_permission', return_value='Permit')

    # Simulate a GET request to /user/permits/client
    response = client.get('/api/user/permits/client', headers={'Authorization': 'Bearer valid_token'})
    assert response.status_code == 200
    assert response.json['clientid'] == ['client1']

def test_user_permits_client_no_permits(client, mocker):
    # Mock validate_user.validate_user and db.select_accounts_registry_for_owner
    mocker.patch('tools.validate_user.validate_user', return_value=('test_user', 'test_session_key'))
    mocker.patch('db_access.select_accounts_registry_for_owner', return_value=[])
    mocker.patch('tools.request_handler.validate_ds_permission', return_value='Deny')

    # Simulate a GET request to /user/permits/client
    response = client.get('/api/user/permits/client', headers={'Authorization': 'Bearer valid_token'})
    assert response.status_code == 200
    assert response.json['clientid'] == []

def test_get_apikey(client, mocker):
    # Mock validate_user.validate_user and tools.crypto.get_account_token
    mocker.patch('tools.validate_user.validate_user', return_value=('test_user', 'test_session_key'))
    mocker.patch('tools.crypto.get_account_token', return_value='test_apikey')

    # Simulate a GET request to /<client>/apikey
    response = client.get('/api/test_client/apikey', headers={'Authorization': 'Bearer valid_token'})
    assert response.status_code == 200
    assert response.json == 'test_apikey'