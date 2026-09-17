"""Broker adapter contracts with paper-only default behavior.

Live adapters are deliberately fail-closed until an official paper API client,
credential store, and integration test suite are configured for that broker.
"""

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
import urllib.error
import urllib.request

try:
    from .risk_engine import RiskEngine
except ImportError:
    from risk_engine import RiskEngine


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    price: float
    data_lag_seconds: float | None = None
    max_lag_seconds: float | None = None


class BrokerAdapter(Protocol):
    name: str
    asset_class: str
    mode: str

    def capabilities(self) -> dict[str, Any]: ...

    def account(self) -> dict[str, Any]: ...

    def submit_order(self, order: OrderRequest) -> dict[str, Any]: ...


class PaperBrokerAdapter:
    name = "paper"
    asset_class = "multi-asset"
    mode = "paper-only"

    def __init__(self, account):
        self.account_state = account

    def capabilities(self):
        return {
            "name": self.name,
            "assetClass": self.asset_class,
            "mode": self.mode,
            "marketData": True,
            "submitOrders": True,
            "liveMoney": False,
            "withdrawals": False,
        }

    def account(self):
        return self.account_state.snapshot()

    def submit_order(self, order):
        return self.account_state.order(
            order.symbol,
            order.side,
            order.quantity,
            order.price,
            order.data_lag_seconds,
            order.max_lag_seconds,
        )


class DisabledLiveAdapter:
    mode = "disabled"

    def __init__(self, name, asset_class):
        self.name = name
        self.asset_class = asset_class

    def capabilities(self):
        return {
            "name": self.name,
            "assetClass": self.asset_class,
            "mode": self.mode,
            "marketData": False,
            "submitOrders": False,
            "liveMoney": False,
            "withdrawals": False,
            "reason": "official paper adapter and credential policy required",
        }

    def account(self):
        raise RuntimeError(f"{self.name} live adapter is disabled")

    def submit_order(self, order):
        raise RuntimeError(f"{self.name} live adapter is disabled")


class AlpacaPaperAdapter:
    """Official Alpaca paper endpoint; credentials never leave this process."""

    name = "alpaca"
    asset_class = "stocks-etfs"
    mode = "paper-api"
    base_url = "https://paper-api.alpaca.markets"

    def __init__(self, risk=None):
        self.key = os.environ.get("APCA_API_KEY_ID", "").strip()
        self.secret = os.environ.get("APCA_API_SECRET_KEY", "").strip()
        self.risk = risk or RiskEngine()

    @property
    def enabled(self):
        return os.environ.get("ALPACA_PAPER_TRADING", "0").lower() in {"1", "true", "yes"} and bool(self.key and self.secret)

    def capabilities(self):
        return {
            "name": self.name,
            "assetClass": self.asset_class,
            "mode": self.mode if self.enabled else "disabled",
            "marketData": self.enabled,
            "submitOrders": self.enabled,
            "liveMoney": False,
            "withdrawals": False,
            "reason": None if self.enabled else "set ALPACA_PAPER_TRADING=1 and server-side Alpaca paper credentials",
        }

    def _request(self, path, method="GET", payload=None):
        if not self.enabled:
            raise RuntimeError("Alpaca paper adapter is disabled")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret, "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"Alpaca paper API {error.code}: {detail}") from error

    def account(self):
        account = self._request("/v2/account")
        positions = self._request("/v2/positions")
        return {
            "mode": self.mode,
            "cash": float(account.get("cash", 0)),
            "equity": float(account.get("equity", 0)),
            "positions": {item["symbol"]: {"quantity": float(item["qty"]), "averagePrice": float(item["avg_entry_price"])} for item in positions},
        }

    def submit_order(self, order):
        state = self.account()
        check = self.risk.check_order(
            order.symbol, order.side, order.quantity, order.price, state["positions"], state["equity"],
            order.data_lag_seconds, order.max_lag_seconds,
        )
        if not check["allowed"]:
            raise ValueError(f"Alpaca paper risk limit: {check['reason']}")
        return self._request("/v2/orders", "POST", {
            "symbol": order.symbol.upper(),
            "qty": str(order.quantity),
            "side": order.side.lower(),
            "type": "market",
            "time_in_force": "day",
        })


def adapter_catalog(paper_account):
    alpaca = AlpacaPaperAdapter()
    adapters = [
        PaperBrokerAdapter(paper_account),
        alpaca if alpaca.enabled else DisabledLiveAdapter("alpaca", "stocks-etfs"),
        DisabledLiveAdapter("interactive-brokers", "multi-asset"),
        DisabledLiveAdapter("futures", "futures"),
        DisabledLiveAdapter("crypto", "crypto"),
    ]
    return {adapter.name: adapter for adapter in adapters}