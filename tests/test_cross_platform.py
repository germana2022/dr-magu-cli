
from dr_magu.platform.system_info import get_platform_info, normalize_path
from dr_magu.platform.shell import default_shell

def test_platform_info():
    assert "os" in get_platform_info()

def test_normalize_path():
    assert normalize_path(".")

def test_default_shell():
    assert default_shell() in ["powershell", "bash"]
