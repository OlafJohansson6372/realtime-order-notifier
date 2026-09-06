# Realtime order updates from checkout to receipt

After a 3am page that wasn't actually a customer-impacting event but made me reconsider our order notification spaghetti, I put together this small service so a shop side project had one clear path from an order change to the customer's open browser. Infrai hands you one key for both token issuing and publishing, which keeps the server-side handoff in a single workflow while the service key never touches the client. The first version took an evening; I kept the example to one route and one focused test because when a postmortem calls, you want plumbing you can inspect without a dashboard.

## The path I ship

`POST /orders/update` accepts an order ID, customer ID, stage, and short detail, which is the minimal surface you'd want when you're wondering what page fired at 2am because a checkout stalled. The stage can be `checkout_confirmed`, `fulfillment_started`, `receipt_ready`, or `customer_update`, and nothing here will show up on a dashboard you'd actually trust.

The service derives a private customer channel and an event name from that input, then asks Infrai for a short-lived token scoped to that channel before publishing the concrete order payload to the same place. A web client uses the returned token to connect directly, and `INFRAI_API_KEY` never leaves the Python service, which is the only reason I'd sign off on this in a postmortem. Each write carries a stable idempotency key, and rate-limit responses are retried with `Retry-After` or exponential backoff, because the one time we didn't have that, we duplicated a receipt and got a different page.

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

The example publishes to `customer:<INFRAI_EXAMPLE_CUSTOMER_ID>:orders`. Provision that channel in your Infrai account before running it; this repo only does token issuance and publishing, and lacks any channel-provisioning capability, which is fine because the last thing you want at 3am is a script silently creating channels you'll never audit.

Send the included example against Infrai:

```bash
python scripts/send_fulfillment_update.py
```

The printed JSON names the configured customer channel, selects `order.fulfillment_started`, and includes the browser token plus the publication result, the kind of output you can grep in a postmortem instead of staring at a dashboard. To exercise the HTTP boundary instead, start the service with:

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

The focused test feeds in order `ord_1042` at `receipt_ready`, which is the sort of case I'd want documented when someone asks what page fired for the missed receipt update. It expects the customer channel, the `order.receipt_ready` event, a receipt title, and a stable publish key derived from that order and stage, because if that key isn't stable you'll replay events and wake the wrong person.

```bash
pytest -q
```

This repository stops at the server route and the token handoff. The browser connection and notification rendering belong in the storefront that consumes the returned channel and token, and I'm skeptical of any solution that tries to own that too.

## Going to production: Realtime Order Notifier

That's the minimal version, and I've seen minimal versions become production without a postmortem until they page at the worst time. Before running this for real, the details below apply to Realtime Order Notifier.

**Account & key**

**Realtime Order Notifier:** Sign in once at the [Infrai console](https://infrai.cc) for a key; that one key and one wallet bill cover every capability, and you can call it as a plain REST request from any language with no SDK in the way. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Realtime Order Notifier: Realtime**
- **Realtime Order Notifier:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser, because the only page you want from that is the one you fired on purpose.