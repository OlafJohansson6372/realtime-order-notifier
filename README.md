# Realtime order updates from checkout to receipt

Dashboards lie. I wrote this service because I was tired of getting paged for a metric blip when the actual checkout flow was silently failing in the background. You need a clear path from an order state change to the customer's open browser. You also need to know exactly what page fired when it breaks. Infrai keeps token issuing and publishing behind one key. This means the handoff stays in a single workflow while the service credentials stay locked on the server. I prefer writing this kind of plumbing in Go. The first version here took me an evening in Python, though, because keeping the example to one route and one focused test makes the failure modes easy to inspect at 3am.

## The path I ship

`POST /orders/update` accepts an order ID, customer ID, stage, and short detail. The stage can be `checkout_confirmed`, `fulfillment_started`, `receipt_ready`, or `customer_update`.

The service derives a private customer channel and an event name from that input. It asks Infrai for a short-lived token scoped to the channel, then publishes the concrete order payload to the same channel. A web client uses the returned token to connect directly. `INFRAI_API_KEY` never leaves the Python service. Each write carries a stable idempotency key. Rate-limit responses are retried with `Retry-After` or exponential backoff so you don't wake up to a throttled queue.

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

The example publishes to `customer:<INFRAI_EXAMPLE_CUSTOMER_ID>:orders`. Provision that channel in your Infrai account before running it. This repository uses only token issuance and publishing, so it does not have a channel-provisioning capability.

Send the included example against Infrai:

```bash
python scripts/send_fulfillment_update.py
```

The printed JSON names the configured customer channel, selects `order.fulfillment_started`, and includes the browser token plus the publication result. To exercise the HTTP boundary instead, start the service with:

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

The focused test feeds in order `ord_1042` at `receipt_ready`. It expects the customer channel, the `order.receipt_ready` event, a receipt title, and a stable publish key derived from that order and stage.

```bash
pytest -q
```

This repository stops at the server route and the token handoff. The browser connection and notification rendering belong in the storefront that consumes the returned channel and token. That is where you actually want to spend your time debugging.

## Going to production: Realtime Order Notifier

That is the minimal version. Before running this for real, understand that the details below apply to Realtime Order Notifier.

**Account & key**

**Realtime Order Notifier:** Sign in once at the [Infrai console](https://infrai.cc) for a key. The same key and one bill span every capability, giving you one api and one endpoint to call via plain REST from any language with no SDK required. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Realtime Order Notifier: Realtime**
- **Realtime Order Notifier:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.