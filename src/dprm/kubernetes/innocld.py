from dpcm.kubernetes.kubecontexts import KubeContexts
from dpcm.kubernetes.kubeconf import kubedep
from kubernetes import client, utils, stream
from kubernetes.client.rest import ApiException
import time, os, base64, tempfile, tarfile,  shutil 


def check_existed_dep_by_name(kubectx:KubeContexts, dep_name):
    """ a kubectx is an object of KubeContexts assigned the designated context with config and api
        a dep_name is the name of a deployment 
    """
    try:
        dep = kubectx.apps_v1.read_namespaced_deployment(dep_name, kubectx.namespace)
        return True, dep
    except ApiException as e:
        if e.status == 404:
            return False, None
        else: raise RuntimeError(f"Failed to get the namespapced dep {dep_name} in namespace {kubectx.namespace}")
        
def del_dep_by_name_wait_pods_deleted(kubectx:KubeContexts, dep_name, timeout=90):
    """ a kubectx is an object of KubeContexts assigned the designated context with config and api
        a dep_name is the name of a deployment 
        -  it will wait by cheking the existency of related pods till all posd delteted
    """
    status, message = delete_dep_by_name(kubectx, dep_name)
    if status == 1: wait_pods_deleted(kubectx, dep_name, timeout=timeout)
    return f"{dep_name} in {kubectx.namespace} deleted status {status}: {message}"
    
def create_dep_from_dic(kubectx:KubeContexts, dep_dic):
    """ a kubectx is an object of KubeContexts assigned the designated context with config and api
        a dep_dic is the config of a deployment 
        -  it is a dictionry type by following the kubernetes' deployment format,
           Generally read a deployment by calling the kubedep function import from dpcm.kubernetes.kubeconf
        
        returning message
    """
    try:
        dep_name = dep_dic["metadata"]["name"]
        utils.create_from_dict(kubectx.api_client, dep_dic)
        status, _label_selector = get_label_selector(kubectx, dep_name) # Ensure the deployment is ready
        if status == 1: 
            return wait_for_pod_ready(kubectx=kubectx, label_selector=_label_selector)
        else: return _label_selector
            
    except ApiException as e:
        raise RuntimeError(f"Failed to create deployment from dic '{dep_dic}'")
    
def delete_dep_by_name(kubectx:KubeContexts, dep_name):
    # apps_v1 = client.AppsV1Api(kubectx.api_client)
    if check_existed_dep_by_name(kubectx=kubectx, dep_name=dep_name)[0]:
        try:
            kubectx.apps_v1.delete_namespaced_deployment(
                name=dep_name,
                namespace = kubectx.namespace,
                body=client.V1DeleteOptions(propagation_policy="Foreground")
            )
            print(f"Deleted existing deployment: {dep_name}")
            return 1, f"Deleted existing deployment: {dep_name}" 
        except ApiException as e:
            if e.status != 404:
                print(f"No existing deployment named {dep_name} found")
                return 0, f"No existing deployment named {dep_name} found"
            raise RuntimeError(f"Failed to delete deployment {e}")
    else: return 0, f"Has not the {dep_name} in {kubectx.namespace}"    

def wait_pods_deleted(kubectx:KubeContexts, dep_name, timeout=90):
    status_, label_selector_ = get_label_selector(kubectx, dep_name)
    start_time = time.time()
    while True and status_== 1:
        status, _ = get_pods_by_dep_label_selector(kubectx, label_selector_)
        if not status:
            print(f"All pods from deployment '{dep_name} have been deleted'")
            return
        if time.time()-start_time > timeout:
            raise TimeoutError(f"Timeout : Pods for deployment '{dep_name}' not del in {timeout} secs")
        time.sleep(2)

def get_pods_by_dep_name(kubectx:KubeContexts, dep_name):
    status, _label_selector = get_label_selector(kubectx, dep_name)
    if status ==1: return get_pods_by_dep_label_selector(kubectx, _label_selector)
    else: return _label_selector # If not 'status == 1' will get None from the label_selector either has not the deployment or 

def get_pods_by_dep_label_selector(kubectx:KubeContexts, label_selector):
    pods = kubectx.corev1api.list_namespaced_pod(namespace=kubectx.namespace, label_selector=label_selector)
    if not pods.items:
        return False, f"No pods found for lable_selector {label_selector} in namespace {kubectx.namespace}"
    return True, pods.items 

def get_pod_and_container_from_deployment(kubectx:KubeContexts, dep_name):
    status_, _ = check_existed_dep_by_name(kubectx, dep_name)
    if status_: 
        _status, pods = get_pods_by_dep_name(kubectx, dep_name)
        if _status: 
            pod = pods[0]
            pod_name = pod.metadata.name
            container_name = pod.spec.containers[0].name
            return True, pod_name, container_name
        else: return False, None, None, f"Given deployment {dep_name} has not running pod/container in namspace {kubectx.namespace}"
    else: return False, f"Given dep_name {dep_name} does not exist in namesapce {kubectx.namespace}"

def get_label_selector(kubectx:KubeContexts, dep_name):
    """
    If the given dep_name has deploymentm will return `1,label_selector`
    elif `0, $message' case when no deploment found by given dep_name
    elif '-1, $message' case when system error 
    """
    try:
        dep = kubectx.apps_v1.read_namespaced_deployment(name=dep_name, namespace=kubectx.namespace)
        label_selector = ",".join([f"{k}={v}" for k, v in dep.spec.selector.match_labels.items()])
        return 1, label_selector
    except ApiException as e:
        if e.status == 404:
            message = f" Deployment '{dep_name}' does not exist or already deleted"
            return 0, message
        else: return -1, RuntimeError(f"Failed to read deployment: {e}")

def wait_for_pod_ready(kubectx:KubeContexts, label_selector ,timeout=90):
    """
    Waits for a pod with the given label_selector (by default the _deploy_label_key) 
    to be in 'Running' state within the given timeout
    """
    start_time = time.time()
    while True:
        try:
            status, pods = get_pods_by_dep_label_selector(kubectx, label_selector)
        except ApiException as e: 
            raise RuntimeError(f"Failed to query pods {e}")
        
        if not status: return None
        for pod in pods:
            if pod.status.phase == "Running":
                for cond in pod.status.conditions:
                    if cond.type == "Ready" and cond.status == "True":
                        pod_name = pod.metadata.name
                        print(f" Pod '{pod_name}' is running")
                        return pod_name
        
        if time.time() -start_time > timeout: 
            raise TimeoutError(f"Timeout: No pods with lable '{label_selector}' reached 'Running' status within {timeout} seconds")
        time.sleep(2)        
         
def apply_deployment_from_dic(kubectx:KubeContexts,dep_name,_dep):
    # Modify required fields
    dep = _dep
    dep["metadata"]["name"] = dep_name
    dep['metadata']['labels']['deploy'] = dep_name
    dep['spec']['template']['spec']['containers'][0]['name'] = dep_name
    dep['spec']['template']['metadata']['labels']['deploy'] = dep_name
    dep['spec']['selector']['matchLabels']['deploy'] = dep_name
    
    del_dep_by_name_wait_pods_deleted(kubectx, dep_name)
    create_dep_from_dic(kubectx, dep)
    return dep

"""
Utility functions
exec_copy for general file copy, exec_copy_simple for text file copy
"""

def exec_copy(kubectx:KubeContexts, _source_data_dep_name, source_path, destination_path):
    """
    Used for general files copy, 
    Copy from a given source data by its deployment name and file path, to the assigned destination path
    """
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
        
        base64_data = ""
        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                base64_data += resp.read_stdout()
            if resp.peek_stderr():
                print(f"STDERR: {resp.read_stderr()}")
        resp.close()  # Close the stream

        base64_data = base64_data.strip()
        tar_data = base64.b64decode(base64_data)
    
        # Create a tempfile to store the tar data
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
            temp_tar_path = temp_file.name
            # Read the tar data from the pod
            temp_file.write(tar_data)
            
        # Extract tar to detination path
        with tarfile.open(temp_tar_path, 'r') as tar:
            member = tar.getmembers()[0]
            # Extract to a temporary location
            extracted_temp = os.path.join(os.path.dirname(destination_path), member.name)
            # Overwrite destination file
            if os.path.exists(destination_path):
                os.remove(destination_path)
            tar.extract(member, path=os.path.dirname(destination_path))
            shutil.move(extracted_temp, destination_path)
        
        os.unlink(temp_tar_path)
                
        print(f"File copied to {destination_path}")
    except Exception as e:
        print(f"Error copy file : {e}")
        raise
    
def copy_file_simple(kubectx:KubeContexts, _source_data_dep_name, source_path, destination_path):
    """
    used for text files copy
    """
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