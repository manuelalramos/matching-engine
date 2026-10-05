from decimal import Decimal
import unittest

from matching_engine import MatchingEngine, execute_command


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

    def test_price_amend_moves_level_and_loses_priority(self) -> None:
        first, _ = self.engine.add_limit_order("buy", Decimal("10"), 200)
        second, _ = self.engine.add_limit_order("buy", Decimal("9.99"), 100)
        third, _ = self.engine.add_limit_order("buy", Decimal("9.98"), 50)
        self.engine.amend_order(first.id, price=Decimal("9.98"))
        self.assertEqual(self.engine.book_orders("buy"), [second, third, first])

    def test_quantity_increase_loses_priority(self) -> None:
        first, _ = self.engine.add_limit_order("buy", Decimal("10"), 100)
        second, _ = self.engine.add_limit_order("buy", Decimal("10"), 100)
        self.engine.amend_order(first.id, qty=150)
        self.engine.add_market_order("sell", 100)
        self.assertNotIn(second.id, self.engine.orders)
        self.assertEqual(first.qty, 150)

    def test_quantity_decrease_keeps_priority_and_means_remaining_qty(self) -> None:
        first, _ = self.engine.add_limit_order("buy", Decimal("10"), 100)
        second, _ = self.engine.add_limit_order("buy", Decimal("10"), 100)
        self.engine.add_market_order("sell", 20)
        self.engine.amend_order(first.id, qty=60)
        self.engine.add_market_order("sell", 60)
        self.assertNotIn(first.id, self.engine.orders)
        self.assertEqual(second.qty, 100)

    def test_amend_can_cross_and_fully_fill(self) -> None:
        buy, _ = self.engine.add_limit_order("buy", Decimal("9"), 100)
        self.engine.add_limit_order("sell", Decimal("10"), 100)
        order, trades = self.engine.amend_order(buy.id, price=Decimal("10"))
        self.assertIsNone(order)
        self.assertEqual([(t.price, t.qty) for t in trades], [(Decimal("10"), 100)])
        self.assertEqual(self.engine.orders, {})

    def test_invalid_amend_does_not_change_order(self) -> None:
        order, _ = self.engine.add_limit_order("buy", Decimal("10"), 100)
        with self.assertRaises(ValueError):
            self.engine.amend_order(order.id, price=Decimal("11"), qty=0)
        self.assertEqual((order.price, order.qty), (Decimal("10"), 100))
        with self.assertRaises(ValueError):
            self.engine.amend_order("missing", qty=10)

    def test_peg_bid_follows_reference_and_keeps_original_priority(self) -> None:
        first, _ = self.engine.add_limit_order("buy", Decimal("10"), 200)
        lower, _ = self.engine.add_limit_order("buy", Decimal("9.99"), 100)
        peg = self.engine.add_pegged_order("bid", "buy", 150)
        self.assertEqual(self.engine.book_orders("buy"), [first, peg, lower])
        better, _ = self.engine.add_limit_order("buy", Decimal("10.1"), 300)
        self.assertEqual(self.engine.book_orders("buy"), [peg, better, first, lower])
        self.assertEqual(peg.price, Decimal("10.1"))

    def test_peg_offer_moves_when_reference_is_cancelled(self) -> None:
        best, _ = self.engine.add_limit_order("sell", Decimal("10.5"), 100)
        self.engine.add_limit_order("sell", Decimal("11"), 100)
        peg = self.engine.add_pegged_order("offer", "sell", 50)
        self.assertEqual(peg.price, Decimal("10.5"))
        self.engine.cancel_order(best.id)
        self.assertEqual(peg.price, Decimal("11"))

    def test_waiting_peg_can_be_amended_cancelled_and_reactivated(self) -> None:
        self.engine.add_limit_order("sell", Decimal("20"), 100)
        peg = self.engine.add_pegged_order("bid", "buy", 150)
        order, trades = self.engine.amend_order(peg.id, qty=200)
        self.assertIsNone(order.price)
        self.assertEqual(trades, [])
        self.assertEqual(self.engine.book_orders("sell")[0].qty, 100)
        self.assertIn(f"Waiting reference: {peg.id}", self.engine.render_book())
        self.engine.add_limit_order("buy", Decimal("10"), 100)
        self.assertEqual(peg.price, Decimal("10"))
        self.assertTrue(self.engine.cancel_order(peg.id))

    def test_reference_updates_between_fills(self) -> None:
        self.engine.add_limit_order("buy", Decimal("10"), 100)
        self.engine.add_limit_order("buy", Decimal("9"), 100)
        peg = self.engine.add_pegged_order("bid", "buy", 50)
        trades = self.engine.add_market_order("sell", 120)
        self.assertEqual([(t.price, t.qty) for t in trades], [(Decimal("10"), 100), (Decimal("9"), 20)])
        self.assertEqual((peg.price, peg.qty), (Decimal("9"), 50))

    def test_last_regular_reference_disappears_after_fill(self) -> None:
        self.engine.add_limit_order("buy", Decimal("10"), 100)
        peg = self.engine.add_pegged_order("bid", "buy", 50)
        trades = self.engine.add_market_order("sell", 200)
        self.assertEqual([(t.price, t.qty) for t in trades], [(Decimal("10"), 100)])
        self.assertIsNone(peg.price)
        self.assertEqual(peg.qty, 50)

    def test_explicit_price_converts_peg_to_regular_limit(self) -> None:
        peg = self.engine.add_pegged_order("bid", "buy", 50)
        self.engine.amend_order(peg.id, price=Decimal("9"))
        self.engine.add_limit_order("buy", Decimal("10"), 100)
        self.assertIsNone(peg.peg_reference)
        self.assertEqual(peg.price, Decimal("9"))

    def test_validation_rejects_invalid_side_qty_price_and_peg(self) -> None:
        for qty in [0, -1, 1.5, True]:
            with self.subTest(qty=qty), self.assertRaises(ValueError):
                self.engine.add_market_order("buy", qty)
        for price in [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")]:
            with self.subTest(price=price), self.assertRaises(ValueError):
                self.engine.add_limit_order("buy", price, 100)
        with self.assertRaises(ValueError):
            self.engine.add_limit_order("other", Decimal("10"), 100)
        with self.assertRaises(ValueError):
            self.engine.add_pegged_order("bid", "sell", 100)
        self.assertEqual(self.engine.orders, {})

    def test_cli_reproduces_challenge(self) -> None:
        self.assertEqual(execute_command(self.engine, "limit buy 10 100"), ["Order created: buy 100 @ 10 order_1"])
        execute_command(self.engine, "limit sell 20 100")
        execute_command(self.engine, "limit sell 20 200")
        self.assertEqual(execute_command(self.engine, "market buy 150"), ["Trade, price: 20, qty: 150"])
        self.assertEqual(execute_command(self.engine, "market buy 200"), ["Trade, price: 20, qty: 150"])
        self.assertEqual(execute_command(self.engine, "market sell 200"), ["Trade, price: 10, qty: 100"])

    def test_cli_book_ids_cancel_and_amend(self) -> None:
        execute_command(self.engine, "limit buy 10 100")
        self.assertIn("order_1", execute_command(self.engine, "book ids")[0])
        self.assertEqual(execute_command(self.engine, "amend order order_1 price 9.98 qty 80"), ["Order amended: buy 80 @ 9.98 order_1"])
        self.assertEqual(execute_command(self.engine, "cancel order order_1"), ["Order cancelled"])
        self.assertEqual(execute_command(self.engine, "cancel order_1"), ["Order not found"])

    def test_cli_rejects_malformed_commands_without_mutating_book(self) -> None:
        for command in ["book other", "limit buy ten 10", "market buy 1.5", "amend order_1 qty 10 qty 20", "cancel", "exit extra"]:
            with self.subTest(command=command), self.assertRaises(ValueError):
                execute_command(self.engine, command)
        self.assertEqual(self.engine.orders, {})
        self.assertEqual(execute_command(self.engine, "  "), [])
        with self.assertRaises(EOFError):
            execute_command(self.engine, "exit")


if __name__ == "__main__":
    unittest.main()
