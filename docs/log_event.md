# Log Event 

## Log Event Payload Spec

### Sample
```json
{
  "timestamp": "string",
  "event_type": "string",
  "actor": {
    "user_clientid": "string",
    "user_ad": "string",
    "ip": "string"
  },
  "target": {
    "service": "string",
    "resource": "string"
  },
  "action": "string",
  "outcome": "string",
  "context": {
    "user_agent": "string",
    "location": "string",
    "client_id": "string"
  },
  "metadata": {
    "request_id": "string",
    "session_id": "string",
    "custom_tags": "string"
  }
}
```

## Event Type

