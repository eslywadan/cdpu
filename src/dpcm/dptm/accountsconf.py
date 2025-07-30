# exporting the related configuration data 
from dpcm.dpcm_conf import __dpcm__

def sync_account_(operation, destination, filename='sync_accounts.yaml'):
    """ operation == [get,put] destination == [innocld, cds]
    example: sync_account_(operation="get", destination="cds") will get the default file from cds
    """
    cds_tsubpath = '/corpus/dptm/accounts'
    return __dpcm__(operation=operation, destination=destination, _cds_tsubpath=cds_tsubpath, _filename=filename)

