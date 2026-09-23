"""带租约的键占用表。

语义见仓库根目录的 README。
"""

import threading
import time
import uuid

from .errors import CapacityExceeded


class LeaseTable:
    """按 key 记录「谁占着、什么时候到期」。

    ``clock`` 是返回当前秒数的零参可调用对象，默认 :func:`time.monotonic`。
    ``max_leases`` 是同时存活的租约数上限，``None`` 表示不限。
    """

    def __init__(self, clock=time.monotonic, max_leases=None):
        self._clock = clock
        self._max_leases = max_leases
        self._leases = {}  # key -> (token, expires_at)
        self._lock = threading.Lock()
        self._stats = {"acquired": 0, "renewed": 0, "released": 0, "expired": 0}

    @staticmethod
    def _check_ttl(ttl):
        if ttl <= 0:
            raise ValueError("ttl 必须为正数")

    def _purge_expired(self, now):
        """清掉所有已过期的项（调用方须已持有锁），返回清掉的条数。"""
        dead = [key for key, (_, expires_at) in self._leases.items() if now >= expires_at]
        for key in dead:
            del self._leases[key]
        self._stats["expired"] += len(dead)
        return len(dead)

    def acquire(self, key, ttl):
        """尝试占用 ``key``：成功返回 token，已被占用返回 ``None``。

        存活租约数达到 ``max_leases`` 时抛 :class:`CapacityExceeded`。
        """
        self._check_ttl(ttl)
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            if key in self._leases:
                return None
            if self._max_leases is not None and len(self._leases) >= self._max_leases:
                raise CapacityExceeded(
                    "存活租约数已达上限 %d" % self._max_leases
                )
            token = uuid.uuid4().hex
            self._leases[key] = (token, now + ttl)
            self._stats["acquired"] += 1
            return token

    def acquire_many(self, keys, ttl):
        """一次占用一批 key，要么全部成功，要么整体失败。

        成功返回与 ``keys`` 同序的 token 列表；任一 key 不可得时返回 ``None``。
        """
        self._check_ttl(ttl)
        keys = list(keys)
        if len(set(keys)) != len(keys):
            raise ValueError("keys 中存在重复")
        if not keys:
            return []
        with self._lock:
            now = self._clock()
            # 失败路径不得留下任何痕迹：先只做只读检查。
            for key in keys:
                lease = self._leases.get(key)
                if lease is not None and now < lease[1]:
                    return None
            if self._max_leases is not None:
                live = sum(1 for _, expires_at in self._leases.values() if now < expires_at)
                if live + len(keys) > self._max_leases:
                    raise CapacityExceeded(
                        "存活租约数将超过上限 %d" % self._max_leases
                    )
            self._purge_expired(now)
            tokens = []
            for key in keys:
                token = uuid.uuid4().hex
                self._leases[key] = (token, now + ttl)
                tokens.append(token)
            self._stats["acquired"] += len(tokens)
            return tokens

    def renew(self, key, token, ttl):
        """给还持有租约的调用方续租。"""
        self._check_ttl(ttl)
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            lease = self._leases.get(key)
            if lease is None or lease[0] != token:
                return False
            self._leases[key] = (token, now + ttl)
            self._stats["renewed"] += 1
            return True

    def release(self, key, token):
        """主动释放。"""
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            lease = self._leases.get(key)
            if lease is None or lease[0] != token:
                return False
            del self._leases[key]
            self._stats["released"] += 1
            return True

    def owner(self, key):
        """返回当前持有者的 token；没人持有返回 ``None``。"""
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            lease = self._leases.get(key)
            return lease[0] if lease is not None else None

    def sweep(self):
        """清掉所有已过期的项，返回清掉的条数。"""
        with self._lock:
            return self._purge_expired(self._clock())

    def stats(self):
        """返回运行计数：``acquired`` / ``renewed`` / ``released`` / ``expired``。"""
        with self._lock:
            self._purge_expired(self._clock())
            return dict(self._stats)

    def __len__(self):
        """当前仍被占用的 key 数量。"""
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._leases)
