from decimal import Decimal
import unittest

from matching_engine import MatchingEngine


class MatchingEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MatchingEngine()

    def test_book_sorts_by_price_and_arrival(self) -> None:
        first = self.engine.add_limit_order("buy", Decimal("10"), 200)
        second = self.engine.add_limit_order("buy", Decimal("10"), 150)
        third = self.engine.add_limit_order("buy", Decimal("9.99"), 100)
        sell = self.engine.add_limit_order("sell", Decimal("10.5"), 100)
        self.assertEqual(self.engine.book_orders("buy"), [first, second, third])
        self.assertEqual(self.engine.book_orders("sell"), [sell])
        self.assertIn("200 @ 10", self.engine.render_book())


if __name__ == "__main__":
    unittest.main()
