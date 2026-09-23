"""带租约的键占用表。

**这个文件目前是空壳，需要实现。** 语义见仓库根目录的 README。
"""

import time

from .errors import CapacityExceeded


class LeaseTable:
    """按 key 记录「谁占着、什么时候到期」。

    ``clock`` 是返回当前秒数的零参可调用对象，默认 :func:`time.monotonic`。
    ``max_leases`` 是同时存活的租约数上限，``None`` 表示不限。
    """

    def __init__(self, clock=time.monotonic, max_leases=None):
        raise NotImplementedError("LeaseTable 还没实现")

    def acquire(self, key, ttl):
        """尝试占用 ``key``：成功返回 token，已被占用返回 ``None``。

        存活租约数达到 ``max_leases`` 时抛 :class:`CapacityExceeded`。
        """
        raise NotImplementedError

    def acquire_many(self, keys, ttl):
        """一次占用一批 key，要么全部成功，要么整体失败。

        成功返回与 ``keys`` 同序的 token 列表；任一 key 不可得时返回 ``None``。
        """
        raise NotImplementedError

    def renew(self, key, token, ttl):
        """给还持有租约的调用方续租。"""
        raise NotImplementedError

    def release(self, key, token):
        """主动释放。"""
        raise NotImplementedError

    def owner(self, key):
        """返回当前持有者的 token；没人持有返回 ``None``。"""
        raise NotImplementedError

    def sweep(self):
        """清掉所有已过期的项，返回清掉的条数。"""
        raise NotImplementedError

    def stats(self):
        """返回运行计数：``acquired`` / ``renewed`` / ``released`` / ``expired``。"""
        raise NotImplementedError

    def __len__(self):
        """当前仍被占用的 key 数量。"""
        raise NotImplementedError
