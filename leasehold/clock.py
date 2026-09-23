"""手动推进的假时钟，调用它就返回当前秒数。"""


class FakeClock:
    """测试用时钟。

    >>> clock = FakeClock(100.0)
    >>> clock()
    100.0
    >>> clock.advance(5)
    105.0
    """

    def __init__(self, start=0.0):
        self._now = float(start)

    def __call__(self):
        return self._now

    def advance(self, seconds):
        self._now += float(seconds)
        return self._now
