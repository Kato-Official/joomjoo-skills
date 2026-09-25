# Joomjoo, payments for AI agents

Joomjoo gives an agent three things it did not have: its own cards with a limit the person sets, the ability to clear the bank's security check (3DS) on its own, and its own browser with its own merchant logins so it can check out alone. Everything below runs against the live Joomjoo API with one API key.

## Setup, once

1. The person creates an API key in the Joomjoo console: https://app.joomjoo.com, Developer, API keys. Keys look like `mk_live_...` and are shown once.
2. The key lives in an environment variable, never in a file you commit:

```
export JOOMJOO_API_KEY="mk_live_your_key_here"
```

3. Base URL: `https://mooj-api-277196974190.us-central1.run.app`. Every request sends `Authorization: Bearer $JOOMJOO_API_KEY`. Amounts are US dollars. Every response carries a `request_id`; quote it when something goes wrong.

Prefer the SDK when the project has one: `npm install @joomjoo/sdk` (`import { Joomjoo } from "@joomjoo/sdk"`), `pip install joomjoo` (`from joomjoo import Joomjoo`). For an MCP client, `JOOMJOO_API_KEY=mk_live_... npx -y @joomjoo/mcp` exposes the same four tools.

## The four tools

### complete_purchase: hand Joomjoo the whole checkout (preferred)

Give a plain-English task, the merchant, and the most you may spend. Joomjoo opens the merchant in its own browser, uses the person's stored login when there is one, reaches the final review, mints a single-use card for the real total plus a small margin (never above the cap), pays, and clears 3DS itself. The card number never touches you.

```
curl -s https://mooj-api-277196974190.us-central1.run.app/v1/checkout \
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
curl -s https://mooj-api-277196974190.us-central1.run.app/v1/checkout/CHECKOUT_ID \
  -H "Authorization: Bearer $JOOMJOO_API_KEY"
```

Poll every 5 to 10 seconds. Statuses and what to do:

| status | meaning | what you do |
|---|---|---|
| queued, running, paying | Joomjoo is working | keep polling |
| needs_login | the merchant wants a signed-in session | tell the person to sign in once at the console (Developer, Connections), then start again |
| needs_answer | Joomjoo asked the person a choice (size, delivery slot) in the console | wait, keep polling |
| awaiting_approval | the final review is ready, `review_total` shows the shop's total (a display string such as "60.90 AED") | tell the person to approve in the console, keep polling |
| submitted | paid; `order_id` and `order_total` are set | done, report the order |
| canceled | the person stopped it | stop, nothing was charged |
| blocked | Joomjoo stopped (login wall, timeout, cap exceeded); `error_reason` says why | report the reason, do not retry blindly |
| error | the engine failed; nothing was charged and any card was closed | report, retry later with the same idempotency_key |

### issue_card: a real card with a cap, when you must pay yourself

```
curl -s https://mooj-api-277196974190.us-central1.run.app/v1/cards \
  -H "Authorization: Bearer $JOOMJOO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount": 20, "merchant": "namecheap", "single_use": true}'
```

Response: `id`, `brand`, `last4`, `exp_month`, `exp_year`, `spend_limit`, `single_use`, `status`, `spend_request_id`. Reveal the number only at the moment of use with `GET /v1/cards/{id}` (fields `number`, `cvc`, `exp`), never log it, never store it. Close a card you no longer need with `POST /v1/cards/{id}/close`; the unused reserve returns to the wallet. A 402 `insufficient_funds` means the wallet needs funding by the person.

### get_spend_status: did the card get charged

```
curl -s https://mooj-api-277196974190.us-central1.run.app/v1/spend/SPEND_REQUEST_ID \
  -H "Authorization: Bearer $JOOMJOO_API_KEY"
```

`status` is `not_started`, `authorized`, `cleared` or `declined`; `settled` is true once the bank cleared it, usually the next day.

## Rules, always

- Never spend above the cap you were given. One card per purchase; a single-use card locks itself after its first charge.
- Prefer `complete_purchase`. Only issue a card yourself when you truly must type it in.
- Pay only with the Joomjoo card; never a card saved on the merchant account. Confirm the last four digits before paying.
- 3DS is handled by Joomjoo. Never ask the person for an OTP.
- Send an `idempotency_key` on every checkout and retry with the same one.
- Never put the API key, a card number or a CVC in a log, a message, a file or a prompt.
- Errors carry a machine code (`invalid_api_key`, `expired_api_key`, `plan_limit`, `agent_paused`, `busy`, `checkout_not_found`) and a message written for the person; pass the message on as it is.

## Webhooks instead of polling

The person can register an endpoint in the console (Developer, Webhooks). Each delivery is `{"id", "type", "created", "data"}` with the `Joomjoo-Signature: t=<unix>,v1=<hex>` header, an HMAC-SHA256 of `t + "." + rawBody` with the endpoint's signing secret. Events: `card.authorized`, `card.cleared`, `card.declined`, `checkout.submitted`, `checkout.needs_login`, `checkout.blocked`.
