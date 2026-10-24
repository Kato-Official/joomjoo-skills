---
name: joomjoo
description: Give an AI agent its own payment card and let it buy things safely. Use when the agent must pay for something online (a domain, a subscription, an order, a purchase on any website), needs a virtual card with a spend limit, has to complete a checkout on a merchant site, or has to check whether a purchase went through. Joomjoo issues the card, drives the checkout in a real browser, clears the bank's 3DS check, and never spends above the cap.
---

# Joomjoo, payments for AI agents

Joomjoo gives an agent three things it did not have: its own cards with a limit the person sets, the ability to clear the bank's security check (3DS) on its own, and its own browser with its own merchant logins so it can check out alone. Everything below runs against the live Joomjoo API with one API key.

## Setup, once

1. The person creates an API key in the Joomjoo console: https://app.joomjoo.com, Developer, API keys. Keys look like `mk_live_...` and are shown once.
2. The key lives in an environment variable, never in a file you commit:

```
export JOOMJOO_API_KEY="mk_live_your_key_here"
```

3. Base URL: `https://api.joomjoo.com`. Every request sends `Authorization: Bearer $JOOMJOO_API_KEY`. Amounts are US dollars. Every response carries a `request_id`; quote it when something goes wrong.

Prefer the SDK when the project has one: `npm install @joomjoo/sdk` (`import { Joomjoo } from "@joomjoo/sdk"`), `pip install joomjoo` (`from joomjoo import Joomjoo`). For an MCP client, `JOOMJOO_API_KEY=mk_live_... npx -y @joomjoo/mcp` exposes the same six tools.

## The six tools

### complete_purchase: hand Joomjoo the whole checkout (preferred)

Give a plain-English task, the merchant, and the most you may spend. Joomjoo opens the merchant in its own browser, uses the person's stored login when there is one, reaches the final review, mints a single-use card for the real total plus a small margin (never above the cap), pays, and clears 3DS itself. The card number never touches you.

```
curl -s https://api.joomjoo.com/v1/checkout \
  -H "Authorization: Bearer $JOOMJOO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "buy the domain example.click for 1 year", "merchant": "namecheap", "amount": 20, "confirm_pay": false, "idempotency_key": "order-2026-09-25-001"}'
```

Response: `{"checkout_id": "...", "status": "queued", "confirm_pay": false, "host": "www.namecheap.com", "poll": "/v1/checkout/{id}"}`.

- `confirm_pay: false` (default): the run stops at the final review and waits for the person's yes in the Joomjoo console. `confirm_pay: true`: pay without a human yes, up to the cap. The person's own approval mode for their agent can only make this stricter; the response's `confirm_pay` says what was granted.
- `idempotency_key`: your own reference. A retry with the same key returns the same checkout instead of a second purchase. Always send one.
- `start_url`: the exact https page to open, when the merchant has no stored login on the account yet. A 400 `site_required` or `site_ambiguous` means: pass `start_url`, or ask the person to connect the merchant once in the console (Developer, Connections).

### get_checkout_status: poll until a terminal status

```
curl -s https://api.joomjoo.com/v1/checkout/CHECKOUT_ID \
  -H "Authorization: Bearer $JOOMJOO_API_KEY"
```

Poll every 5 to 10 seconds. Statuses and what to do:

| status | meaning | what you do |
|---|---|---|
| queued, running, paying | Joomjoo is working | keep polling |
| needs_login | the merchant wants a signed-in session | read `login_check`, `login_url` and `connect_url` on the status: `signed_out` or `unknown` means the person signs in once at `connect_url` (the agent never types a password), then start again on the same connection; `passkey_password` means the person is signed in and the merchant wants the password once so Joomjoo can add its passkey (type it at `connect_url` and start again, or `POST /v1/connections/{id}/passkey` with `{"action": "skip"}` to keep the plain session) |
| needs_answer | Joomjoo asked the person a choice (size, delivery slot) in the console | wait, keep polling |
| awaiting_approval | the final review is ready, `review_total` shows the shop's total (a display string such as "60.90 AED") | tell the person to approve in the console, keep polling |
| submitted | paid; `order_id` and `order_total` are set | done, report the order |
| canceled | the person stopped it | stop, nothing was charged |
| blocked | Joomjoo stopped (login wall, timeout, cap exceeded); `error_reason` says why | report the reason, do not retry blindly |
| error | the engine failed; nothing was charged and any card was closed | report, retry later with the same idempotency_key |

### issue_card: a real card with a cap, when you must pay yourself

```
curl -s https://api.joomjoo.com/v1/cards \
  -H "Authorization: Bearer $JOOMJOO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount": 20, "merchant": "namecheap", "single_use": true}'
```

Response: `id`, `brand`, `last4`, `exp_month`, `exp_year`, `spend_limit`, `single_use`, `status`, `spend_request_id`. Reveal the number only at the moment of use with `GET /v1/cards/{id}` (fields `number`, `cvc`, `exp`), never log it, never store it. Close a card you no longer need with `POST /v1/cards/{id}/close`; the unused reserve returns to the wallet. A 402 `insufficient_funds` means the wallet needs funding by the person.

### get_spend_status: did the card get charged

```
curl -s https://api.joomjoo.com/v1/spend/SPEND_REQUEST_ID \
  -H "Authorization: Bearer $JOOMJOO_API_KEY"
```

`status` is `not_started`, `authorized`, `cleared` or `declined`; `settled` is true once the bank cleared it, usually the next day.

### get_wallet: what the account can spend

```
curl -s https://api.joomjoo.com/v1/wallet \
  -H "Authorization: Bearer $JOOMJOO_API_KEY"
```

Returns `balance`, `available` (free to assign to a new card), `reserved` (on open cards) and `pending` (bank money not landed yet), in dollars, plus display strings. Check it when a 402 `insufficient_funds` is possible.

### create_topup_link: when the wallet is short

```
curl -s https://api.joomjoo.com/v1/wallet/funding-sessions \
  -H "Authorization: Bearer $JOOMJOO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50, "success_url": "https://yourapp.example/funded"}'
```

Returns a Stripe Checkout `url`. Give it to the person; Stripe takes a card or stablecoin; the wallet is credited the moment Stripe confirms (webhook `money.funded`). Never type a card yourself, never ask the person for their card number. For a bank transfer, `POST /v1/wallet/bank-transfers` with `amount` and `rail` (`ach`, `wire_domestic`, `wire_international`, `uae_local`) returns the account to send to and a `reference_code` for the memo; the money is pending until it lands.

## Rules, always

- Never spend above the cap you were given. One card per purchase; a single-use card locks itself after its first charge.
- Prefer `complete_purchase`. Only issue a card yourself when you truly must type it in.
- Pay only with the Joomjoo card; never a card saved on the merchant account. Confirm the last four digits before paying.
- 3DS is handled by Joomjoo. Never ask the person for an OTP.
- Send an `idempotency_key` on every checkout and retry with the same one.
- Never put the API key, a card number or a CVC in a log, a message, a file or a prompt.
- Errors carry a machine code (`invalid_api_key`, `expired_api_key`, `plan_limit`, `agent_paused`, `busy`, `checkout_not_found`) and a message written for the person; pass the message on as it is.

## Webhooks instead of polling

The person can register an endpoint in the console (Developer, Webhooks). Each delivery is `{"id", "type", "created", "data"}` with the `Joomjoo-Signature: t=<unix>,v1=<hex>` header, an HMAC-SHA256 of `t + "." + rawBody` with the endpoint's signing secret. Events: `card.authorized`, `card.cleared`, `card.declined`, `checkout.submitted`, `checkout.needs_login`, `checkout.blocked`, `money.funded`.


## Merchant logins and the Joomjoo passkey

A connection is the person's signed-in session at one merchant. `POST /v1/connections` gives a `connect_url` where the person signs in once; `POST /v1/connections/{id}/complete` saves it. On merchants that take passkeys (Amazon first), Joomjoo then adds its own passkey to that account the next time a checkout runs, and from then on every checkout signs in by itself, even after the merchant expires the session: `GET /v1/connections` shows `layer: "passkey"` and `passkey_status: "connected"` (or `connected_unmanaged` when the merchant shows no identifier Joomjoo can use to delete the entry remotely). The agent does nothing for this. `DELETE /v1/connections/{id}` disconnects: the key is destroyed first, then the entry is removed at the merchant when Joomjoo can (`passkey_status` ends `removed` or `removed_locally`, the latter meaning the person removes the "Joomjoo-..." entry in the merchant's security settings). A checkout's `login_layer` says `passkey` or `session`.

## The person's own card (connected, not issued)

A cardholder can connect one of their OWN credit or debit cards once, behind a passkey, and the agent pays with it after they approve each purchase on their phone. `POST /v1/cards/connect` returns a one-hour, single-use `connect_url`; send it to the cardholder, never open it yourself. `GET /v1/cards` lists it with `source: "own"`. To pay with it, pass `own_card_id` on `POST /v1/checkout`: the checkout stops at the review with status `needs_card_approval` and an `approval_url` (also on the `checkout.needs_card_approval` event); give that link to the cardholder, who types the security code and confirms with their passkey. `confirm_pay` cannot skip that approval, and the bank's own check (3-D Secure) on a connected card is the cardholder's to complete on the agent's screen. `DELETE /v1/cards/{id}` removes a connected card. A connected card has no cap beyond the approved order, nothing is issued and nothing is prepaid.
