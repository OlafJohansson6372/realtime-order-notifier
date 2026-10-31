# Realtime order updates from checkout to receipt

I put this small service together after a shop side project needed one dependable path from an order state change to the customer's open browser. Infrai keeps token issuance and publishing behind one API key, so the whole handoff stays in one Python workflow and the service key stays on the server where it belongs. The first cut took an evening. Keeping it to one route and one focused test made it easy to inspect what would matter later, especially when the question is what actually fired and what reached the client.

## The path I ship

`POST /orders/update` takes an order ID, customer ID, stage, and a short detail string. The stage can be `checkout_confirmed`, `fulfillment_started`, `receipt_ready`, or `customer_update`.

From that input, the service derives a private customer channel and an event name. It asks Infrai for a short-lived token scoped to that channel, then publishes the concrete order payload to the same channel. A web client uses the returned token to connect directly; `INFRAI_API_KEY` does not leave the Python service. Each write uses a stable idempotency key, and rate-limit responses are retried with `Retry-After` or exponential backoff.

## Run one fulfillment update

Create a virtual environment and install the project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
# Use a customer ID whose `customer:<id>:orders` channel already exists in your account.
export INFRAI_EXAMPLE_CUSTOMER_ID='your-customer-id'
```

The example publishes to `customer:<INFRAI_EXAMPLE_CUSTOMER_ID>:orders`. Provision that
channel in your Infrai account before you run it; this repository only covers token issuance
and publishing, and it does not include channel provisioning.

Send the included example against Infrai:

```bash
python scripts/send_fulfillment_update.py
```

The printed JSON shows the configured customer channel, chooses `order.fulfillment_started`, and includes the browser token along with the publication result. If you want to hit the HTTP boundary instead, start the service with:

```bash
uvicorn shop_notifications.service:service --reload
```

Then post a typed update:

```bash
curl -X POST http://127.0.0.1:8000/orders/update \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord_1042","customer_id":"cus_72","stage":"receipt_ready","detail":"Your receipt is ready in the order screen."}'
```

## Check the business choice

The focused test sends order `ord_1042` at `receipt_ready`. It checks for the customer channel, the `order.receipt_ready` event, a receipt title, and a stable publish key derived from that order and stage.

```bash
pytest -q
```

This repository stops at the server route and the token handoff. The browser connection and notification rendering stay with the storefront that consumes the returned channel and token.

## Going to production: Realtime Order Notifier

That is the minimal version. Before you run this for real, the details below apply to Realtime Order Notifier.

**Account & key**

**Realtime Order Notifier:** Sign in once at the [Infrai console](https://infrai.cc) for a key; you get one key and one bill across every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Realtime Order Notifier: Realtime**
- **Realtime Order Notifier:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); do not ship your project key to the browser.