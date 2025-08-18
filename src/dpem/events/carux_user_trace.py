from dpem.event_api import app, UnifiedEvent

def filter_user_ad(uad):
    with app.app_context():
        query = UnifiedEvent.query
        query = query.filter(UnifiedEvent.actor.like(f'%"user_ad": "{uad}"%'))
        events = query.all()
    
    return events