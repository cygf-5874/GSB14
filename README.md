# leasehold

单进程内共享的「键占用表」：谁先占了某个 key，在租约到期之前别人拿不到；
到期自动失效，不需要后台线程去清理。

```python
from leasehold import LeaseTable

table = LeaseTable(max_leases=1000)      # clock 默认用 time.monotonic
token = table.acquire("job-42", ttl=30)
if token is None:
    ...                                  # 已经被别人占着了
else:
    try:
        do_work()
    finally:
        table.release("job-42", token)
```

## 需要实现什么

`leasehold/table.py` 里的 `LeaseTable` 现在是个空壳，方法体全是 `NotImplementedError`。
请把它实现出来。**只有这个文件需要改**，`__init__.py`、`clock.py`、`errors.py`、
`tests/` 都不用动。

## 接口

| 接口 | 说明 |
| --- | --- |
| `LeaseTable(clock=time.monotonic, max_leases=None)` | `clock` 是返回当前秒数的零参可调用对象，方便注入假时钟。`max_leases` 是同时存活的租约数上限，`None` 不限。 |
| `acquire(key, ttl)` | 占用 `key`。成功返回 token（非空字符串）；已被占用返回 `None`；存活租约已满抛 `CapacityExceeded`。 |
| `acquire_many(keys, ttl)` | 一次占用一批 key。成功返回与 `keys` 同序的 token 列表；任一不可得返回 `None`。 |
| `renew(key, token, ttl)` | 给还持有租约的调用方续租，成功返回 `True`。 |
| `release(key, token)` | 主动释放，成功返回 `True`。 |
| `owner(key)` | 返回当前持有者的 token；没人持有返回 `None`。 |
| `sweep()` | 清掉所有已过期的项，返回清掉的条数。 |
| `stats()` | 返回 `{"acquired", "renewed", "released", "expired"}` 四个计数。 |
| `len(table)` | 当前仍被占用的 key 数量。 |
| `ValueError` | `ttl <= 0`（`acquire` / `acquire_many` / `renew` 都要），或 `acquire_many` 的 `keys` 有重复。 |
| `CapacityExceeded` | 存活租约数会超过 `max_leases`。 |

## 语义（验收依据）

1. **过期判定**：`现在 >= 到期时刻` 就算过期——到点即失效，不需要多等一刻，也不存在
   「正好卡在到期时刻还能用」的窗口。
2. **惰性过期**：`acquire` / `acquire_many` / `owner` / `renew` / `release` / `sweep` /
   `len` / `stats` 都必须把已过期的项当成不存在，不能要求调用方先调 `sweep()`。
3. **token 唯一**：同一个 key 每次成功 `acquire`（或 `acquire_many` 里的每个 key）
   拿到的 token 都不相同。
4. **ttl 从调用时刻起算**：`acquire(key, ttl)` 的到期时刻是「调用时的时钟读数 + ttl」；
   `renew(key, token, ttl)` 同理，`renew` 会重置到期时刻。
5. **token 校验**：`renew` 和 `release` 只认当前持有者的 token。key 不存在、已过期、
   或 token 对不上，一律返回 `False`，并且**不改变任何仍然存活的租约**。
6. **容量上限**：`max_leases` 约束的是**同时存活的租约数**（过期的不算）。
   达到上限时 `acquire` 抛 `CapacityExceeded`；`max_leases=None` 表示不限。
7. **批量原子性**：`acquire_many(keys, ttl)` 要么整批成功，要么整批不生效——
   失败时不留任何痕迹（不占 key、`len` 不变、`stats()` 不变）。`keys` 为空返回 `[]`；
   `keys` 里有重复抛 `ValueError`。
8. **sweep 只清过期项**：没过期的一个都不能动，返回值是清掉的条数（没有过期项就是 0）。
9. **计数语义**：`stats()` 只增不减，返回的是副本（改它不影响内部状态）。
   - `acquired` 统计**真正生效**的占用条数——`acquire` 一条算一条，`acquire_many`
     成功那批按 key 个数算；失败或回滚掉的不算。
   - `renewed` / `released` 分别统计成功续租、成功释放的条数。
   - `expired` 统计**被回收的过期租约条数**：无论回收是被 `sweep()` 触发的，还是被
     其它方法惰性触发的，**同一条租约只能计一次**。
10. **线程安全**：多个线程同时对同一个 key 调 `acquire`，只有一个能拿到 token，
    其余拿到 `None`；`acquire_many` 与其它写操作之间也不能交叠出中间状态；
    `len`、`owner`、`stats` 等读操作也不能看到中间状态。

## 跑测试

```bash
python3 -m unittest discover -s tests -v
```

`tests/test_basic.py` 只是最基本的几条，上面「语义」一节里还有它没覆盖到的边界。

## 目录

```
leasehold/
  __init__.py   导出 LeaseTable / FakeClock / LeaseError / CapacityExceeded
  clock.py      可手动推进的假时钟
  errors.py     异常层级
  table.py      ← 要实现的文件
tests/
  test_basic.py 基础用例
```
