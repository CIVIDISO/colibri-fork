"""Deterministic paper-trading account for local strategy experiments."""

from datetime import datetime, timezone


class PaperAccount:
    def __init__(self, starting_cash=100_000.0, max_order_value=5_000.0):
        self.starting_cash = float(starting_cash)
        self.max_order_value = float(max_order_value)
        self.cash = self.starting_cash
        self.positions = {}
        self.orders = []

    def snapshot(self, prices=None):
        prices = prices or {}
        position_value = sum(
            position["quantity"] * float(prices.get(symbol, position["averagePrice"]))
            for symbol, position in self.positions.items()
        )
        return {
            "mode": "paper-only",
            "cash": round(self.cash, 2),
            "equity": round(self.cash + position_value, 2),
            "startingCash": round(self.starting_cash, 2),
            "maxOrderValue": round(self.max_order_value, 2),
            "positions": self.positions,
            "orders": self.orders[-100:],
        }

    def reset(self):
        self.cash = self.starting_cash
        self.positions = {}
        self.orders = []
        return self.snapshot()

    def order(self, symbol, side, quantity, price, data_lag_seconds=None, max_lag_seconds=None):
        symbol = str(symbol).strip().upper()
        side = str(side).strip().lower()
        quantity = float(quantity)
        price = float(price)
        if not symbol or side not in {"buy", "sell"}:
            raise ValueError("symbol and side=buy|sell are required")
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")
        if data_lag_seconds is not None and max_lag_seconds is not None and float(data_lag_seconds) > float(max_lag_seconds):
            raise ValueError("stale market data: paper order rejected")
        value = quantity * price
        if value > self.max_order_value:
            raise ValueError(f"paper risk limit: order value exceeds {self.max_order_value:.2f}")
        position = self.positions.get(symbol, {"quantity": 0.0, "averagePrice": price})
        if side == "buy":
            if value > self.cash:
                raise ValueError("insufficient paper cash")
            new_quantity = position["quantity"] + quantity
            position["averagePrice"] = ((position["quantity"] * position["averagePrice"]) + value) / new_quantity
            position["quantity"] = new_quantity
            self.cash -= value
        else:
            if quantity > position["quantity"]:
                raise ValueError("cannot short in the default paper account")
            position["quantity"] -= quantity
            self.cash += value
        if position["quantity"]:
            self.positions[symbol] = {"quantity": round(position["quantity"], 8), "averagePrice": round(position["averagePrice"], 8)}
        else:
            self.positions.pop(symbol, None)
        self.orders.append({
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "value": round(value, 2),
            "dataLagSeconds": round(float(data_lag_seconds), 3) if data_lag_seconds is not None else None,
            "status": "filled-paper",
        })
        return self.snapshot({symbol: price})