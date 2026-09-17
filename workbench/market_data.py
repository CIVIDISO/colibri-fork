"""Read-only market-data adapters for the local strategy lab."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import time
import urllib.parse
import urllib.request


DEFAULT_UNIVERSE = [
    "SPY", "QQQ", "DIA", "IWM", "TLT", "GLD", "SLV",
    "BTC-USD", "ETH-USD", "SOL-USD", "EURUSD=X", "JPY=X",
    "CL=F", "GC=F", "SI=F", "NG=F",
]


def yahoo_candles(symbol, period="6mo", interval="1d"):
    symbol = str(symbol).strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    allowed_intervals = {"1m", "5m", "15m", "30m", "60m", "1d", "1wk"}
    if interval not in allowed_intervals:
        raise ValueError("unsupported interval")
    query = urllib.parse.urlencode({"range": period, "interval": interval, "events": "history"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{query}"
    started = time.perf_counter()
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
    fetched_at = datetime.now(timezone.utc)
    latest_time = datetime.fromtimestamp(candles[-1]["time"], timezone.utc)
    lag_seconds = max(0.0, (fetched_at - latest_time).total_seconds())
    return {
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "candles": candles,
        "fetchedAt": fetched_at.isoformat(),
        "latestCandleAt": latest_time.isoformat(),
        "dataLagSeconds": round(lag_seconds, 3),
        "requestLatencyMs": round((time.perf_counter() - started) * 1000, 3),
    }


def scan_universe(symbols=None, period="1mo", interval="1d", max_workers=6, max_lag_seconds=None):
    universe = [str(symbol).strip().upper() for symbol in (symbols or DEFAULT_UNIVERSE) if str(symbol).strip()]
    universe = list(dict.fromkeys(universe))
    if not universe:
        raise ValueError("symbols are required")
    if len(universe) > 100:
        raise ValueError("universe is limited to 100 symbols per scan")
    started = time.perf_counter()
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=min(max(int(max_workers), 1), 8)) as pool:
        futures = {pool.submit(yahoo_candles, symbol, period, interval): symbol for symbol in universe}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                result = future.result()
                result["stale"] = max_lag_seconds is not None and result["dataLagSeconds"] > float(max_lag_seconds)
                results.append(result)
            except Exception as error:
                errors.append({"symbol": symbol, "error": str(error)})
    results.sort(key=lambda item: item["symbol"])
    return {
        "requested": universe,
        "results": results,
        "errors": errors,
        "summary": {
            "requested": len(universe),
            "received": len(results),
            "failed": len(errors),
            "stale": sum(1 for item in results if item.get("stale")),
            "scanLatencyMs": round((time.perf_counter() - started) * 1000, 3),
        },
    }