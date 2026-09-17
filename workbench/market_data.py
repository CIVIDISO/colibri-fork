"""Read-only market-data adapters for the local strategy lab."""

import json
import urllib.parse
import urllib.request


def yahoo_candles(symbol, period="6mo", interval="1d"):
    symbol = str(symbol).strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    allowed_intervals = {"1m", "5m", "15m", "30m", "60m", "1d", "1wk"}
    if interval not in allowed_intervals:
        raise ValueError("unsupported interval")
    query = urllib.parse.urlencode({"range": period, "interval": interval, "events": "history"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "ColibriStrategyLab/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise RuntimeError(f"market data request failed: {error}") from error
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError("market data returned no result")
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    candles = []
    for index, timestamp in enumerate(timestamps):
        close = (quote.get("close") or [None])[index]
        if close is not None:
            candles.append({"time": timestamp, "close": float(close)})
    if len(candles) < 3:
        raise RuntimeError("market data returned too few candles")
    return {"symbol": symbol, "interval": interval, "period": period, "candles": candles}