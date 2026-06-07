
from dr_magu.plugins.resource_contracts import PluginResources
from dr_magu.plugins.resource_validator import validate_resources

def test_plugin_resources_contract():
    r = PluginResources(
        agents=["repository-analyzer"],
        workflows=["repository.context"],
        tools=["repo.scan"]
    )
    assert validate_resources(r) is True
