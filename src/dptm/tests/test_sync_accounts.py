from dptm.accounts.sync_accounts import _sync_account, _context_name,  \
                    _source_data_dep_name, _target_data_dep_name, \
                    kubectx, apply_dep_from_template, copy_file_to_pod

from dprm.kubernetes.innocld import get_pods_by_dep_name
import os
                    
assert _context_name == 'ci-dev'
assert _source_data_dep_name == "dpamsidecar"
assert  _target_data_dep_name == 'postgres'
dep_name = _source_data_dep_name

assert apply_dep_from_template()
pod_ = get_pods_by_dep_name(kubectx, _source_data_dep_name) 
assert pod_[1][0]._metadata._labels['deploy'] == _source_data_dep_name
destination_path = os.path.join(os.getcwd(), "temp\\account.sqlite")    
copy_file_to_pod(destination_path=destination_path)
postgres_pods_ = get_pods_by_dep_name(kubectx, _target_data_dep_name) 
# return data from the get_pods_by_dep_name conatain (retun_status:Boolean, pod_items)
# Thus ..[0] is the 1st pod's info
# ..[0].metadata.name is the same name with the `kubectl get pods`
assert postgres_pods_[1][0].metadata.name.split("-")[0] == _target_data_dep_name

