"""带租约的键占用表。

语义见仓库根目录的 README：到点即失效、惰性回收、批量原子、配额计数、线程安全。
"""

import itertools
import threading
import time

from .errors import CapacityExceeded


class LeaseTable:
    """按 key 记录「谁占着、什么时候到期」。

    ``clock`` 是返回当前秒数的零参可调用对象，默认 :func:`time.monotonic`。
    ``max_leases`` 是同时存活的租约数上限，``None`` 表示不限。
    """

    def __init__(self, clock=time.monotonic, max_leases=None):
        self._clock = clock
        self._max_leases = max_leases
        self._leases = {}
        self._stats = {"acquired": 0, "renewed": 0, "released": 0, "expired": 0}
        self._lock = threading.Lock()
        self._token_seq = itertools.count(1)

    @staticmethod
    def _check_ttl(ttl):
        if ttl <= 0:
            raise ValueError("ttl 必须是正数")

    def _new_token(self):
        return f"lease-{next(self._token_seq)}"

    def _purge_expired(self, now):
        """删除所有 now >= 到期时刻 的租约，返回删除条数并累计 expired。"""
        dead = [key for key, (_, expiry) in self._leases.items() if now >= expiry]
        for key in dead:
            del self._leases[key]
        if dead:
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
                raise CapacityExceeded(f"存活租约已达上限 {self._max_leases}")
            token = self._new_token()
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
            self._purge_expired(now)
            if any(key in self._leases for key in keys):
                return None
            if (
                self._max_leases is not None
                and len(self._leases) + len(keys) > self._max_leases
            ):
                raise CapacityExceeded(f"存活租约已达上限 {self._max_leases}")
            tokens = []
            for key in keys:
                token = self._new_token()
                tokens.append(token)
                self._leases[key] = (token, now + ttl)
            self._stats["acquired"] += len(keys)
            return tokens

    def renew(self, key, token, ttl):
        """给还持有租约的调用方续租。"""
        self._check_ttl(ttl)
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            entry = self._leases.get(key)
            if entry is None or entry[0] != token:
                return False
            self._leases[key] = (token, now + ttl)
            self._stats["renewed"] += 1
            return True

    def release(self, key, token):
        """主动释放。"""
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            entry = self._leases.get(key)
            if entry is None or entry[0] != token:
                return False
            del self._leases[key]
            self._stats["released"] += 1
            return True

    def owner(self, key):
        """返回当前持有者的 token；没人持有返回 ``None``。"""
        with self._lock:
            self._purge_expired(self._clock())
            entry = self._leases.get(key)
            return entry[0] if entry is not None else None

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
