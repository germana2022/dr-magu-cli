
from dr_magu.permissions.registry import get_policy
def test_shell_requires_approval():
    assert get_policy("shell.run").mode=="approval_required"
def test_git_push_blocked():
    assert get_policy("git.push").mode=="blocked"
