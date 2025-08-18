# Sync Task Description
# 1. Ensure environment ready and test all connections
# 2. Copy the source sqlite db file 
# 3. Load the account table in sqlite db file to postres
# 4. Check the consistency
# 5. remove intermedidate data

import shutil, tarfile, tempfile, os, base64
from dpcm import database_config
from bridge.load_account import Account
from kubernetes import stream
from dpcm.kubernetes.kubecontexts import KubeContexts # Get the Kubernetes object that can use its api
from dpcm.kubernetes.kubeconf import kubedep # implementation config
from dpcm.dptm.accountsconf import sync_account_
from dprm.kubernetes.innocld import apply_deployment_from_dic, get_pod_and_container_from_deployment, exec_copy
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
    return exec_copy(kubectx=kubectx, _source_data_dep_name=_source_data_dep_name, source_path=source_path,destination_path=destination_path)

def main():
    apply_deployment_from_dic()
    copy_file_to_pod(destination_path='',source_path='/app/ext/account.sqlite')    
