from decimal import Decimal
import unittest

from matching_engine import MatchingEngine


class MatchingEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MatchingEngine()

    def test_book_sorts_by_price_and_arrival(self) -> None:
        first, _ = self.engine.add_limit_order("buy", Decimal("10"), 200)
        second, _ = self.engine.add_limit_order("buy", Decimal("10"), 150)
        third, _ = self.engine.add_limit_order("buy", Decimal("9.99"), 100)
        sell, _ = self.engine.add_limit_order("sell", Decimal("10.5"), 100)
        self.assertEqual(self.engine.book_orders("buy"), [first, second, third])
        self.assertEqual(self.engine.book_orders("sell"), [sell])
        self.assertIn("200 @ 10", self.engine.render_book())

    def test_market_fills_oldest_order_first(self) -> None:
        first, _ = self.engine.add_limit_order("sell", Decimal("20"), 100)
        second, _ = self.engine.add_limit_order("sell", Decimal("20"), 200)
        trades = self.engine.add_market_order("buy", 150)
        self.assertNotIn(first.id, self.engine.orders)
        self.assertEqual(self.engine.orders[second.id].qty, 150)
        self.assertEqual(trades[0].qty, 150)

    def test_market_visits_best_price_first_and_discards_remainder(self) -> None:
        self.engine.add_limit_order("sell", Decimal("21"), 100)
        self.engine.add_limit_order("sell", Decimal("20"), 50)
        trades = self.engine.add_market_order("buy", 200)
        self.assertEqual([(t.price, t.qty) for t in trades], [(Decimal("20"), 50), (Decimal("21"), 100)])
        self.assertEqual(self.engine.orders, {})
        self.assertEqual(self.engine.add_market_order("buy", 10), [])

    def test_crossing_limit_fills_at_resting_price_and_books_remainder(self) -> None:
        self.engine.add_limit_order("sell", Decimal("10"), 80)
        order, trades = self.engine.add_limit_order("buy", Decimal("11"), 100)
        self.assertEqual([(t.price, t.qty) for t in trades], [(Decimal("10"), 80)])
        self.assertEqual((order.price, order.qty), (Decimal("11"), 20))

    def test_limit_stops_at_its_price(self) -> None:
        self.engine.add_limit_order("sell", Decimal("10"), 50)
        self.engine.add_limit_order("sell", Decimal("12"), 50)
        order, trades = self.engine.add_limit_order("buy", Decimal("11"), 100)
        self.assertEqual([(t.price, t.qty) for t in trades], [(Decimal("10"), 50)])
        self.assertEqual(order.qty, 50)
        self.assertEqual(self.engine.book_orders("sell")[0].price, Decimal("12"))

    def test_cancel_removes_order_and_reports_missing_id(self) -> None:
        order, _ = self.engine.add_limit_order("buy", Decimal("10"), 100)
        self.assertTrue(self.engine.cancel_order(order.id))
        self.assertFalse(self.engine.cancel_order(order.id))
        self.assertEqual(self.engine.book_orders("buy"), [])


if __name__ == "__main__":
    unittest.main()
