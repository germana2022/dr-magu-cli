import pytest
from dr_magu.security.permission_guard import PermissionGuard


def test_validate_shell_command_blocks_dangerous_command():
    guard = PermissionGuard(["rm -rf"])

    with pytest.raises(PermissionError):
        guard.validate_shell_command("rm -rf /")


def test_validate_shell_command_allows_safe_command():
    guard = PermissionGuard(["rm -rf"])

    guard.validate_shell_command("pytest")
