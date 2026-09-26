"""Joomjoo tools for LangChain and CrewAI.

Install:
    pip install joomjoo langchain-core

Set JOOMJOO_API_KEY in your environment (get a key from the Joomjoo console -> API keys).
Then add JOOMJOO_TOOLS to your agent. Card controls, 3DS, and fraud caps are handled for you.
"""

import os

from joomjoo import Joomjoo
from langchain_core.tools import tool

joomjoo = Joomjoo(api_key=os.environ["JOOMJOO_API_KEY"])


@tool
def issue_card(amount: float, merchant: str, single_use: bool = True) -> dict:
    """Issue a real virtual card capped at `amount` USD for a merchant.

    Returns the card and a spend_request_id. Use single_use=True for a one-time purchase
    (the card auto-freezes after the first charge).
    """
    return joomjoo.cards.create(amount=amount, merchant=merchant, single_use=single_use)


@tool
def complete_purchase(task: str, merchant: str, amount: float, confirm_pay: bool = False) -> dict:
    """Hand Joomjoo a plain-English purchase task and a spend cap.

    Joomjoo mints a card, drives the merchant checkout, handles 3DS, and (if confirm_pay=True) pays.
    Async: returns a checkout_id to poll with get_checkout_status. confirm_pay=False (default)
    stops at the final review without charging.
    """
    return joomjoo.checkout.create(task=task, merchant=merchant, amount=amount, confirm_pay=confirm_pay)


@tool
def get_checkout_status(checkout_id: str) -> dict:
    """Poll a complete_purchase run.

    Status is one of: queued, running, needs_login, needs_answer, awaiting_approval, paying, submitted,
    canceled, blocked, error. review_total and order_total are display strings such as "60.90 AED".
    """
    return joomjoo.checkout.get(checkout_id)


@tool
def get_spend_status(spend_id: str) -> dict:
    """Check whether a card from issue_card was charged.

    Status is one of: not_started, authorized, cleared, declined. Pass the spend_request_id.
    """
    return joomjoo.spend.get(spend_id)


@tool
def get_wallet() -> dict:
    """The wallet every card and purchase draws on: balance, available (free to assign),
    reserved (on open cards), pending (bank money in flight), in US dollars.
    Call it before a purchase when a 402 insufficient_funds is possible.
    """
    return joomjoo.wallet.get()


@tool
def create_topup_link(amount: float, success_url: str = "", cancel_url: str = "") -> dict:
    """When the wallet is short: a Stripe top-up page for `amount` US dollars.
    Give the returned url to the person; the wallet is credited when Stripe confirms.
    Never type a card yourself.
    """
    return joomjoo.wallet.create_funding_session(
        amount=amount, success_url=success_url or None, cancel_url=cancel_url or None
    )


# Drop these into your agent.
JOOMJOO_TOOLS = [issue_card, complete_purchase, get_checkout_status, get_spend_status, get_wallet, create_topup_link]
MOOJ_TOOLS = JOOMJOO_TOOLS  # the old name, kept so existing agents keep running

# LangChain:  from langgraph.prebuilt import create_react_agent
#             agent = create_react_agent(llm, JOOMJOO_TOOLS)
# CrewAI:     pass JOOMJOO_TOOLS to your Agent(tools=...), or wrap each callable with crewai.tools.tool.
