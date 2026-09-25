"""Joomjoo tools for LangChain and CrewAI.

Install:
    pip install joomjoo langchain-core

Set JOOMJOO_API_KEY in your environment (get a key from the Joomjoo console -> API keys).
Then add MOOJ_TOOLS to your agent. Card controls, 3DS, and fraud caps are handled for you.
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

    Status is one of: queued, running, awaiting_approval, needs_login, submitted, blocked.
    """
    return joomjoo.checkout.get(checkout_id)


@tool
def get_spend_status(spend_id: str) -> dict:
    """Check whether a card from issue_card was charged.

    Status is one of: not_started, authorized, cleared, declined. Pass the spend_request_id.
    """
    return joomjoo.spend.get(spend_id)


# Drop these into your agent.
MOOJ_TOOLS = [issue_card, complete_purchase, get_checkout_status, get_spend_status]

# LangChain:  from langgraph.prebuilt import create_react_agent
#             agent = create_react_agent(llm, MOOJ_TOOLS)
# CrewAI:     pass MOOJ_TOOLS to your Agent(tools=...), or wrap each callable with crewai.tools.tool.
