from flask import Flask,request, json
from flask_restx import Api, Resource, fields, reqparse
from flask_sqlalchemy import SQLAlchemy 
from dsbase.tools.logger import Logger
from dsbase.tools.config_loader import ConfigLoader
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.parser import parse as parse_datetime
import os
from flask_cors import CORS

if "PYTHONPATH" not in os.environ.keys(): instance_path = os.path.join(os.getcwd(), "instance")
else:  instance_path = os.path.join(os.environ["PYTHONPATH"], "instance")

app = Flask(__name__, instance_path=instance_path)
CORS(app)
app.config.from_pyfile(os.path.join(instance_path,"flask.cfg"))
db_path = os.path.join(instance_path, 'events.db')
print(f"instance path is {instance_path}")
print(f"db path is {db_path}")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///"+db_path
#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////event.db" 
app.config["SQLALACEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

event_api = Api(app, version="1.0", title="Platform Evenet Logging API", description="API for logging platform events")
ns = event_api.namespace('Events', description = 'Platform Event Logging Operations')

tz = ZoneInfo("Asia/Taipei")
dt = datetime.now(tz)
print(f"Current time is {dt.isoformat()} on {tz} timezone")

# SQLAlchemy Model
class UnifiedEvent(db.Model):
    """
    version 0.1 an unified event model
    """    
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String, nullable=False)
    event_type = db.Column(db.String, nullable=False)
    actor = db.Column(db.Text)
    target = db.Column(db.Text)
    action = db.Column(db.String)
    outcome = db.Column(db.String)
    context = db.Column(db.Text)
    _metadata = db.Column(db.Text)
    
    # Decorated fields
    ## Log
    log_level = db.Column(db.String)
    ## Issue
    severity = db.Column(db.String)
    ## Alert
    critical = db.Column(db.Boolean)
    ## Incident
    status = db.Column(db.String)
    related_issue_id = db.Column(db.Integer)
    related_alert_id = db.Column(db.Integer)
    # Feedback
    related_event_id = db.Column(db.Integer)
    comment = db.Column(db.Text)    
    
    """def __init__(self, data):
        
        self.timestamp = data.get('timestamp', datetime.now(tz).isoformat())
        self.event_type = data.get('event_type')
        self.actor = json.dumps(data.get('actor', {}))
        self.target = json.dumps(data.get('target', {}))
        self.action = data.get('action')
        self.outcome = data.get('outcome')
        self.context = json.dumps(data.get('context', {}))
        self._metadata = json.dumps(data.get('_metadata', {}))
        self.user_ad = data.get("user_ad")
        
        # Decorated fields based on event type
        self.log_level = data.get('log_level')
        self.severity = data.get('severity')
        self.critical = data.get('critical')
        self.status = data.get('status')
        self.related_issue_id = data.get('related_issue_id')
        self.related_alert_id = data.get('related_alert_id')
        self.comment = data.get('comment')
        self.related_event_id = data.get('related_event_id')
      
       example use cases
        Log event
        `
        {
            "event_type": "log",
            "log_level": "INFO",
            "actor": {"clientid":"eng", "user_ad":"u123"},
            "target": {"service": "auth"},
            "action": {login},
            "outcome": "success"
        }`
        Issue event
        `
        {
            "event_type": "issue",
            "severity": "medium",
            "actor": {"clientid":"eng", "user_ad":"u234"},
            "target": {"resource":"/ds/ml/regression"},
            "action": "Unauthrozed",
            "outcome": "detected"
        }`
        Feedback event
        `
        {
            "event_type":"feedback",
            "comment":"Issue were solved after set registry value",
            "related_event_id": 52,
            "actor": {"clientid":"eng", "user_ad": "u234"},
            "action": "submit",
            "outcome": "accepted"
        }
        `
        """ 
        
# JSON models for documentation
actor_model = event_api.model('Actor', {
    'clientid': fields.String(required=True),
    'user_ad': fields.String(),
    'ip': fields.String(),
})

target_model = event_api.model('Target', {
    'service': fields.String(required=True),
    'resource': fields.String(required=True)
})

context_model = event_api.model('Context', {
    'user_agent': fields.String(),
    'location': fields.String()
})

metadata_model = event_api.model('Metadata',{
    'request_id': fields.String(),
    'session_id': fields.String(),
    'custom_tags': fields.String(),  
})

log_event_model = event_api.model('LogEvent', {
    'timestamp': fields.String(required=False),
    'event_type': fields.String(required=True, default="log",description="log, issue, alert, incident, feedback"),
    'actor': fields.Nested(actor_model),
    'target': fields.Nested(target_model),
    'action': fields.String(required=True),
    'outcome': fields.String(required=True),
    'context': fields.Nested(context_model),
    '_metadata': fields.Nested(metadata_model),
    'log_level': fields.String() })

issue_event_model = event_api.inherit("IssueEvent", log_event_model, { 
    'severity': fields.String(required=True)})

alert_event_model = event_api.inherit("AlertEvent", log_event_model, {
    'critical': fields.Boolean(required=False, description="Critical flag for alert")})

incident_event_model = event_api.inherit("IncidentEvent", log_event_model, {
    'status': fields.String(),
    'related_issue_id': fields.Integer(),
    'related_alert_id': fields.Integer()})

feedback_event_model = event_api.inherit("FeedbackEvent", log_event_model, {
    'comment': fields.String(),
    'related_event_id': fields.Integer()})

# API Endpoint

parser = reqparse.RequestParser()
parser.add_argument('event_type', type=str, required=False)
parser.add_argument('user_ad', type=str, required=False, help='User AD in actor.user_ad')
parser.add_argument('start', type=str, required=False, help='Start timestamp (inclusive)')
parser.add_argument('end', type=str, required=False, help='End timestamp (inclusive)')

@event_api.route('/events')
class EventList(Resource):
    @event_api.expect(parser)
    def get(self):
        """
        Retrieve events with optional filtering by event_type, user_ad, timestamp duration
        """
        args = parser.parse_args()
        query = UnifiedEvent.query
        
        if args['event_type']:
            query = query.filter_by(event_type=args['event_type'])
        if args['user_ad']:
            query = query.filter(UnifiedEvent.actor.like(f'%"user_ad": "{args["user_ad"]}"%'))
        if args['start']:
            start_dt = parse_datetime(args['start'])
            query = query.filter(UnifiedEvent.timestamp >= start_dt)
        if args['end']:
            end_dt = parse_datetime(args['end'])
            query = query.filter(UnifiedEvent.timestamp <= end_dt)
        
        events = UnifiedEvent.query.all()
        return {
            "events":
            [
                {
                    'id': e.id,
                    'event_type': e.event_type,
                    'timestamp': e.timestamp,
                    'actor': json.loads(e.actor or "{}"),
                    'target': json.loads(e.target or "{}"),
                    'action': e.action,
                    'outcome': e.outcome,
                    'context': json.loads(e.context or "{}"),
                    'metadata': json.loads(e._metadata or "{}"),
                    'log_level': e.log_level,
                    'severity': e.severity,
                    'critical': e.critical,
                    'status': e.status,
                    'related_issue_id': e.related_issue_id,
                    'related_alert_id': e.related_alert_id,
                    'comment': e.comment,
                    'related_event_id': e.related_event_id
                } for e in events
            ]}, 200


@event_api.route('/log')
class LogEvent(Resource):
    @event_api.expect(log_event_model)
    def post(self):
        """Log a structured event and store it in sql"""
        return save_event(request.json, "log")

@event_api.route('/issue')
class IssueEvent(Resource):
    @event_api.expect(issue_event_model)
    def post(self):
        """Log a structured event and store it in sql"""
        return save_event(request.json, "issue")
    

@event_api.route('/alert')
class AlertEvent(Resource):
    @event_api.expect(alert_event_model)
    def post(self):
        """Log a structured event and store it in sql"""
        return save_event(request.json, "alert")


@event_api.route('/incident')
class IncidentEvent(Resource):
    @event_api.expect(incident_event_model)
    def post(self):
        """Log a structured event and store it in sql"""
        return save_event(request.json, "incident")


@event_api.route('/feedback')
class FeedbackEvent(Resource):
    @event_api.expect(feedback_event_model)
    def post(self):
        """Log a structured event and store it in sql"""
        Logger.log(f"{request.json}")
        return save_event(request.json, "feedback")

    
def save_event(data, event_type):
    try:
        actor =  json.dumps(data.get("actor", {}), ensure_ascii=False)
    except Exception as e:
        Logger.log("Failed to serialize actor")
        return {"error": f"Invalid actor field : {str(e)}"}, 400
    try:
        target =  json.dumps(data.get("target", {}), ensure_ascii=False)
    except Exception as e:
        Logger.log("Failed to serialize target")
        return {"error": f"Invalid target field : {str(e)}"}, 400    
    try:
        context =  json.dumps(data.get("context", {}), ensure_ascii=False)
    except Exception as e:
        Logger.log("Failed to serialize context")
        return {"error": f"Invalid context field : {str(e)}"}, 400   
    try:
        _metadat =  json.dumps(data.get("_metadata", {}), ensure_ascii=False)
    except Exception as e:
        Logger.log("Failed to serialize _metadata")
        return {"error": f"Invalid _metadata field : {str(e)}"}, 400
    
    try:
        event = UnifiedEvent(
            event_type = event_type,
            timestamp = datetime.now(tz).isoformat(),
            actor = actor,
            target = target,
            action = data.get("action"),
            outcome = data.get("outcome"),
            context = context,
            _metadata = _metadat,
            log_level = data.get("log_level"),
            severity = data.get("severity"),
            critical = data.get("critical"),
            status = data.get("status"),
            related_issue_id = data.get("related_issue_id"),
            related_alert_id = data.get("related_alert_id"),
            comment = data.get("comment"),
            related_event_id = data.get("related_event_id")
        )
        db.session.add(event)
        db.session.commit()
        return {"message":f"{event_type.capitalize()} event logged", "id": event.id}, 201
    except Exception as e:
        db.session.rollback()
        return {"error": str(e)}, 400
    
def create_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':    
    app.run(host='0.0.0.0', port=8080)































































































































































































































































































































































