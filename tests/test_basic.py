import unittest

from leasehold import FakeClock, LeaseTable


class BasicTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.table = LeaseTable(self.clock)

    def test_acquire_returns_a_token(self):
        token = self.table.acquire("a", 10)
        self.assertIsInstance(token, str)
        self.assertTrue(token)

    def test_acquire_twice_gets_none(self):
        self.assertIsNotNone(self.table.acquire("a", 10))
        self.assertIsNone(self.table.acquire("a", 10))

    def test_different_keys_are_independent(self):
        first = self.table.acquire("a", 10)
        second = self.table.acquire("b", 10)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)

    def test_owner_reflects_the_holder(self):
        token = self.table.acquire("a", 10)
        self.assertEqual(self.table.owner("a"), token)

    def test_owner_of_unknown_key_is_none(self):
        self.assertIsNone(self.table.owner("nobody"))

    def test_release_frees_the_key(self):
        token = self.table.acquire("a", 10)
        self.assertTrue(self.table.release("a", token))
        self.assertIsNone(self.table.owner("a"))
        self.assertIsNotNone(self.table.acquire("a", 10))

    def test_renew_extends_the_lease(self):
        token = self.table.acquire("a", 10)
        self.clock.advance(9)
        self.assertTrue(self.table.renew("a", token, 10))
        self.clock.advance(9)
        self.assertEqual(self.table.owner("a"), token)

    def test_ttl_must_be_positive(self):
        with self.assertRaises(ValueError):
            self.table.acquire("a", 0)
        with self.assertRaises(ValueError):
            self.table.acquire("a", -0.5)

    def test_len_counts_live_leases(self):
        self.table.acquire("a", 10)
        self.table.acquire("b", 10)
        self.assertEqual(len(self.table), 2)

    def test_default_clock_is_usable(self):
        table = LeaseTable()
        self.assertIsNotNone(table.acquire("a", 1))


if __name__ == "__main__":
    unittest.main()
