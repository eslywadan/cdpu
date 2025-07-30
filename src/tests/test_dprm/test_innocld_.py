from dprm.kubernetes.innocld import check_existed_dep_by_name, del_dep_by_name_wait_pods_deleted \
    , create_dep_from_dic, delete_dep_by_name, wait_pods_deleted, get_pods_by_dep_name \
        , get_pods_by_dep_label_selector, get_label_selector, wait_for_pod_ready, get_pod_and_container_from_deployment
    
from dpcm.kubernetes.kubecontexts import KubeContexts
from dpcm.kubernetes.kubeconf import kubedep
import urllib3
urllib3.disable_warnings()


kubectx = KubeContexts(context_name='ci-dev')
dep_name = 'postgres'
# To get the 'label_selector'
label_selector = get_label_selector(kubectx,dep_name) 
assert label_selector
pods_ = get_pods_by_dep_label_selector(kubectx, label_selector)
_pods = get_pods_by_dep_name(kubectx, dep_name)
assert pods_ == _pods
pod = pods_
pod_name = pod[0].metadata.name
assert pod_name.split("-")[0] == dep_name

get_pod_and_container_from_deployment(kubectx, dep_name)