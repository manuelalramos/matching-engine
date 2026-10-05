from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Order:
    id: str
    side: str
    price: Decimal | None
    qty: int
    sequence: int


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

    def add_limit_order(self, side: str, price: Decimal, qty: int) -> Order:
        validate_side_qty(side, qty)
        validate_price(price)
        order = self._new_order(side, price, qty)
        self.orders[order.id] = order
        return order

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

        return "\n".join(lines)


def validate_side_qty(side: str, qty: int) -> None:
    if side not in {"buy", "sell"}:
        raise ValueError("Side must be buy or sell")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise ValueError("Quantity must be a positive integer")


def validate_price(price: Decimal) -> None:
    if not isinstance(price, Decimal) or not price.is_finite() or price <= 0:
        raise ValueError("Price must be a positive finite Decimal")


def format_price(price: Decimal) -> str:
    text = format(price, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text
