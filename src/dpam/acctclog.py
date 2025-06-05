from flask import request, json
from flask_restx import Api, Resource, fields
from flask_sqlalchemy import SQLAlchemy 
from dpam.tools.logger import Logger
from dpam.blueprint_create import create_app
from dpam.account_portal import cfg_path
from datetime import datetime, timedelta, timezone

app = create_app(cfg_path)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clogs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
acctclog_api = Api(app, version="1.0", title="Platform Logging API", description="API for logging platform events")
ns = acctclog_api.namespace('log', description = 'Event logging operations')

# Define UTC+8 timezone
tz_utc8 = timezone(timedelta(hours=8))

# SQLAlchemy Model
class LogEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String, nullable=False)
    event_type = db.Column(db.String, nullable=False)
    actor = db.Column(db.Text)
    target = db.Column(db.Text)
    action = db.Column(db.String)
    outcome = db.Column(db.String)
    context = db.Column(db.Text)
    _metadata = db.Column(db.Text)
    
    def __init__(self, data):
        self.timestamp = data.get('timestamp', datetime.now(tz_utc8).isoformat())
        self.event_type = data.get('event_type')
        self.actor = json.dumps(data.get('actor', {}))
        self.target = json.dumps(data.get('target', {}))
        self.action = data.get('action')
        self.outcome = data.get('outcome')
        self.context = json.dumps(data.get('context', {}))
        self.metadata = json.dumps(data.get('metadata', {}))
        
# JSON models for documentation
actor_model = acctclog_api.model('Actor', {
    'user_clientid': fields.String(required=True),
    'user_ad': fields.String(),
    'ip': fields.String(),
})

target_model = acctclog_api.model('Target', {
    'service': fields.String(required=True),
    'resource': fields.String(requied=True)
})

context_model = acctclog_api.model('Context', {
    'user_agent': fields.String(),
    'location': fields.String(),
    'client_id': fields.String()
})

metadata_model = acctclog_api.model('Metadata',{
    'request_id': fields.String(),
    'session_id': fields.String(),
    'custom_tags': fields.String(),  
})

event_model = acctclog_api.model('Event', {
    'timestamp': fields.String(required=False),
    'event_type': fields.String(required=True),
    'actor': fields.Nested(actor_model),
    'target': fields.Nested(target_model),
    'action': fields.String(required=True),
    'outcome': fields.String(required=True),
    'context': fields.Nested(context_model),
    'metadata': fields.Nested(metadata_model)
})

# API Endpoint
@ns.route('/event')
class EventLogger(Resource):
    @ns.expect(event_model)
    def post(self):
        """Log a structured event and store it in sql"""
        event = request.json
        if 'timestamp' not in event or not event['timestamp']:
            event['timestamp'] = datetime.now(tz_utc8).isoformat()
        log = LogEvent(event)
        db.session.add(log)
        db.session.commit()
        
        return {"message": "Event logged and posted"}, 201


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8070)































































































































































































































































































































































