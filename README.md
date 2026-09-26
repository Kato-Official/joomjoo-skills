<p align="center">
  <a href="https://joomjoo.com">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://assets.joomjoo.com/logo/png/joomjoo-logo-horizontal-white-1704x414.png">
      <img src="https://assets.joomjoo.com/logo/png/joomjoo-logo-horizontal-black-1704x414.png" alt="Joomjoo" width="300">
    </picture>
  </a>
</p>

<h1 align="center">Let your AI agent pay on its own</h1>

<p align="center">
  Payments for AI agents. Your agent gets its own card with a limit you set, clears the bank's security check (3DS) itself, and checks out in its own browser. Zero taps from you.
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/@joomjoo/sdk"><img src="https://img.shields.io/npm/v/%40joomjoo%2Fsdk?label=%40joomjoo%2Fsdk&color=1F7C93" alt="npm @joomjoo/sdk"></a>
  <a href="https://www.npmjs.com/package/@joomjoo/mcp"><img src="https://img.shields.io/npm/v/%40joomjoo%2Fmcp?label=%40joomjoo%2Fmcp&color=1F7C93" alt="npm @joomjoo/mcp"></a>
  <a href="https://pypi.org/project/joomjoo/"><img src="https://img.shields.io/pypi/v/joomjoo?label=pypi%20joomjoo&color=1F7C93" alt="PyPI joomjoo"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-111111" alt="MIT"></a>
</p>

<br>

This repository is everything an agent needs to use Joomjoo, in the format each agent reads. One skill, one AGENTS.md, one MCP server, four tool files, the full API reference. They all describe the same four tools and are regenerated together whenever the API changes.

## Install in one line

| Your agent | Do this |
|---|---|
| Claude Code, Codex, Cursor, Gemini CLI and any agent that reads skills | `npx skills add Kato-Official/joomjoo-skills` |
| Claude Code, by hand | copy `skills/joomjoo/SKILL.md` to `.claude/skills/joomjoo/SKILL.md` in your project or home folder |
| Anything that reads AGENTS.md (Codex, Cursor, Aider, most agents) | copy `AGENTS.md` next to your agent's code |
| Any MCP client (Claude Desktop, Cursor, Windsurf, Zed) | add `mcp/joomjoo_mcp_config.json` to your MCP settings, or run `JOOMJOO_API_KEY=mk_live_... npx -y @joomjoo/mcp` |
| Your own code, TypeScript or JavaScript | `npm install @joomjoo/sdk` |
| Your own code, Python | `pip install joomjoo` |
| Raw tool schemas | `tools/anthropic_tools.json`, `tools/openai_tools.json`, `tools/gemini_tools.json`, `tools/langchain_tools.py` |

Every file reads the key from the `JOOMJOO_API_KEY` environment variable, so the file itself is safe to commit. Get a key at [app.joomjoo.com](https://app.joomjoo.com), Developer, API keys. Joomjoo is in private beta: request an invite at [joomjoo.com/beta.html](https://joomjoo.com/beta.html).

## The four tools

| Tool | What it does | Returns |
|---|---|---|
| `complete_purchase` | Hand Joomjoo a plain-English task, the merchant and a spend cap. It opens the merchant in its own browser, uses the person's stored login, mints a single-use card at the final review for the real total, pays, and clears 3DS. The card number never touches your agent. | `checkout_id` to poll |
| `get_checkout_status` | Poll a checkout until it ends. Ten statuses, each with a clear next step (see the skill). | status, order id, totals |
| `issue_card` | A real virtual card capped at an amount, for the rare case your agent must type a card itself. | card, `spend_request_id` |
| `get_spend_status` | Whether a card was charged: `not_started`, `authorized`, `cleared`, `declined`. | status, settled, amount |

## One purchase, end to end

```ts
import { Joomjoo } from "@joomjoo/sdk";

const joomjoo = new Joomjoo(process.env.JOOMJOO_API_KEY!);

const run = await joomjoo.checkout.create({
  task: "buy the domain example.click for 1 year",
  merchant: "namecheap",
  amount: 20,
  confirm_pay: false,               // stop at the final review, the person approves in the console
  idempotency_key: "order-2026-09-26-001",
});

let status = await joomjoo.checkout.get(run.checkout_id);
while (!["submitted", "canceled", "blocked", "error"].includes(status.status)) {
  await new Promise((r) => setTimeout(r, 8000));
  status = await joomjoo.checkout.get(run.checkout_id);
}
console.log(status.status, status.order_id, status.order_total);   // submitted 6288 "60.90 AED"
```

```python
from joomjoo import Joomjoo

joomjoo = Joomjoo(api_key=os.environ["JOOMJOO_API_KEY"])
run = joomjoo.checkout.create(task="buy the domain example.click for 1 year", merchant="namecheap", amount=20, idempotency_key="order-2026-09-26-001")
```

## What is in here

| Path | For |
|---|---|
| `skills/joomjoo/SKILL.md` | The skill: setup, the four tools, the ten checkout statuses and what the agent does at each, the rules, webhooks |
| `AGENTS.md` | The same knowledge as a universal AGENTS.md |
| `mcp/joomjoo_mcp_config.json` | One entry for your MCP settings |
| `tools/` | Tool definitions for the Anthropic, OpenAI and Gemini APIs, and LangChain or CrewAI |
| `docs/api-reference.md` | The full REST reference: authentication, cards, spend, checkout, connections, errors, webhooks |
| `docs/joomjoo.postman_collection.json` | Every endpoint, ready to import |
| `CHANGELOG.md` | What changed, and which package versions each release matches |

## The rules the agent follows

- Never above the cap. One card per purchase; a single-use card locks itself after its first charge.
- The card is minted at the final review for the real total, never before, never above the cap.
- Pay only with the Joomjoo card, never a card saved on the merchant account.
- 3DS is handled by Joomjoo. The agent never asks the person for a code.
- Every checkout carries an `idempotency_key`, so a retry can never buy twice.
- No key, card number or CVC ever lands in a log, a message, a file or a prompt.

## Links

[joomjoo.com](https://joomjoo.com) · [console](https://app.joomjoo.com) · [npm @joomjoo/sdk](https://www.npmjs.com/package/@joomjoo/sdk) · [npm @joomjoo/mcp](https://www.npmjs.com/package/@joomjoo/mcp) · [PyPI joomjoo](https://pypi.org/project/joomjoo/)

Joomjoo LLC, Delaware. MIT licensed.
