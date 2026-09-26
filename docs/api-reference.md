# Joomjoo API reference

The same reference the Joomjoo console shows under Developer, Docs. Regenerated from the console copy whenever the API changes.

# Joomjoo API

The payment layer for AI agents. Issue a real, capped virtual card and either use it yourself or hand the whole checkout to Joomjoo. Card controls, 3DS, and fraud caps are handled for you.

The Joomjoo API is organized around REST. It has predictable, resource-oriented URLs, accepts JSON request bodies, returns JSON responses, and uses standard HTTP verbs and status codes. Every response includes an `X-Mooj-Request-Id` header (also echoed as `request_id` in the body) so any call can be traced.

|  |  |
| --- | --- |
| Base URL | `https://api.joomjoo.com` |
| Version | All endpoints are under `/v1`. |
| Auth | Bearer API key in the `Authorization` header. |
| Content type | `application/json` for all request bodies. |

Amounts in requests are in **US dollars** (e.g. `"amount": 20` means $20.00). Card and wallet math is exact to the cent internally.

---

## Authentication 

Authenticate every request with your secret API key. Create and manage keys in the Joomjoo console under **Developer → API keys**. Keys look like `mk_live_...` and are shown only once at creation, so store yours securely.

Send the key as a bearer token. Keep it server-side and never commit it to source control; the examples below read it from an environment variable.

Shell

```
export JOOMJOO\_API\_KEY="YOUR\_API\_KEY"
# every request sends the bearer header:
curl https://api.joomjoo.com/v1/spend/example \
-H "Authorization: Bearer $JOOMJOO\_API\_KEY"
```

A missing or invalid key returns 401 `missing_api_key` or `invalid_api_key`. See [Errors](#errors) for the full list.

---

## Quickstart 

Issue your first card in one call. The response comes back with a real, usable card capped at the amount you set.

cURL

```
curl https://api.joomjoo.com/v1/cards \
-H "Authorization: Bearer $JOOMJOO\_API\_KEY" \
-H "Content-Type: application/json" \
-d '{"amount": 20, "merchant": "namecheap", "single\_use": true}'
```

200 Response

```
{
"id": "card\_8f2a...",
"brand": "visa",
"last4": "8339",
"exp\_month": 4,
"exp\_year": 2033,
"spend\_limit": 20,
"single\_use": true,
"status": "ACTIVE",
"spend\_request\_id": "spr\_1c9d..."
}
```

From here you can [reveal the card](#reveal-card) to use it yourself, or skip cards entirely and let Joomjoo [complete a checkout](#complete-a-checkout) for you.

---

## Guide: Give your agent a card 

The safest way to let an agent spend is a single-use card capped at exactly what the purchase should cost. It auto-freezes after the first charge, so it cannot be reused or over-spent.

1. **Issue** a card with [`POST /v1/cards`](#create-card), setting `single_use: true` and `amount` to the cap.
2. **Reveal** the number with [`GET /v1/cards/{id}`](#reveal-card) only at the moment of use.
3. **Check** the result with [`GET /v1/spend/{spend_request_id}`](#get-spend) (`authorized` / `cleared` / `declined`).

To teach your agent these calls in one paste, grab a ready tool file from **Developer → Agent skills** (Claude, OpenAI, and Gemini schemas). See [Agent skills](#agent-skills).

## Guide: Complete a checkout 

Hand Joomjoo a plain-English task and a spend cap. Joomjoo mints a card, drives the merchant checkout in a real browser, auto-accepts 3DS, and pays. This is asynchronous: you get a `checkout_id` back, then poll it.

cURL

```
# 1. start the checkout (confirm\_pay:false = dry run, stops at review)
curl https://api.joomjoo.com/v1/checkout \
-H "Authorization: Bearer $JOOMJOO\_API\_KEY" \
-H "Content-Type: application/json" \
-d '{"task":"buy the domain joomjoo.click for 1 year","merchant":"namecheap","amount":20,"confirm\_pay":false}'
# 2. poll until it finishes
curl https://api.joomjoo.com/v1/checkout/CHECKOUT\_ID \
-H "Authorization: Bearer $JOOMJOO\_API\_KEY"
```

Set `confirm_pay: true` to have Joomjoo pay autonomously, up to the cap. Poll `status` until it reaches a terminal state:

queued
running
needs\_login
needs\_answer
awaiting\_approval
paying
submitted
canceled
blocked
error

`submitted`, `canceled`, `blocked` and `error` are terminal. `awaiting_approval` means the run reached the final review and is waiting for the account owner's yes in the Joomjoo console (or `confirm_pay: true`, within the agent's own approval mode). `needs_answer` is a choice the account owner is being asked in the console.

If `status` is `needs_login`, the merchant requires a signed-in session. Set up a reusable login once with [Connections](#connect-merchant), then pass its `connection_id` to the checkout.

## Guide: Connect a merchant login 

Some merchants require an account. A **connection** is a reusable, isolated login your users complete once in a hosted browser session; every future checkout on that connection is already signed in.

1. [`POST /v1/connections`](#create-connection) returns a `connect_url`. Open it so the user signs in on the merchant's own page (Joomjoo never sees the password).
2. [`POST /v1/connections/{id}/complete`](#complete-connection) persists the login. The connection becomes connected.
3. Pass `connection_id` to [`POST /v1/checkout`](#create-checkout) and the run executes signed-in as that user.

## Guide: Handle events 

Instead of polling, get events pushed to your server the moment they happen. Register an endpoint in the Joomjoo console (Developer -> Webhooks); Joomjoo sends a signed POST for each event.

### Events

card.authorized
card.cleared
card.declined
checkout.submitted
checkout.needs\_login
checkout.blocked
money.funded

`money.funded` fires when a top-up lands in the wallet, by card, stablecoin or bank, with `amount`, `method` and `balance_after`.

Each delivery is JSON: `{ "id", "type", "created", "data": { ... } }`.

### Verify the signature

Every request carries a `Joomjoo-Signature: t=<unix>,v1=<hex>` header (the same value is also sent as `Mooj-Signature` for integrations written before the rename). Recompute it with your endpoint's signing secret (shown once when you create the endpoint) and compare, so you know the event really came from Joomjoo.

Node, verify

```
import crypto from "node:crypto";
function verify(rawBody, header, secret) {
const [t, v1] = header.split(",").map(p => p.split("=")[1]);
const expected = crypto.createHmac("sha256", secret)
.update(`${t}.${rawBody}`).digest("hex");
return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(v1));
}
```

Failed deliveries retry automatically. You can still poll [`GET /v1/spend/{id}`](#get-spend) and [`GET /v1/checkout/{id}`](#get-checkout) at any time.

---

# API reference

Every live endpoint, its parameters, and an example response. All requests require the `Authorization: Bearer` header from [Authentication](#authentication).

## Cards 

### Create a card

POST/v1/cards

Mint a virtual card capped at `amount` (USD) for a merchant.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| amount | number | yes | Spend cap in US dollars. Per-card ceiling is $5,000. |
| merchant | string | yes | Merchant the card is for, e.g. `namecheap`. |
| single\_use | boolean | no | Default `true`. Auto-freezes after the first charge. |
| network | string | no | `auto` (default), `visa`, or `mastercard`. |
| card\_name | string | no | Label for the card in your dashboard. |

200 Response

```
{
"id": "card\_8f2a...",
"brand": "visa",
"last4": "8339",
"exp\_month": 4,
"exp\_year": 2033,
"spend\_limit": 20,
"single\_use": true,
"status": "ACTIVE",
"spend\_request\_id": "spr\_1c9d..."
}
```

Returns 402 `insufficient_funds` if the cap exceeds your available wallet balance.

### Reveal a card

GET/v1/cards/{id}

Return the full card number, CVC, and expiry. Reveal only at the moment of use; Joomjoo never logs the PAN.

200 Response

```
{
"id": "card\_8f2a...",
"last4": "8339",
"number": "4775xxxxxxxx8339",
"number\_formatted": "4775 xxxx xxxx 8339",
"cvc": "123",
"exp": "04/33"
}
```

### Close a card

POST/v1/cards/{id}/close

Close a card and release any unused reserve back to your wallet.

200 Response

```
{
"id": "card\_8f2a...",
"status": "closed",
"released\_display": "$20.00",
"available\_to\_issue\_display": "$140.00"
}
```

## Spend 

### Get spend status

GET/v1/spend/{spend\_request\_id}

Check whether a card issued with [`POST /v1/cards`](#create-card) was charged. Pass the `spend_request_id` from the create response.

not\_started
authorized
cleared
declined

200 Response

```
{
"spend\_request\_id": "spr\_1c9d...",
"merchant": "namecheap",
"decision": "APPROVED",
"status": "cleared",
"settled": true,
"amount": 1.98
}
```

## Checkout 

### Start a checkout

POST/v1/checkout

Asynchronous. Joomjoo mints a card, drives the merchant checkout, handles 3DS, and (if authorized) pays. Returns a `checkout_id` to poll.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| task | string | yes | Plain-English description of what to buy. |
| merchant | string | yes | Merchant to buy from. |
| amount | number | yes | Maximum USD to spend (becomes the card cap). |
| confirm\_pay | boolean | no | Default false: the run stops at the final review and waits for the account owner's yes. true: pay without a human yes, up to the cap. The agent's own approval mode can only make this stricter; the response's `confirm_pay` says what was granted. |
| idempotency\_key | string | no | Your own key for this checkout. A retry with the same key returns the same checkout instead of starting a second run. |
| connection\_id | string | no | Run signed-in on a [connection](#connections). Auto-matched by merchant if omitted. |
| card\_holder\_name | string | no | Name on the card for the run. |
| start\_url | string | no | URL or bare domain to open first. |

200 Response

```
{
"checkout\_id": "run\_7a1e...",
"status": "queued",
"poll": "/v1/checkout/run\_7a1e..."
}
```

### Get checkout status

GET/v1/checkout/{checkout\_id}

200 Response

```
{
"checkout\_id": "run\_7a1e...",
"status": "awaiting\_approval",
"task": "buy the domain joomjoo.click for 1 year",
"merchant": "namecheap",
"amount": 20,
"card\_last4": "4775",
"host": "www.namecheap.com",
"review\_total": "1.98 USD",
"order\_id": null,
"order\_total": null,
"needs\_login": false,
"error\_reason": null
}
```

## Connections 

### Create a connection

POST/v1/connections

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| merchant | string | yes | Merchant to connect a login for. |
| user\_ref | string | no | Your own reference for the end user this login belongs to. |

200 Response

```
{
"connection\_id": "conn\_5d2b...",
"connect\_url": "https://connect.browserbase.com/...",
"status": "pending"
}
```

### Complete a connection

POST/v1/connections/{id}/complete

Call after the user has signed in at the `connect_url`. Persists the login; status becomes `connected`.

### List / get connections

GET/v1/connections

GET/v1/connections/{id}

List all connections, or poll a single connection's status (`pending` / `connected`).

## Wallet 

The wallet every card and checkout draws on. A top-up always ends on Stripe's own page, so a card number never passes through the API or through you.

### Read the wallet

GET/v1/wallet

200 Response

```
{
"currency": "USD",
"balance": 32.96,
"available": 22.96,
"reserved": 10,
"pending": 0,
"balance\_display": "$32.96",
"available\_display": "$22.96"
}
```

`available` is what a new card can be capped at. `reserved` sits on open cards. `pending` is declared bank money that has not landed yet and cannot be spent.

### Top up by card or stablecoin

POST/v1/wallet/funding-sessions

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| amount | number | yes | Dollars to add. |
| success\_url | string | no | Where the person lands after paying, https. Defaults to the Joomjoo console. |
| cancel\_url | string | no | Where the person lands if they cancel, https. |

200 Response

```
{
"funding\_session\_id": "cs\_live\_...",
"url": "https://checkout.stripe.com/c/pay/...",
"amount": 50,
"status": "open"
}
```

Open `url` for the person. Stripe offers card and stablecoin. The wallet is credited the moment Stripe confirms; subscribe to `money.funded` to know, or poll `GET /v1/wallet`.

Returns 402 `wallet_limit`, `funding_budget_reached` or `funding_unavailable` when a fence refuses the amount; the message says which.

### Top up by bank transfer

POST/v1/wallet/bank-transfers

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| amount | number | yes | Amount in the transfer currency. |
| rail | string | no | `ach` (default), `wire_domestic`, `wire_international` or `uae_local`. |
| currency | string | no | `USD`, or `AED` for `uae_local`. Defaults by rail. |
| sent\_on | string | no | `yyyy-MM-dd`, the day the transfer was sent. |
| sender\_bank\_name, sender\_account\_name, sender\_reference | string | no | What the bank statement will show, so the transfer is matched faster. |
| idempotency\_key | string | no | Your own key; a retry returns the same declaration. |

200 Response

```
{
"funding\_event\_id": "...",
"status": "pending",
"amount": 500,
"currency": "USD",
"rail": "wire\_domestic",
"reference\_code": "7K2QW9PD",
"pending\_balance": 500,
"instructions": { "beneficiary\_name": "Joomjoo, LLC", "account\_number": "...", "routing\_number": "...", "reference": "7K2QW9PD" }
}
```

Show the person `instructions`. The reference code goes in the transfer memo. The money is pending until it lands, then `money.funded` fires and the balance moves.

## Errors 

Joomjoo uses conventional HTTP status codes. The body carries a machine-readable string and a `request_id`.

| Status | Meaning |
| --- | --- |
| 200 | Success. |
| 400 | `invalid_request`, `invalid_amount`: a required field is missing or invalid. `connection_not_found`: no connected connection with that id. `site_required`, `site_ambiguous`: the account has no stored login for that merchant, or several; pass `start_url`. `agent_required`: the account has several agents and none was named. |
| 401 | `missing_api_key`, `invalid_api_key`, `expired_api_key` (the body carries `expired_at`). |
| 402 | `insufficient_funds`: the requested cap exceeds the available wallet balance. `plan_limit`: the plan's cards a month or per-card cap is reached. `wallet_limit`, `funding_budget_reached`, `funding_unavailable`: a wallet fence refused a top-up. |
| 404 | `card_not_found`, `spend_not_found`, `checkout_not_found`, `connection_not_found`, `account_not_found`: not found, or not owned by your account. |
| 409 | `agent_paused`: resume the agent first. `busy`: the merchant session is busy with another run, retry shortly. |
| 502 | `card_issue_failed`, `reveal_failed`, `close_failed`, `spend_status_failed`, `checkout_start_failed`, `connect_start_failed`, `enqueue_failed`: an upstream step failed; the message says which. Retry with the same `idempotency_key`. |
| 500 | `server_error`, `checkout_create_failed`. |

Error body

```
{
"error": "insufficient\_funds",
"request\_id": "req\_a1b2c3"
}
```

---

## Postman collection 

Prefer to click instead of curl? Import the Joomjoo collection into Postman and every endpoint is ready to run.

Import URL

```
https://joomjoo.com/docs/joomjoo.postman\_collection.json
```

1. In Postman, choose **Import** and paste the URL above (or download and drop the file in).
2. Open the collection's **Variables** and set `apiKey` to your `mk_live_` key. `baseUrl` is already filled.
3. Run **Cards → Create a card** to get your first card. The other requests reuse the same variables.

The collection sets `Authorization: Bearer {{apiKey}}` at the collection level, so every request inherits your key automatically.

## Agent skills 

Everything below is also one public repository, [github.com/Kato-Official/joomjoo-skills](https://github.com/Kato-Official/joomjoo-skills), with the full reference and the Postman collection. Install the skill into any agent (Claude Code, Codex, Cursor, Gemini CLI and more) with `npx skills add Kato-Official/joomjoo-skills`.

Teach your agent to use Joomjoo in one paste. The Joomjoo console (**Developer → Agent skills**) ships ready tool files for each stack:

Claude Code / AGENTS.md

Two files: `SKILL.md` (save as `.claude/skills/joomjoo/SKILL.md`, Claude Code loads it by itself) and `AGENTS.md` (drop next to your agent's code; Codex, Cursor and most agents read it). Both carry the four tools, the ten checkout statuses and the rules.

Anthropic tool-use

JSON tool schema for the Claude API.

OpenAI function tools

JSON tool schema for the OpenAI API.

Google Gemini

Function declarations for the Gemini API.

Each file exposes the same four tools: `issue_card`, `complete_purchase`, `get_checkout_status`, and `get_spend_status`.

## SDKs 

Official SDKs wrap this API so you do not have to hand-roll requests. Same surface in every language: `cards`, `spend`, `checkout`, `connections`.

Node

`npm install @joomjoo/sdk` · [npmjs.com/package/@joomjoo/sdk](https://www.npmjs.com/package/@joomjoo/sdk)

Python

`pip install joomjoo` · [pypi.org/project/joomjoo](https://pypi.org/project/joomjoo/)

MCP server

`npx -y @joomjoo/mcp` · [npmjs.com/package/@joomjoo/mcp](https://www.npmjs.com/package/@joomjoo/mcp)

Node

```
import { Joomjoo } from "@joomjoo/sdk";
const joomjoo = new Joomjoo(process.env.JOOMJOO\_API\_KEY);
const card = await joomjoo.cards.create({ amount: 20, merchant: "namecheap", single\_use: true });
```

Python

```
from joomjoo import Joomjoo
joomjoo = Joomjoo(api\_key=os.environ["JOOMJOO\_API\_KEY"])
card = joomjoo.cards.create(amount=20, merchant="namecheap", single\_use=True)
```

Agent (MCP)

```
{
"mcpServers": {
"joomjoo": {
"command": "npx",
"args": ["-y", "@joomjoo/mcp"],
"env": { "JOOMJOO\_API\_KEY": "YOUR\_API\_KEY" }
}
}
}
```

Joomjoo API v1 · Base URL `https://api.joomjoo.com` · Questions? Reach the team from the console.
