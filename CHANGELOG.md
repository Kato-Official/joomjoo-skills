# Changelog

All notable changes to the skill, the tool files and the reference in this repository. The packages have their own versions on npm and PyPI.

## 2026-09-26, wallet

- The wallet: `GET /v1/wallet`, `POST /v1/wallet/funding-sessions` (a Stripe top-up page), `POST /v1/wallet/bank-transfers` (a declared transfer with the account and a reference code). Webhook event `money.funded`.
- Two more tools everywhere: `get_wallet` and `create_topup_link`. Six tools in the skill, AGENTS.md, the MCP server and the tool files.
- Matches @joomjoo/sdk 0.2.0, @joomjoo/mcp 0.2.0, PyPI joomjoo 0.2.0.

## 2026-09-26

- First public release: the `joomjoo` skill (SKILL.md), AGENTS.md, the MCP config, the Anthropic, OpenAI, Gemini and LangChain tool files, the API reference and the Postman collection.
- Matches @joomjoo/sdk 0.1.1, @joomjoo/mcp 0.1.1, PyPI joomjoo 0.1.1 and the live API: ten checkout statuses, display-string totals, idempotency_key, Joomjoo-Signature on webhooks.
