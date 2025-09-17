from dpem.event_api import app, UnifiedEvent
from sqlalchemy import or_, and_
from typing import Union, List, Optional
from datetime import datetime
import json
import pandas as pd

def query_events(uad_list: Union[str, List[str]],
                 event_type: Union[str, List[str]] = None,
                 timestamp_start: Optional[datetime] = None,
                 timestamp_end: Optional[datetime] = None,
                 timestamp_exact: Optional[datetime] = None):
    """
    Filter events by multiple user_ad values (database-agnostic) with event_type
    and timestamp filtering 
    
    Args:
        uad_list: List of user_ad values or single string
        event_type: Sigle event type or list of event types from  ['log', 'issue', 'incident', 'feedback']
        timestamp_start: Start datetime for timestamp range filtering (inclusive)
        timestamp_end: End dateitme for timestamp range filtering (inclusive)
        timestamp_exact: Exact timestamppp to match (Overrides start/end if provided)
    
    Returns:
        List of events matching the specified criteria
    """
    with app.app_context():
        query = UnifiedEvent.query
        # Handle both single string and list inputs
        if isinstance(uad_list, str):
            uad_list = [uad_list]
        # Remove empty strings and None values
        uad_list = [uad for uad in uad_list if uad]
        if not uad_list:
            return []
        # Build OR conditions for each UAD
        like_conditions = [
            UnifiedEvent.actor.like(f'%"user_ad": "{uad}"%')
            for uad in uad_list
        ]
        query = query.filter(or_(*like_conditions))
        
        # Handle event_type filtering
        if event_type is not None:
                # validate event types
                valid_event_type = ["log", "issue", "alert", "incident","feedback"]
                
                if isinstance(event_type, str):
                    event_type = [event_type]
                    
                # validate each event type
                invalid_types = [et for et in event_type if et not in valid_event_type]
                if invalid_types:
                    raise ValueError(f"Invalid event_type(s): {invalid_types},"
                                     f"Valid types are: {valid_event_type}")
                # Apply event_type filter
                if len(event_type) == 1:
                    query = query.filter(UnifiedEvent.event_type == event_type[0])
                else:
                    query = query.filter(UnifiedEvent.event_type.in_(event_type))
        
        # Handle timestamp filtering        
        if timestamp_exact is not None:
            # Exact timestamp match
            query = query.filter(UnifiedEvent.timestamp == timestamp_exact)
        
        else:
            # Range-based timestamp filtering
            if timestamp_start is not None:
                query = query.filter(UnifiedEvent.timestamp >= timestamp_start)
            
            if timestamp_end is not None:
                query = query.filter(UnifiedEvent.timestamp <= timestamp_end)
        
        events = query.all()
    
    return events

def get_log_events_uads(uad_list: Union[str, List[str]],outputfmt='csv'):
    events = query_events(uad_list=uad_list, event_type=['log'])
    if events == []: return None
    else:
        data = {
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
            ]}
        df = pd.json_normalize(data['events'])
        df.to_csv("events.csv", index=False, encoding='utf-8')
        return df