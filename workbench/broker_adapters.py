"""Broker adapter contracts with paper-only default behavior.

Live adapters are deliberately fail-closed until an official paper API client,
credential store, and integration test suite are configured for that broker.
"""

from dataclasses import dataclass
from typing import Any, Protocol


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


def adapter_catalog(paper_account):
    adapters = [
        PaperBrokerAdapter(paper_account),
        DisabledLiveAdapter("alpaca", "stocks-etfs"),
        DisabledLiveAdapter("interactive-brokers", "multi-asset"),
        DisabledLiveAdapter("futures", "futures"),
        DisabledLiveAdapter("crypto", "crypto"),
    ]
    return {adapter.name: adapter for adapter in adapters}