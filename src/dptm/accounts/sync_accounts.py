# Sync Task Description
# 1. Ensure environment ready and test all connections
# 2. Copy the source sqlite db file 
# 3. Load the account table in sqlite db file to postres
# 4. Check the consistency
# 5. remove intermedidate data

import io, tarfile, tempfile, os, base64
from dpcm import database_config
from bridge.load_account import Account
from kubernetes import stream
from dpcm.kubernetes.kubecontexts import KubeContexts # Get the Kubernetes object that can use its api
from dpcm.kubernetes.kubeconf import kubedep # implementation config
from dpcm.dptm.accountsconf import sync_account_
from dprm.kubernetes.innocld import apply_deployment_from_dic, get_pod_and_container_from_deployment
import urllib3
urllib3.disable_warnings()

# system sementic setting (3s)
_sync_account = sync_account_(operation="get", destination="innocld")
_context_name = _sync_account.get('context_name','ci-dev')
_source_data_dep_name = _sync_account.get('source_data_deployment_name', 'dpamsidecar')
_target_data_dep_name = _sync_account.get('target_data_deployment_name', 'postgres')

kubectx = KubeContexts(context_name=_context_name)

def apply_dep_from_template(dep_name=_source_data_dep_name):
    """
    1. Read the deployment file from the tempalte store
    2. Allowed to change the deployment name
    """
    _dep = kubedep(operation="get", destination="cds", context=_context_name, filename=f"{_source_data_dep_name}_deployment_template.yaml")
    # Modify required fields
    dep = _dep
    return apply_deployment_from_dic(kubectx=kubectx, dep_name=dep_name, _dep=dep)

def copy_file_to_pod(destination_path='',source_path='/app/ext/account.sqlite'):
    status, pod_name, container_name = get_pod_and_container_from_deployment(kubectx, _source_data_dep_name)
    if not status: return f"Given {_source_data_dep_name} has not the running container"
    try:
        resp = stream.stream(
            kubectx.corev1api.connect_get_namespaced_pod_exec, 
            name=pod_name,
            namespace=kubectx.namespace,
            container= container_name,
            command=['sh', '-c',
                     f'tar cf - -C {os.path.dirname(source_path)} {os.path.basename(source_path)} | base64'],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False
        )
        
        # Create a tempfile to store the tar data
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
            temp_tar_path = temp_file.name
            # Read the tar data from the pod
            base64_data = ""
            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    base64_data += resp.read_stdout()
                if resp.peek_stderr():
                    print(f"STDERR: {resp.read_stderr()}")
            base64_data = base64_data.strip()
            tar_data = base64.b64decode(base64_data)
            temp_file.write(tar_data)
            
        # Extract tar to detination path
        with tarfile.open(temp_tar_path, 'r') as tar:
            tar.extractall(path=os.path.dirname(destination_path))
            #Move the extracted file to the desired destinaion
            extracted_file = os.path.join(
                os.path.dirname(destination_path),
                os.path.basename(source_path)
            )
            
            if extracted_file != destination_path:
                os.rename(extracted_file, destination_path)
        
        os.unlink(temp_tar_path)
                
        print(f"File copied to {destination_path}")
    except Exception as e:
        print(f"Error copy file : {e}")
        raise
    
def copy_file_simple(source_path, destination_path):
    status, pod_name, container_name = get_pod_and_container_from_deployment(kubectx, _source_data_dep_name)
    if not status: return f"Given {_source_data_dep_name} has not the running container"
    try:
        resp = stream.stream(
            kubectx.corev1api.connect_get_namespaced_pod_exec, 
            name=pod_name,
            namespace=kubectx.namespace,
            container= container_name,
            command=['cat', source_path],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        # Write to local
        with open(destination_path, 'w') as f:
            f.write(resp)
        print(f"Successfully copied {source_path} from pods {pod_name} to destination path {destination_path}")
    except Exception as e:
        print(f"Error coping file with message {e}")
        raise    
    
def test_copy():
    from dptm.accounts.sync_accounts import kubectx, _source_data_dep_name
    from dptm.accounts.sync_accounts import get_pod_and_container_from_deployment
    from kubernetes import stream
    import tempfile, os
    destination_path='E:\\projects\\cdpu\\src'
    source_path='/app/ext/account.sqlite'
    status, pod_name, container_name = get_pod_and_container_from_deployment(kubectx, _source_data_dep_name)
    
        

def main():
    apply_deployment_from_dic()
    file_to_copy = ""
    remote_file_path = ""
    copy_file_to_pod(pod_name, file_to_copy, remote_file_path)    

