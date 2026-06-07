
from dataclasses import dataclass

@dataclass(frozen=True)
class PermissionPolicy:
    tool_name:str
    mode:str
    risk_level:str
    background_allowed:bool=False
