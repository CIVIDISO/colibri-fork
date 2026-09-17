"""Small deterministic long-only strategy backtester."""


def _sma(values, period):
    return sum(values[-period:]) / period if len(values) >= period else None


def run_sma_backtest(candles, fast=10, slow=30, starting_cash=100_000.0):
    if not isinstance(candles, list) or len(candles) < 3:
        raise ValueError("at least three candles are required")
    fast, slow = int(fast), int(slow)
    if fast < 2 or slow <= fast:
        raise ValueError("slow period must be greater than fast period >= 2")
    prices = [float(candle["close"]) for candle in candles]
    cash = float(starting_cash)
    quantity = 0.0
    entry = None
    trades = []
    equity_curve = []
    for index, price in enumerate(prices):
        previous_fast = _sma(prices[:index], fast)
        previous_slow = _sma(prices[:index], slow)
        current_fast = _sma(prices[: index + 1], fast)
        current_slow = _sma(prices[: index + 1], slow)
        if current_fast is not None and current_slow is not None:
            if quantity == 0 and previous_fast is not None and previous_slow is not None and previous_fast <= previous_slow < current_fast:
                quantity = cash / price
                cash = 0.0
                entry = price
                trades.append({"side": "buy", "index": index, "price": price, "quantity": quantity})
            elif quantity and previous_fast is not None and previous_slow is not None and previous_fast >= previous_slow > current_fast:
                cash = quantity * price
                trades.append({"side": "sell", "index": index, "price": price, "quantity": quantity, "return": price / entry - 1})
                quantity, entry = 0.0, None
        equity_curve.append(cash + quantity * price)
    if quantity:
        cash = quantity * prices[-1]
        trades.append({"side": "sell", "index": len(prices) - 1, "price": prices[-1], "quantity": quantity, "return": prices[-1] / entry - 1})
    ending_equity = cash
    peak = float(starting_cash)
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
    completed = [trade["return"] for trade in trades if trade["side"] == "sell"]
    return {
        "strategy": "sma-crossover-long-only",
        "fast": fast,
        "slow": slow,
        "startingEquity": round(float(starting_cash), 2),
        "endingEquity": round(ending_equity, 2),
        "return": round(ending_equity / float(starting_cash) - 1, 6),
        "maxDrawdown": round(max_drawdown, 6),
        "trades": trades,
        "completedTrades": len(completed),
        "winRate": round(sum(1 for value in completed if value > 0) / len(completed), 6) if completed else 0.0,
    }