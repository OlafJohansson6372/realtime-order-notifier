from typing import Any, Mapping

from shop_notifications.order_updates import OrderStage, OrderUpdate, deliver_order_update


class RecordingRealtime:
    def __init__(self) -> None:
        self.published: dict[str, Any] = {}

    def issue_customer_token(self, client_id: str, channel: str) -> Mapping[str, Any]:
        return {"token": "browser-session", "client_id": client_id, "channel": channel}

    def publish_order_event(self, **values: Any) -> Mapping[str, Any]:
        self.published = values
        return {"published": True}


def test_receipt_update_targets_customer_and_selects_receipt_event() -> None:
    realtime = RecordingRealtime()
    update = OrderUpdate(
        order_id="ord_1042",
        customer_id="cus_72",
        stage=OrderStage.receipt_ready,
        detail="Your receipt can now be viewed in the order screen.",
    )

    result = deliver_order_update(update, realtime)  # type: ignore[arg-type]

    assert result.channel == "customer:cus_72:orders"
    assert result.event == "order.receipt_ready"
    assert realtime.published["account_id"] == "cus_72"
    assert realtime.published["data"] == {
        "order_id": "ord_1042",
        "stage": "receipt_ready",
        "title": "Receipt is ready",
        "detail": "Your receipt can now be viewed in the order screen.",
    }
    assert realtime.published["idempotency_key"] == "order:ord_1042:receipt_ready"

