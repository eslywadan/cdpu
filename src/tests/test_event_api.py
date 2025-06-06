import json
from datetime import datetime

def test_log_event(client):
    payload = {
        "actor": {"clientid":"eng","user_ad":"qs.chou", "ip":""},
        "target": {"service":"","resource":"https://mlplat.cminl.oa/"},
        "context": {"user_agent":"Chrome","location":"TN"},
        "action": "login",
        "outcome": "success",
        "log_level": "INFO"
    }
    response = client.post("/events/", json=payload)
    assert response.status_code == 201 
    
    payload = {
        "actor": {"clientid":"eng","user_ad":"qs.chou", "ip":""},
        "target": {"service":"","resource":"https://mlplat.cminl.oa/"},
        "context": {"user_agent":"Chrome","location":"TN"},
        "action": "logout",
        "outcome": "success",
        "log_level": "INFO"
    }
    response = client.post("/events/", json=payload)
    assert response.status_code == 201
    
def test_issue_event(client):
    payload = {
        "event_type": "issue",
        "actor": {"clientid":"eng","user_ad":"qs.chou", "ip":""},
        "target": {"service":"","resource":"https://mlplat.cminl.oa/"},
        "context": {"user_agent":"Chrome","location":"TN"},
        "action": "report",
        "outcome": "notified",
        "severity": "medium"
    }
    response = client.post("")
    assert response.status_code == 201
    
def test_alert_event(client):
    payload = {
        "event_type": "alert",
        "actor": {"clientid":"system_alert","user_ad":"", "ip":""},
        "target": {"service":"mapp","resource":""},
        "context": {"user_agent":"metric_proxy","location":"TN"},
        "action": "send",
        "outcome": "alerted",
        "_metadata": {"request_id": "abc123"},
        "critical": True
    }
    response = client.post("")
    assert response.status_code == 201
        
    
def test_incident_event(client):
    payload = {
        "event_type": "incident",
        "actor": {"clientid":"system_incident","user_ad":"", "ip":""},
        "target": {"service":"/apikey","resource":""},
        "context": {"user_agent":"","location":"TN"},
        "action": "mitigation",
        "outcome": "in-progress",
        "_metadata": {},
        "status": "ongoing",
        "related_issue_id": 1,
        "related_alert_id": 2
    }
    response = client.post("")
    assert response.status_code == 201
    
def test_feedback_event(client):
    
    payload = {
        "event_type": "feedback",
        "actor": {"clientid":"apds","user_ad":"qs.chou", "ip":""},
        "target": {"service":"/ml/regression","resource":""},
        "context": {"user_agent":"","location":"TN"},
        "action": "comment",
        "outcome": "received",
        "_metadata": {},
        "related_event_id": 3,
        "comment": "Issue is resolved"
    }
    response = client.post("")
    assert response.status_code == 201
    