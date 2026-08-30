from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .infrai_realtime import InfraiError, InfraiRealtime
from .order_updates import DeliveryResult, OrderUpdate, deliver_order_update

service = FastAPI(title="Shop order notifications")


@service.exception_handler(InfraiError)
async def infrai_error_response(_: Request, error: InfraiError) -> JSONResponse:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return JSONResponse(
        status_code=status,
        content={"error": {"code": error.code, "detail": dict(error.detail)}},
    )


@service.post("/orders/update", response_model=DeliveryResult)
def push_order_update(update: OrderUpdate) -> DeliveryResult:
    return deliver_order_update(update, InfraiRealtime())

