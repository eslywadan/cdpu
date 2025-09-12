# src/dptm/tasks/workflows.py
from celery import chain, group, chord, signature
from common.celery_app import celery_app
from typing import List, Dict, Any

class WorkflowBuilder:
    """Build complex workflows"""
    
    @staticmethod
    def create_etl_pipeline(source: str, target: str) -> chain:
        """Create ETL pipeline workflow"""
        
        workflow = chain(
            # Extract
            signature('dptm.tasks.extract_data', args=[source]),
            
            # Transform
            signature('dptm.tasks.transform_data'),
            
            # Validate
            signature('dptm.tasks.validate_data'),
            
            # Load
            signature('dptm.tasks.load_data', args=[target]),
            
            # Notify
            signature('dptm.tasks.send_notification')
        )
        
        return workflow
    
    @staticmethod
    def create_parallel_processing(tasks: List[Dict]) -> group:
        """Create parallel task execution"""
        
        signatures = [
            signature(task['name'], args=task.get('args', []), 
                     kwargs=task.get('kwargs', {}))
            for task in tasks
        ]
        
        return group(*signatures)
    
    @staticmethod
    def create_map_reduce(map_task: str, reduce_task: str, 
                         data_chunks: List[Any]) -> chord:
        """Create map-reduce workflow"""
        
        # Map phase - parallel processing
        map_signatures = [
            signature(map_task, args=[chunk])
            for chunk in data_chunks
        ]
        
        # Reduce phase - aggregate results
        reduce_signature = signature(reduce_task)
        
        return chord(group(*map_signatures))(reduce_signature)

@celery_app.task(name='dptm.tasks.run_workflow')
def run_workflow(workflow_definition: Dict) -> Dict:
    """Execute workflow from definition"""
    
    workflow_type = workflow_definition['type']
    
    if workflow_type == 'sequential':
        tasks = workflow_definition['tasks']
        workflow = chain(*[
            signature(task['name'], **task.get('options', {}))
            for task in tasks
        ])
    
    elif workflow_type == 'parallel':
        tasks = workflow_definition['tasks']
        workflow = group(*[
            signature(task['name'], **task.get('options', {}))
            for task in tasks
        ])
    
    elif workflow_type == 'dag':
        # Build DAG workflow
        workflow = build_dag_workflow(workflow_definition)
    
    else:
        raise ValueError(f"Unknown workflow type: {workflow_type}")
    
    # Execute workflow
    result = workflow.apply_async()
    
    return {
        'workflow_id': result.id,
        'status': 'started',
        'type': workflow_type
    }

def build_dag_workflow(definition: Dict):
    """Build DAG workflow from definition"""
    
    nodes = definition['nodes']
    edges = definition['edges']
    
    # Build task graph
    task_graph = {}
    for node in nodes:
        task_graph[node['id']] = {
            'signature': signature(node['task'], **node.get('options', {})),
            'dependencies': []
        }
    
    # Add dependencies
    for edge in edges:
        task_graph[edge['to']]['dependencies'].append(edge['from'])
    
    # Topological sort and build workflow
    return create_dag_chain(task_graph)