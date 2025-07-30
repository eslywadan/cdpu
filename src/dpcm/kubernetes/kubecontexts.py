from kubernetes import config, client
from dpcm.kubernetes.kubeconf import kubeconfig

class KubeContexts:
    
    config_file_ = kubeconfig(operation="get", destination="cds") # Original Config file
    config = config 
        
    def __init__(self, context_name: str='ci-dev', disable_tlsverify=True):
        self.context_name = context_name
        self.switch_context()
        self.config.load_kube_config_from_dict(self.config_file) # Set deagult config on loaded
        self.configuration = client.Configuration.get_default_copy() # Get a default copy 
        if disable_tlsverify: self.configuration.verify_ssl = False # Customized the config
        self._get_namespace()
        self.api_client = client.ApiClient(self.configuration)
        self.apps_v1 = client.AppsV1Api(self.api_client)
        self.corev1api = client.CoreV1Api(self.api_client)
        
    def switch_context(self):
        # swith the 'currnet' contex to assinged context name
        context_names = [ctx["name"] for ctx in self.config_file_.get("contexts", [])]
        if self.context_name not in context_names:
            raise ValueError(f"Context {self.context_name} not found in kubectl file")
        self.config_file = self.config_file_
        self.config_file["current-context"] = self.context_name
        
    def _get_namespace(self):
        _, current = self.config.list_kube_config_contexts()
        namespace = current['context'].get('namespace', 'default')
        if namespace : self.namespace = namespace
        else:  self.namespace =  "default"
        
    def get_namesapce(self):
        return self.namespace
    
    def get_api_client(self):
        return self.api_client
    
    def get_context_name(self):
        return self.context_name