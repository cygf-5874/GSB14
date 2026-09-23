# leasehold

单进程内共享的「键占用表」：谁先占了某个 key，在租约到期之前别人拿不到；
到期自动失效，不需要后台线程去清理。

```python
from leasehold import LeaseTable

table = LeaseTable()                     # 默认用 time.monotonic
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
请把它实现出来。**只有这个文件需要改**，`__init__.py`、`clock.py`、`tests/` 都不用动。

## 接口

| 接口 | 说明 |
| --- | --- |
| `LeaseTable(clock=time.monotonic)` | `clock` 是返回当前秒数的零参可调用对象，方便注入假时钟。 |
| `acquire(key, ttl)` | 尝试占用 `key`。成功返回 token（非空字符串）；已被占用返回 `None`。`ttl <= 0` 抛 `ValueError`。 |
| `renew(key, token, ttl)` | 给还在持有租约的调用方续租，成功返回 `True`。`ttl <= 0` 抛 `ValueError`。 |
| `release(key, token)` | 主动释放，成功返回 `True`。 |
| `owner(key)` | 返回当前持有者的 token；没人持有返回 `None`。 |
| `sweep()` | 清掉所有已过期的项，返回清掉的条数。 |
| `len(table)` | 当前仍被占用的 key 数量。 |

## 语义（验收依据）

1. **过期判定**：`现在 >= 到期时刻` 就算过期——到点即失效，不需要多等一刻，也不存在
   「正好卡在到期时刻还能用」的窗口。
2. **惰性过期**：`acquire`、`owner`、`renew`、`release`、`len` 都必须把已过期的项当成
   不存在，不能要求调用方先调 `sweep()`。
3. **token 校验**：`renew` 和 `release` 只认当前持有者的 token。key 不存在、已经过期、
   或者 token 对不上，一律返回 `False`，并且**不改变任何状态**。
4. **token 唯一**：同一个 key 每次成功 `acquire` 拿到的 token 都不相同。
5. **ttl 从调用时刻起算**：`acquire(key, ttl)` 的到期时刻是「调用时的时钟读数 + ttl」；
   `renew(key, token, ttl)` 同理。
6. **sweep 只清过期项**：没过期的一个都不能动，返回值是清掉的条数（没有过期项就是 0）。
7. **线程安全**：多个线程同时对同一个 key 调 `acquire`，只有一个能拿到 token，
   其余拿到 `None`；`len`、`owner` 等读操作也不能看到中间状态。

## 跑测试

```bash
python3 -m unittest discover -s tests -v
```

`tests/test_basic.py` 只是最基本的几条，上面「语义」一节里还有它没覆盖到的边界。

## 目录

```
leasehold/
  __init__.py   导出 LeaseTable / FakeClock
  table.py      ← 要实现的文件
  clock.py      可手动推进的假时钟
tests/
  test_basic.py 基础用例
```
