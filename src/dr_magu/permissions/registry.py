
from .models import PermissionPolicy
DEFAULT_POLICIES={
 "repo.scan":PermissionPolicy("repo.scan","allowed","low",True),
 "context.generate":PermissionPolicy("context.generate","allowed","low",True),
 "shell.run":PermissionPolicy("shell.run","approval_required","high",False),
 "git.push":PermissionPolicy("git.push","blocked","critical",False),
}
def get_policy(tool_name:str):
    return DEFAULT_POLICIES.get(tool_name)
