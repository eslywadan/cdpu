from flask import Flask,request
from flask_restx import Namespace, Resource, fields, Api
from flask_sqlalchemy import SQLAlchemy 
from dsbase.tools.logger import Logger
from memory.agent_memory import log_resource_memory
from datetime import datetime
from zoneinfo import ZoneInfo
import os

if "PYTHONPATH" not in os.environ.keys(): instance_path = os.path.join(os.getcwd(), "instance")
else:  instance_path = os.path.join(os.environ["PYTHONPATH"], "instance")

app = Flask(__name__, instance_path=instance_path)
app.config.from_pyfile(os.path.join(instance_path,"flask.cfg"))
db_path = os.path.join(instance_path, 'resources.db')
print(f"instance path is {instance_path}")
print(f"db path is {db_path}")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///"+db_path
app.config["SQLALACEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

resource_ns = Namespace('resources', description = 'Resource Managenement')
resource_api = Api(app, version="1.0", title="Platform Resource API", description="API for registering, get, and managing resources at platform")
resource_api.add_namespace(resource_ns, path = '/resource')

tz = ZoneInfo("Asia/Taipei")
dt = datetime.now(tz)
print(f"Current time is {dt.isoformat()} on {tz} timezone")

# SQLAlchemy Model

class _Resources(db.Model):
    
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    type = db.Column(db.String(50), nullable = False)
    description = db.Column(db.Text)
    _metadata = db.Column(db.JSON) # Flexible Structure for different type
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now()) 


resource_model = resource_api.model(
    'Resource', {
        'id': fields.Integer(readonly=True),
        'name': fields.String(required=True, description='Resource name'),
        'type': fields.String(required=True, description='Type of resource: compute, storage, service'),
        'description': fields.String(),
        '_metadata': fields.Raw(description='Flexible metadata depenging on type'),
        'create_at': fields.DateTime(readonly=True),
        'update_at': fields.DateTime(readonly=True)
    }
)

@resource_ns.route('/')
class ResourceList(Resource):
    @resource_api.marshal_list_with(resource_model)
    def get(self):
        """List all resources"""
        return _Resources.query.all()
    
    @resource_api.expect(resource_model)
    @resource_api.marshal_with(resource_model, code=201)
    def post(self):
        """Create a new resource
        """
        data = request.json
        new_resource = _Resources(
            name = data['name'],
            type = data['type'],
            description = data.get('description'),
            _metadata = data.get('_metadata', {})
        )
        db.session.add(new_resource)
        db.session.commit()
        
        # Optional record to agentic memory
        from memory.agent_memory import log_resource_memory
        log_resource_memory(new_resource)
        
        return new_resource, 201

@resource_ns.route('/<int:id>')
@resource_ns.response(404, 'Resource not Found')
class ResourceItem(Resource):   # inherited from the Resouce class import from flask_restx
    @resource_ns.marshal_with(resource_model)
    def get(self, id):
        """Get a single resource"""
        return _Resources.query.get_or_404(id)

    @resource_ns.expect(resource_model)
    @resource_ns.marshal_with(resource_model)
    def put(self, id):
        """Updata a resource"""
        resource = _Resources.query.get_or_404(id)
        data = request.json
        resource.name = data['name']
        resource.type = data['type']
        resource.description = data.get('description')
        resource._metadata = data.get('_metadata', {})
        resource.update_at = datetime.now()
        db.session.commit()
        
        log_resource_memory(resource)
        
        return resource
    
    def delete(self, id):
        """Delete a resource"""
        resource = _Resources.query.get_or_404(id)
        if not resource:
            return {"message": "Resource Not Found"}, 404
        db.session.delete(resource)
        db.session.commit()
        
        # Flag memory as deleted in Redis
        log_resource_memory(resource, deleted=True)
        return {'message': 'Deleted'}, 204
    

def create_db():
    with app.app_context():
        db.create_all()
        
if __name__ == '__main__':    
    app.run(host='0.0.0.0', port=8080)