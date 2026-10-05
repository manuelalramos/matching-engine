from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass
class Order:
    id: str
    side: str
    price: Decimal | None
    qty: int
    sequence: int
    peg_reference: str | None = None


@dataclass
class Trade:
    price: Decimal
    qty: int


class MatchingEngine:
    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}
        self.next_id = 1
        self.next_sequence = 1

    def _new_order(self, side: str, price: Decimal | None, qty: int) -> Order:
        order = Order(f"order_{self.next_id}", side, price, qty, self.next_sequence)
        self.next_id += 1
        self.next_sequence += 1
        return order

    def book_orders(self, side: str) -> list[Order]:
        orders = [
            order for order in self.orders.values()
            if order.side == side and order.price is not None
        ]
        if side == "buy":
            return sorted(orders, key=lambda order: (-order.price, order.sequence))
        return sorted(orders, key=lambda order: (order.price, order.sequence))

    def add_limit_order(self, side: str, price: Decimal, qty: int) -> tuple[Order | None, list[Trade]]:
        validate_side_qty(side, qty)
        validate_price(price)
        order = self._new_order(side, price, qty)
        trades = self._match(order)
        if order.qty > 0:
            self.orders[order.id] = order
        self._refresh_pegged_orders()
        return (order if order.qty > 0 else None), trades

    def add_market_order(self, side: str, qty: int) -> list[Trade]:
        validate_side_qty(side, qty)
        order = self._new_order(side, None, qty)
        trades = self._match(order)
        self._refresh_pegged_orders()
        return trades

    def _match(self, incoming: Order) -> list[Trade]:
        trades = []
        opposite = "sell" if incoming.side == "buy" else "buy"

        while incoming.qty > 0:
            candidates = self.book_orders(opposite)
            if not candidates:
                break
            resting = candidates[0]
            if incoming.price is not None:
                if incoming.side == "buy" and incoming.price < resting.price:
                    break
                if incoming.side == "sell" and incoming.price > resting.price:
                    break

            trade_price = resting.price
            trade_qty = min(incoming.qty, resting.qty)
            incoming.qty -= trade_qty
            resting.qty -= trade_qty
            if trades and trades[-1].price == trade_price:
                trades[-1].qty += trade_qty
            else:
                trades.append(Trade(trade_price, trade_qty))

            if resting.qty == 0:
                del self.orders[resting.id]
            self._refresh_pegged_orders()

        return trades

    def cancel_order(self, order_id: str) -> bool:
        if order_id not in self.orders:
            return False
        del self.orders[order_id]
        self._refresh_pegged_orders()
        return True

    def amend_order(
        self, order_id: str, *, price: Decimal | None = None, qty: int | None = None
    ) -> tuple[Order | None, list[Trade]]:
        if order_id not in self.orders:
            raise ValueError("Order not found")
        if price is None and qty is None:
            raise ValueError("Provide price, qty, or both")

        order = self.orders[order_id]
        if price is not None:
            validate_price(price)
        if qty is not None:
            validate_side_qty(order.side, qty)

        loses_priority = (price is not None and price != order.price) or (
            qty is not None and qty > order.qty
        )
        if loses_priority:
            order.sequence = self.next_sequence
            self.next_sequence += 1
        if price is not None:
            order.price = price
            order.peg_reference = None
        if qty is not None:
            order.qty = qty

        # A pegged order without a reference must not behave like a market order.
        if order.peg_reference is not None:
            self._refresh_pegged_orders()
            return order, []

        del self.orders[order_id]
        trades = self._match(order)
        if order.qty > 0:
            self.orders[order_id] = order
        self._refresh_pegged_orders()
        return (order if order.qty > 0 else None), trades

    def add_pegged_order(self, reference: str, side: str, qty: int) -> Order:
        validate_side_qty(side, qty)
        if (reference, side) not in {("bid", "buy"), ("offer", "sell")}:
            raise ValueError("Use peg bid buy or peg offer sell")
        order = self._new_order(side, None, qty)
        order.peg_reference = reference
        self.orders[order.id] = order
        self._refresh_pegged_orders()
        return order

    def _refresh_pegged_orders(self) -> None:
        # Only regular limit orders provide a reference, avoiding circular prices.
        buy_prices = []
        sell_prices = []
        for order in self.orders.values():
            if order.peg_reference is None and order.price is not None:
                if order.side == "buy":
                    buy_prices.append(order.price)
                else:
                    sell_prices.append(order.price)

        bid = max(buy_prices) if buy_prices else None
        offer = min(sell_prices) if sell_prices else None
        for order in self.orders.values():
            if order.peg_reference == "bid":
                order.price = bid
            elif order.peg_reference == "offer":
                order.price = offer

    def render_book(self, show_ids: bool = False) -> str:
        def labels(side: str) -> list[str]:
            rows = []
            for order in self.book_orders(side):
                text = f"{order.qty} @ {format_price(order.price)}"
                if show_ids:
                    text += f" {order.id}"
                rows.append(text)
            return rows

        buys = labels("buy")
        sells = labels("sell")
        width = max([20] + [len(row) for row in buys])
        lines = [
            f"{'Ordens de Compra':<{width}} | Ordens de Venda",
            f"{'-' * width}|{'-' * 16}",
        ]
        for index in range(max(len(buys), len(sells))):
            buy = buys[index] if index < len(buys) else ""
            sell = sells[index] if index < len(sells) else ""
            lines.append(f"{buy:<{width}} | {sell}")

        waiting = [order for order in self.orders.values() if order.price is None]
        for order in sorted(waiting, key=lambda item: item.sequence):
            lines.append(f"Waiting reference: {order.id} peg {order.peg_reference} {order.side} {order.qty}")
        return "\n".join(lines)


def validate_side_qty(side: str, qty: int) -> None:
    if side not in {"buy", "sell"}:
        raise ValueError("Side must be buy or sell")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise ValueError("Quantity must be a positive integer")


def validate_price(price: Decimal) -> None:
    if not isinstance(price, Decimal) or not price.is_finite() or price <= 0:
        raise ValueError("Price must be a positive finite Decimal")


def parse_price(raw: str) -> Decimal:
    try:
        price = Decimal(raw)
    except InvalidOperation as error:
        raise ValueError("Invalid price") from error
    validate_price(price)
    return price


def format_price(price: Decimal) -> str:
    text = format(price, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def order_message(prefix: str, order: Order) -> str:
    price = f"@ {format_price(order.price)}" if order.price is not None else "waiting reference"
    peg = f" peg {order.peg_reference}" if order.peg_reference else ""
    return f"{prefix}: {order.side} {order.qty}{peg} {price} {order.id}"


def execute_command(engine: MatchingEngine, command: str) -> list[str]:
    parts = command.lower().split()
    if not parts:
        return []
    if parts in [["exit"], ["quit"]]:
        raise EOFError
    if parts == ["help"]:
        return [
            "limit <buy|sell> <price> <qty>",
            "market <buy|sell> <qty>",
            "peg bid buy <qty> | peg offer sell <qty>",
            "cancel [order] <id>",
            "amend [order] <id> [price <price>] [qty <qty>]",
            "book | book ids | print book | exit",
        ]
    if parts in [["book"], ["print", "book"], ["book", "ids"]]:
        return [engine.render_book(show_ids=parts == ["book", "ids"])]

    verb = parts[0]
    order = None
    trades = []
    prefix = "Order created"
    if verb == "limit" and len(parts) == 4:
        order, trades = engine.add_limit_order(parts[1], parse_price(parts[2]), int(parts[3]))
    elif verb == "market" and len(parts) == 3:
        trades = engine.add_market_order(parts[1], int(parts[2]))
    elif verb == "peg" and len(parts) == 4:
        order = engine.add_pegged_order(parts[1], parts[2], int(parts[3]))
    elif verb == "cancel":
        args = parts[2:] if parts[1:2] == ["order"] else parts[1:]
        if len(args) != 1:
            raise ValueError("Usage: cancel [order] <id>")
        return ["Order cancelled" if engine.cancel_order(args[0]) else "Order not found"]
    elif verb == "amend":
        args = parts[2:] if parts[1:2] == ["order"] else parts[1:]
        if len(args) not in {3, 5}:
            raise ValueError("Usage: amend [order] <id> [price <price>] [qty <qty>]")
        updates = {}
        for index in range(1, len(args), 2):
            field, value = args[index], args[index + 1]
            if field not in {"price", "qty"} or field in updates:
                raise ValueError("Use price and/or qty once each")
            updates[field] = parse_price(value) if field == "price" else int(value)
        order, trades = engine.amend_order(args[0], **updates)
        prefix = "Order amended"
    else:
        raise ValueError("Invalid command. Type help for commands")

    lines = [f"Trade, price: {format_price(trade.price)}, qty: {trade.qty}" for trade in trades]
    if order is not None:
        lines.append(order_message(prefix, order))
    elif verb == "amend":
        lines.append("Order amended and fully filled")
    return lines or ["No trades"]


def main() -> None:
    engine = MatchingEngine()
    print("Matching Engine ready. Type 'help' for commands.")
    while True:
        try:
            for line in execute_command(engine, input(">>> ")):
                print(line)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        except ValueError as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    main()
