from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, Field

from .infrai_realtime import InfraiRealtime


class OrderStage(str, Enum):
    checkout_confirmed = "checkout_confirmed"
    fulfillment_started = "fulfillment_started"
    receipt_ready = "receipt_ready"
    customer_update = "customer_update"


class OrderUpdate(BaseModel):
    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    stage: OrderStage
    detail: str = Field(min_length=1, max_length=240)


class DeliveryResult(BaseModel):
    channel: str
    event: str
    browser_token: Mapping[str, Any]
    publication: Mapping[str, Any]


def notification_copy(update: OrderUpdate) -> tuple[str, str]:
    event_by_stage = {
        OrderStage.checkout_confirmed: ("order.checkout_confirmed", "Order confirmed"),
        OrderStage.fulfillment_started: ("order.fulfillment_started", "Packing has started"),
        OrderStage.receipt_ready: ("order.receipt_ready", "Receipt is ready"),
        OrderStage.customer_update: ("order.customer_update", "Order update"),
    }
    return event_by_stage[update.stage]


def deliver_order_update(update: OrderUpdate, realtime: InfraiRealtime) -> DeliveryResult:
    channel = f"customer:{update.customer_id}:orders"
    event, title = notification_copy(update)
    browser_token = realtime.issue_customer_token(update.customer_id, channel)
    publication = realtime.publish_order_event(
        channel=channel,
        event=event,
        data={
            "order_id": update.order_id,
            "stage": update.stage.value,
            "title": title,
            "detail": update.detail,
        },
        account_id=update.customer_id,
        idempotency_key=f"order:{update.order_id}:{update.stage.value}",
    )
    return DeliveryResult(
        channel=channel,
        event=event,
        browser_token=browser_token,
        publication=publication,
    )

