"""带租约的键占用表。

只依赖标准库。
"""

from .clock import FakeClock
from .table import LeaseTable

__all__ = ["LeaseTable", "FakeClock"]

__version__ = "0.1.0"
