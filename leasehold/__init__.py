"""带租约的键占用表。

只依赖标准库。
"""

from .clock import FakeClock
from .errors import CapacityExceeded, LeaseError
from .table import LeaseTable

__all__ = ["LeaseTable", "FakeClock", "LeaseError", "CapacityExceeded"]

__version__ = "0.2.0"
