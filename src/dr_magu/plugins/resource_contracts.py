
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PluginResources:
    agents: list[str] = field(default_factory=list)
    workflows: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    schedules: list[str] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)
