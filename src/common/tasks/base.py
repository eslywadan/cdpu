# src/common/tasks/base.py
from celery import Task
from typing import Any, Dict, Optional
import logging
from abc import abstractmethod
import traceback

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """Base task with common functionality"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 5}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def __init__(self):
        super().__init__()
        self.task_metadata = {}
    
    def before_start(self, task_id, args, kwargs):
        """Called before task execution"""
        logger.info(f"Starting task {self.name} with ID {task_id}")
        self.task_metadata['start_time'] = datetime.utcnow()
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on successful execution"""
        duration = datetime.utcnow() - self.task_metadata.get('start_time', datetime.utcnow())
        logger.info(f"Task {self.name} completed in {duration.total_seconds()}s")
        
        # Emit success event
        self._emit_event('task.completed', {
            'task_id': task_id,
            'task_name': self.name,
            'duration': duration.total_seconds(),
            'result': retval
        })
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f"Task {self.name} failed: {exc}")
        
        # Emit failure event
        self._emit_event('task.failed', {
            'task_id': task_id,
            'task_name': self.name,
            'error': str(exc),
            'traceback': traceback.format_exc()
        })
    
    def _emit_event(self, event_type: str, data: Dict):
        """Emit task event to message bus"""
        try:
            from common.messaging.redis_streams import RedisStreamBus, Message
            bus = RedisStreamBus()
            message = Message.create(
                topic='task_events',
                event_type=event_type,
                payload=data
            )
            bus.publish(message)
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
    
    @abstractmethod
    def run(self, *args, **kwargs):
        """Task implementation"""
        raise NotImplementedError

class KubernetesTask(BaseTask):
    """Base task for Kubernetes operations"""
    
    def __init__(self):
        super().__init__()
        self.kube_client = None
    
    def _get_kube_client(self):
        """Get Kubernetes client"""
        if not self.kube_client:
            from kubernetes import client, config
            config.load_incluster_config()  # For in-cluster execution
            self.kube_client = client
        return self.kube_client
    
    def create_job(self, job_spec: Dict) -> str:
        """Create Kubernetes job"""
        client = self._get_kube_client()
        batch_v1 = client.BatchV1Api()
        
        job = batch_v1.create_namespaced_job(
            namespace=job_spec.get('namespace', 'default'),
            body=job_spec['body']
        )
        
        return job.metadata.name
    
    def get_job_status(self, job_name: str, namespace: str = 'default') -> Dict:
        """Get job status"""
        client = self._get_kube_client()
        batch_v1 = client.BatchV1Api()
        
        job = batch_v1.read_namespaced_job_status(
            name=job_name,
            namespace=namespace
        )
        
        return {
            'active': job.status.active,
            'succeeded': job.status.succeeded,
            'failed': job.status.failed,
            'conditions': job.status.conditions
        }

class DataPipelineTask(BaseTask):
    """Base task for data pipeline operations"""
    
    def __init__(self):
        super().__init__()
        self.checkpoint_enabled = True
        self.checkpoint_key = None
    
    def get_checkpoint(self) -> Optional[Dict]:
        """Get task checkpoint from Redis"""
        if not self.checkpoint_key:
            return None
        
        from common.celery_app import celery_app
        data = celery_app.redis_client.get(f"checkpoint:{self.checkpoint_key}")
        return json.loads(data) if data else None
    
    def save_checkpoint(self, data: Dict):
        """Save task checkpoint"""
        if not self.checkpoint_key:
            return
        
        from common.celery_app import celery_app
        celery_app.redis_client.set(
            f"checkpoint:{self.checkpoint_key}",
            json.dumps(data),
            ex=86400  # Expire after 1 day
        )
    
    def clear_checkpoint(self):
        """Clear task checkpoint"""
        if not self.checkpoint_key:
            return
        
        from common.celery_app import celery_app
        celery_app.redis_client.delete(f"checkpoint:{self.checkpoint_key}")