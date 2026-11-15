from __future__ import annotations

import json
import re
from dataclasses import dataclass

from shared.billing import INPUT_PRICE, OUTPUT_PRICE, CostSession
from shared.kb import article_ids, load_article
from shared.llm import ChatMessage, LlmClient
from shared.tokens import count_tokens
from shared.tools import get_order, get_ticket


@dataclass
class TicketResolution:
    action: str
    kb_article: str
    customer_reply: str
    raw_completion: str


def parse_resolution(text: str) -> TicketResolution:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError(f"No JSON in model output:\n{text[:400]}")
    data = json.loads(m.group())
    return TicketResolution(
        action=str(data["action"]).upper(),
        kb_article=str(data["kb_article"]),
        customer_reply=str(data.get("customer_reply", "")),
        raw_completion=text,
    )


allowed_actions = {"REFUND", "REPLACE", "SEND_ARTICLE", "ESCALATE_TIER2"}
input_token_budget = (3000 - 64 * OUTPUT_PRICE) // INPUT_PRICE


def compact_order(order: dict) -> str:
    model_fields = {key: value for key, value in order.items() if key not in {"order_id", "sku"}}
    return json.dumps(model_fields, separators=(",", ":"))


def compact_thread(ticket: dict) -> str:
    return "|".join(
        f"{message['from'][0].upper()}:{' '.join(message['text'].split())}"
        for message in ticket["messages"]
    )


def compact_articles(ids: list[str] | None = None) -> str:
    rows = []
    for article_id in ids or article_ids():
        text = re.sub(r"^#\s+[^\n]+\n+", "", load_article(article_id)).replace("**", "")
        rows.append(f"{article_id}:{' '.join(text.split())}")
    return "\n".join(rows)


def message_tokens(messages: list[ChatMessage]) -> int:
    prompt = "\n\n".join(f"{message.role.upper()}:\n{message.content}" for message in messages)
    return count_tokens(prompt)


def audit_resolution(resolution: TicketResolution, ids: list[str] | None = None) -> TicketResolution:
    if resolution.action not in allowed_actions:
        raise ValueError(f"unknown action: {resolution.action}")
    if resolution.kb_article not in set(ids or article_ids()):
        raise ValueError(f"unknown article: {resolution.kb_article}")
    return resolution


class SupportCopilot:
    """shopassist tier-1 copilot."""

    def __init__(self, session: CostSession | None = None):
        self.session = session or CostSession()
        self.llm = LlmClient(self.session)

    def build_messages(self, ticket_id: str) -> list[ChatMessage]:
        ticket = get_ticket(ticket_id)
        order = get_order(ticket["order_id"])
        system = (
            "Resolve from policy. JSON only with action, kb_article, customer_reply. "
            "Allowed actions: REFUND, REPLACE, SEND_ARTICLE, ESCALATE_TIER2."
        )
        user = "\n".join(
            [
                f"POLICY\n{compact_articles()}",
                f"TICKET\n{compact_thread(ticket)}",
                f"ORDER_SNAPSHOT:{compact_order(order)} END_SNAPSHOT",
            ]
        )
        return [ChatMessage("system", system), ChatMessage("user", user)]

    def handle_ticket(self, ticket_id: str) -> TicketResolution:
        messages = self.build_messages(ticket_id)
        tokens = message_tokens(messages)
        if tokens > input_token_budget:
            raise ValueError(f"prompt is {tokens} tokens; budget is {input_token_budget}")
        completion = self.llm.chat("handle_ticket", messages)
        return audit_resolution(parse_resolution(completion))
