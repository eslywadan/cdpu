# src/dptm/tasks/sync_tasks.py
from common.celery_app import celery_app
from common.tasks.base import DataPipelineTask
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime

@celery_app.task(base=DataPipelineTask, name='dptm.tasks.sync_accounts')
class SyncAccountsTask(DataPipelineTask):
    """Sync accounts from SQLite to PostgreSQL"""
    
    def run(self, source_config: Dict, target_config: Dict, 
            batch_size: int = 1000) -> Dict:
        """
        Execute account synchronization
        
        Args:
            source_config: Source database configuration
            target_config: Target database configuration
            batch_size: Batch size for processing
        """
        
        self.checkpoint_key = f"sync_accounts_{datetime.utcnow().date()}"
        
        # Get checkpoint
        checkpoint = self.get_checkpoint()
        start_offset = checkpoint.get('offset', 0) if checkpoint else 0
        
        try:
            # Extract from source
            source_data = self._extract_data(source_config, start_offset, batch_size)
            
            # Transform data
            transformed_data = self._transform_data(source_data)
            
            # Load to target
            loaded_count = self._load_data(target_config, transformed_data)
            
            # Update checkpoint
            self.save_checkpoint({'offset': start_offset + loaded_count})
            
            # If more data exists, chain next task
            if len(source_data) == batch_size:
                self.apply_async(
                    args=[source_config, target_config, batch_size],
                    countdown=5
                )
            else:
                # Clear checkpoint on completion
                self.clear_checkpoint()
            
            return {
                'status': 'success',
                'records_processed': loaded_count,
                'batch_complete': len(source_data) < batch_size
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise
    
    def _extract_data(self, config: Dict, offset: int, limit: int) -> pd.DataFrame:
        """Extract data from source"""
        import sqlite3
        
        conn = sqlite3.connect(config['database'])
        query = f"""
            SELECT * FROM account 
            LIMIT {limit} OFFSET {offset}
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def _transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform data"""
        # Add transformation logic
        df['synced_at'] = datetime.utcnow()
        df['source'] = 'sqlite'
        
        return df
    
    def _load_data(self, config: Dict, df: pd.DataFrame) -> int:
        """Load data to target"""
        from sqlalchemy import create_engine
        
        engine = create_engine(config['connection_string'])
        df.to_sql(
            'account',
            engine,
            if_exists='append',
            index=False,
            method='multi'
        )
        
        return len(df)

@celery_app.task(base=KubernetesTask, name='dptm.tasks.k8s.run_job')
class RunKubernetesJobTask(KubernetesTask):
    """Run a Kubernetes job"""
    
    def run(self, job_name: str, image: str, command: List[str],
            namespace: str = 'default', **kwargs) -> Dict:
        """
        Run Kubernetes job
        
        Args:
            job_name: Name of the job
            image: Container image
            command: Command to run
            namespace: Kubernetes namespace
        """
        
        from kubernetes import client
        
        # Create job specification
        job_spec = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=job_name),
            spec=client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=job_name,
                                image=image,
                                command=command,
                                resources=client.V1ResourceRequirements(
                                    limits={"memory": "1Gi", "cpu": "500m"},
                                    requests={"memory": "256Mi", "cpu": "100m"}
                                )
                            )
                        ],
                        restart_policy="Never"
                    )
                ),
                backoff_limit=3
            )
        )
        
        # Create job
        job_id = self.create_job({
            'namespace': namespace,
            'body': job_spec
        })
        
        # Monitor job
        return self._monitor_job(job_id, namespace)
    
    def _monitor_job(self, job_name: str, namespace: str) -> Dict:
        """Monitor job execution"""
        import time
        
        max_wait = 3600  # 1 hour
        check_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            status = self.get_job_status(job_name, namespace)
            
            if status['succeeded']:
                return {'status': 'completed', 'job_name': job_name}
            elif status['failed']:
                raise Exception(f"Job {job_name} failed")
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        raise TimeoutError(f"Job {job_name} timed out")