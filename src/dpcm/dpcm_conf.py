import os,yaml

def __dpcm__(operation, destination, _cds_tsubpath, _filename):
    """ operation == [get,put] destination == [innocld, cds]
    
    General function to get the corpus doc
    Redundant policy: (Archive to cds policy)
        1. case when get none from innocld will try to fetch from cds
        2. case when get none from cds at the first time, will try to upload from innocld, and do the 2nd try. 
        3. case when get from inncld successfully, will archive one copy to cds
    """
    clientid = 'dpcm'
    cds_tsubpath = _cds_tsubpath # cds_tsubpath is generally the same with innocld's path
    objname = _filename
    filepath = f'{clientid}{cds_tsubpath}/{_filename}'
    if operation == "get" and destination == "cds": return get_from_cds(filepath=filepath, objname=objname, cds_tsubpath=cds_tsubpath)
    if operation == "get" and destination == "innocld": return get_from_innocld(filepath=filepath, objname=objname, cds_tsubpath=cds_tsubpath)
    if operation == "put" and destination == "cds": return upload_to_cds(filepath=filepath, objname=objname, cds_tsubpath=cds_tsubpath)

def get_from_innocld(filepath, objname, cds_tsubpath, tryCdsOnNone=True, sync_cds=True): 
    if os.path.exists(filepath):
        if sync_cds: upload_to_cds(filepath=filepath,objname=objname, cds_tsubpath=cds_tsubpath)
        with open(filepath) as file:
            return yaml.safe_load(file)
    else: 
        if tryCdsOnNone: get_from_cds(filepath=filepath, objname=objname, cds_tsubpath=cds_tsubpath, tryInnocldOnNone=False)
        else: raise FileNotFoundError(f"Given filepath '{filepath}', filename '{objname}' not found")
    
def get_from_cds(filepath, objname, cds_tsubpath, tryInnocldOnNone=True):    
    from dsbase.tools.clientdatastore import ClientDataStore
    cds = ClientDataStore(clientid='dpcm')
    fileid = cds.clientds.get_id_byname(name=objname)
    if fileid: 
        getfile = cds.get_file(fileid[0])
        if getfile.status_code == 200 : return yaml.safe_load(getfile.text)
        else: raise RuntimeError(f"Request with status code {getfile.status_code}")
    elif tryInnocldOnNone: 
        upload_to_cds(filepath=filepath, objname=objname, cds_tsubpath=cds_tsubpath) 
        return get_from_cds(filepath=filepath, objname=objname, cds_tsubpath=cds_tsubpath, tryInnocldOnNone=False)
    else: raise FileNotFoundError(f"file '{objname}' dose not exist")
        
def upload_to_cds(filepath, objname, cds_tsubpath):    
    if os.path.exists(filepath):
        from dsbase.tools.clientdatastore import ClientDataStore
        cds = ClientDataStore(clientid='dpcm')
        return cds.put_file(**{'sfilepath':filepath,'sfilename':objname,'tsubpath':cds_tsubpath,'tfilename':objname})
    else: raise FileNotFoundError(f"Given '{filepath}' has not the file '{objname} found'")
