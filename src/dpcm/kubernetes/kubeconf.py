# dpcm - config data : kubeconfig data for innocloud
# file path @dpcm.corpus 'dpcm/corpus/kubernetes/kubeconfig_innocld.yaml'
# archive file @cds clientid='dpcm' archive path 'dpcm/corpus/kubernetes/kubeconfig_innocld.yaml'
from dpcm.dpcm_conf import __dpcm__

def kubeconfig(operation, destination, filename='kubeconfig_innocld.yaml'):
    """ operation == [get,put] destination == [innocld, cds]
    example: kubeconfig(operation="get", destination="cds") will get the default file from cds
    """
    cds_tsubpath = '/corpus/kubernetes'
    return __dpcm__(operation=operation, destination=destination, _cds_tsubpath=cds_tsubpath, _filename=filename)

def kubedep(operation, destination, context='ci-dev',filename='dpam_deployment_template.yaml'):
    """ operation == [get,put] destination == [innocld, cds], 
        detination argument indicate where the deployment file is sourced
    """
    cds_tsubpath = f'/corpus/kubernetes/deployment/{context}'
    return __dpcm__(operation=operation, destination=destination, _cds_tsubpath=cds_tsubpath, _filename=filename)
