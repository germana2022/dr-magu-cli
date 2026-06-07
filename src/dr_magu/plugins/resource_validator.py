
from .resource_contracts import PluginResources

def validate_resources(resources: PluginResources) -> bool:
    return isinstance(resources.agents, list) and isinstance(resources.tools, list)
