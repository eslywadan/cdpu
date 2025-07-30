# Test Sync Account

## Step 1 kubernetes api
from dpcm.kubernetes.kubecontexts import KubeContexts

## Sync_account
## Test to get the deployment file and verify the image name
## use kubedep to test the __dpcm__ function
## __dpcm__  
## Redundant policy: (Archive to cds policy)
##        1. case when get none from innocld will try to fetch from cds else 'file not found'
##        2. case when get none from cds at the first time, will try to upload from innocld, and do the 2nd try. 
##        3. case when get from inncld successfully, will archive one copy to cds
## Test Scenario: 

image_name = 'irepocld.cminl.oa/datastudio-ci-dev/cdpu-account:v02'

from dptm.accounts.sync_accounts import _context_name, \
    _source_data_dep_name, kubedep,  kubectx
    
from dprm.kubernetes.innocld import \
del_dep_by_name_wait_pods_deleted, create_dep_from_dic, wait_for_pod_ready, get_label_selector, check_existed_dep_by_name

dep_innocld = kubedep(operation="get", destination="innocld", context=_context_name, filename=f"{_source_data_dep_name}_deployment_template.yaml")
assert dep_innocld['spec']['template']['spec']['containers'][0]['image'] == image_name
dep_cds = kubedep(operation="get", destination="cds", context=_context_name, filename=f"{_source_data_dep_name}_deployment_template.yaml")
assert dep_innocld['spec']['template']['spec']['containers'][0]['image'] == image_name

del_dep_by_name_wait_pods_deleted(kubectx=kubectx,dep_name=_source_data_dep_name)
dep = dep_cds
dep["metadata"]["name"] = _source_data_dep_name
dep['metadata']['labels']['deploy'] = _source_data_dep_name
dep['spec']['template']['spec']['containers'][0]['name'] = _source_data_dep_name
dep['spec']['template']['metadata']['labels']['deploy'] = _source_data_dep_name
dep['spec']['selector']['matchLabels']['deploy'] = _source_data_dep_name

create_dep_from_dic(kubectx, dep)
label_selector=get_label_selector(kubectx=kubectx,dep_name=_source_data_dep_name)
assert wait_for_pod_ready(kubectx=kubectx, label_selector=label_selector)

del_dep_by_name_wait_pods_deleted(kubectx=kubectx,dep_name=_source_data_dep_name)

assert not check_existed_dep_by_name(kubectx=kubectx, dep_name=_source_data_dep_name)