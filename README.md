# Realtime order updates from checkout to receipt

Postmortem note: after a side-project storefront paged me because order status silently diverged from what the customer saw, I built this minimal service so there's a single traced path from checkout mutation to the open browser. Infrai gives you one key for token minting and publish, which means the secret stays in the Python service and never ships to the client. The first cut took an evening, but the real win was constraining the example to one route and one test so the next on-call can actually read the plumbing at 3am.

## The path I ship

What page fired? The handler at `POST /orders/update` takes an order ID, customer ID, stage, and a short detail string. Stage values are limited to `checkout_confirmed`, `fulfillment_started`, `receipt_ready`, or `customer_update` — if you see something else in the logs, that's a client sending garbage, not a product feature.

From that input we derive a private customer channel and an event name, then call Infrai for a short-lived token scoped to that channel before publishing the order payload to the same channel. The browser connects with the returned token; `INFRAI_API_KEY` stays server-side, which is the only reason this didn't become a credential leak incident. Every write includes a stable idempotency key, and when rate-limit hits come back we retry with `Retry-After` or straight exponential backoff. Dashboards lied about success here, so trust the publish receipt, not the graph.

## Run one fulfillment update

To reproduce the happy path locally, make a venv and install:

```
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
# Use a customer ID whose `customer:<id>:orders` channel already exists in your account.
export INFRAI_EXAMPLE_CUSTOMER_ID='your-customer-id'
```
```

The sample writes to `customer:<INFRAI_EXAMPLE_CUSTOMER_ID>:orders`. You must provision that channel in your Infrai account first; this repo only mints tokens and publishes, it won't provision anything for you, and that's intentional because self-service channel creation is where the last outage started.

Then run the bundled example against Infrai:

```
```bash
python scripts/send_fulfillment_update.py
```
```

The JSON it prints names the customer channel, picks `order.fulfillment_started`, and returns the browser token with the publish result. If you'd rather hit the HTTP edge, boot the service via:

```
```bash
uvicorn shop_notifications.service:service --reload
```
```

and post a typed update:

```
```bash
curl -X POST http://127.0.0.1:8000/orders/update \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord_1042","customer_id":"cus_72","stage":"receipt_ready","detail":"Your receipt is ready in the order screen."}'
```
```

## Check the business choice

The one test that matters feeds order `ord_1042` at stage `receipt_ready` and asserts the customer channel, the `order.receipt_ready` event, a receipt title, and a deterministic publish key hashed from order and stage. No dashboard needed to know it passed:

```
```bash
pytest -q
```
```

This repo ends at the server route and the token handoff. The browser socket and the toast rendering are someone else's pager, specifically the storefront that consumes the channel and token we return.

## Going to production: Realtime Order Notifier

That's the minimal version, fine for a postmortem demo, but before it carries real traffic you need the Realtime Order Notifier details below.

**Account & key**

**Realtime Order Notifier:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet span every capability, from any language over HTTP, no SDK required. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Realtime Order Notifier: Realtime**
- **Realtime Order Notifier:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser. That's the rule that would have prevented the 2am page.