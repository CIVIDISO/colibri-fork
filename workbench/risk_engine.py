"""Deterministic order-risk gate shared by paper and future broker adapters."""

from datetime import datetime, timezone


class RiskEngine:
    def __init__(self, starting_equity=100_000.0, max_order_value=5_000.0,
                 max_position_value=20_000.0, max_daily_loss=2_000.0,
                 max_data_lag_seconds=300.0, allowed_symbols=None):
        self.starting_equity = float(starting_equity)
        self.max_order_value = float(max_order_value)
        self.max_position_value = float(max_position_value)
        self.max_daily_loss = float(max_daily_loss)
        self.max_data_lag_seconds = float(max_data_lag_seconds)
        self.allowed_symbols = {str(symbol).upper() for symbol in allowed_symbols} if allowed_symbols else None
        self.day = datetime.now(timezone.utc).date().isoformat()
        self.day_start_equity = self.starting_equity

    def _roll_day(self, equity):
        day = datetime.now(timezone.utc).date().isoformat()
        if day != self.day:
            self.day = day
            self.day_start_equity = float(equity)

    def check_order(self, symbol, side, quantity, price, positions, equity,
                    data_lag_seconds=None, max_lag_seconds=None):
        symbol = str(symbol).strip().upper()
        side = str(side).strip().lower()
        quantity = float(quantity)
        price = float(price)
        equity = float(equity)
        self._roll_day(equity)
        value = quantity * price
        position_quantity = float((positions.get(symbol) or {}).get("quantity", 0.0))
        projected_quantity = position_quantity + quantity if side == "buy" else position_quantity - quantity
        projected_position_value = abs(projected_quantity * price)
        lag_limit = self.max_data_lag_seconds if max_lag_seconds is None else float(max_lag_seconds)
        if not symbol or side not in {"buy", "sell"}:
            return {"allowed": False, "reason": "invalid symbol or side"}
        if self.allowed_symbols is not None and symbol not in self.allowed_symbols:
            return {"allowed": False, "reason": "symbol is outside the configured universe"}
        if quantity <= 0 or price <= 0:
            return {"allowed": False, "reason": "quantity and price must be positive"}
        if value > self.max_order_value:
            return {"allowed": False, "reason": "order exceeds maximum order value"}
        if projected_position_value > self.max_position_value:
            return {"allowed": False, "reason": "projected position exceeds maximum position value"}
        if side == "sell" and quantity > position_quantity:
            return {"allowed": False, "reason": "shorting is disabled"}
        if data_lag_seconds is not None and float(data_lag_seconds) > lag_limit:
            return {"allowed": False, "reason": "market data is stale"}
        if self.day_start_equity - equity >= self.max_daily_loss:
            return {"allowed": False, "reason": "maximum daily loss reached"}
        return {"allowed": True, "reason": "risk checks passed"}

    def snapshot(self, equity):
        self._roll_day(equity)
        return {
            "day": self.day,
            "dayStartEquity": round(self.day_start_equity, 2),
            "currentEquity": round(float(equity), 2),
            "dailyLoss": round(max(0.0, self.day_start_equity - float(equity)), 2),
            "maxDailyLoss": round(self.max_daily_loss, 2),
            "maxOrderValue": round(self.max_order_value, 2),
            "maxPositionValue": round(self.max_position_value, 2),
            "maxDataLagSeconds": round(self.max_data_lag_seconds, 2),
        }