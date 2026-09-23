"""异常定义。"""


class LeaseError(Exception):
    """本模块所有异常的基类。"""


class CapacityExceeded(LeaseError):
    """同时存活的租约数已经达到 ``max_leases`` 上限。"""
