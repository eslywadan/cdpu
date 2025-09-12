# src/common/celery_app.py
from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure
from kombu import Exchange, Queue
import redis
from typing import Any, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CDPUCeleryApp:
    """Central Celery application for CDPU"""
    
    def __init__(self):
        self.app = None
        self.redis_client = None
        self.config = self._get_config()
        
    def _get_config(self) -> Dict:
        """Get Celery configuration"""
        return {
            'broker_url': 'redis://localhost:6379/2',
            'result_backend': 'redis://localhost:6379/3',
            'task_serializer': 'json',
            'accept_content': ['json'],
            'result_serializer': 'json',
            'timezone': 'UTC',
            'enable_utc': True,
            'task_track_started': True,
            'task_time_limit': 3600,  # 1 hour
            'task_soft_time_limit': 3300,  # 55 minutes
            'worker_prefetch_multiplier': 4,
            'worker_max_tasks_per_child': 1000,
            
            # Task routing
            'task_routes': {
                'dptm.tasks.sync.*': {'queue': 'sync'},
                'dptm.tasks.etl.*': {'queue': 'etl'},
                'dptm.tasks.scheduled.*': {'queue': 'scheduled'},
                'dptm.tasks.k8s.*': {'queue': 'kubernetes'},
                'dpam.tasks.*': {'queue': 'accounts'},
                'dpem.tasks.*': {'queue': 'events'},
                'dprm.tasks.*': {'queue': 'resources'}
            },
            
            # Queue configuration
            'task_queues': (
                Queue('default', Exchange('default'), routing_key='default'),
                Queue('sync', Exchange('sync'), routing_key='sync.#'),
                Queue('etl', Exchange('etl'), routing_key='etl.#'),
                Queue('scheduled', Exchange('scheduled'), routing_key='scheduled.#'),
                Queue('kubernetes', Exchange('kubernetes'), routing_key='k8s.#'),
                Queue('accounts', Exchange('accounts'), routing_key='accounts.#'),
                Queue('events', Exchange('events'), routing_key='events.#'),
                Queue('resources', Exchange('resources'), routing_key='resources.#'),
                Queue('priority', Exchange('priority'), routing_key='priority.#',
                      queue_arguments={'x-max-priority': 10})
            ),
            
            # Beat schedule for periodic tasks
            'beat_schedule': {
                'cleanup-old-events': {
                    'task': 'dpem.tasks.cleanup_old_events',
                    'schedule': 86400.0,  # Daily
                },
                'sync-accounts': {
                    'task': 'dptm.tasks.sync_accounts',
                    'schedule': 3600.0,  # Hourly
                },
                'check-resource-health': {
                    'task': 'dprm.tasks.check_resource_health',
                    'schedule': 300.0,  # Every 5 minutes
                }
            }
        }
    
    def create_app(self) -> Celery:
        """Create and configure Celery app"""
        self.app = Celery('cdpu')
        self.app.config_from_object(self.config)
        
        # Setup Redis connection
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=4,
            decode_responses=True
        )
        
        # Register signal handlers
        self._register_signals()
        
        return self.app
    
    def _register_signals(self):
        """Register Celery signal handlers"""
        
        @task_prerun.connect
        def task_prerun_handler(sender=None, task_id=None, task=None, 
                               args=None, kwargs=None, **kw):
            """Before task execution"""
            # Store task start time
            self.redis_client.hset(
                f"task:{task_id}",
                mapping={
                    'status': 'RUNNING',
                    'started_at': datetime.utcnow().isoformat(),
                    'task_name': task.name
                }
            )
            logger.info(f"Task {task.name} [{task_id}] started")
        
        @task_postrun.connect
        def task_postrun_handler(sender=None, task_id=None, task=None,
                                args=None, kwargs=None, retval=None, **kw):
            """After task execution"""
            # Update task completion
            self.redis_client.hset(
                f"task:{task_id}",
                mapping={
                    'status': 'SUCCESS',
                    'completed_at': datetime.utcnow().isoformat(),
                    'result': str(retval)[:1000]  # Limit result size
                }
            )
            self.redis_client.expire(f"task:{task_id}", 86400)  # Expire after 1 day
            logger.info(f"Task {task.name} [{task_id}] completed")
        
        @task_failure.connect
        def task_failure_handler(sender=None, task_id=None, exception=None,
                                args=None, kwargs=None, traceback=None, **kw):
            """On task failure"""
            # Record failure
            self.redis_client.hset(
                f"task:{task_id}",
                mapping={
                    'status': 'FAILURE',
                    'failed_at': datetime.utcnow().isoformat(),
                    'error': str(exception),
                    'traceback': str(traceback)[:5000]
                }
            )
            logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")

# Create global Celery app
celery_app = CDPUCeleryApp().create_app()