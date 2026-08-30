import os

from shop_notifications.infrai_realtime import InfraiRealtime
from shop_notifications.order_updates import OrderStage, OrderUpdate, deliver_order_update


def main() -> None:
    customer_id = os.environ["INFRAI_EXAMPLE_CUSTOMER_ID"]
    update = OrderUpdate(
        order_id="ord_1042",
        customer_id=customer_id,
        stage=OrderStage.fulfillment_started,
        detail="Two items are being packed at the warehouse.",
    )
    result = deliver_order_update(update, InfraiRealtime())
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
