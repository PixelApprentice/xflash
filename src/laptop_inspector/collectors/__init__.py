"""Hardware collector adapters for native OS and bootable environments."""
import platform
from .base import Collector, CommandResult, safe_exec
from .linux import LinuxCollector
from .windows import WindowsCollector


def get_collector() -> Collector:
    """Return the appropriate hardware collector for the running OS."""
    os_name = platform.system()
    if os_name == "Windows":
        return WindowsCollector()
    elif os_name == "Linux":
        return LinuxCollector()
    else:
        # Fallback to LinuxCollector with default sysfs path
        return LinuxCollector()


__all__ = ["Collector", "CommandResult", "safe_exec", "LinuxCollector", "WindowsCollector", "get_collector"]
