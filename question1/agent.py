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


def _field(text: str, name: str, allowed: set[str] | None = None) -> str | None:
    """read one string field out of a reply without parsing json at all.

    scans for the key, then for the next quoted value, honouring backslash
    escapes. the last occurrence wins, because a reply may restate an example
    before the answer. when a set of allowed values is given, only a value in
    that set is accepted, so a stray mention of the word earlier cannot win.
    """
    found = None
    key = f'"{name}"'
    start = 0
    upper_allowed = {item.upper() for item in allowed} if allowed else None
    while True:
        at = text.find(key, start)
        if at < 0:
            return found
        cursor = at + len(key)
        while cursor < len(text) and text[cursor] in " \t\r\n:":
            cursor += 1
        if cursor >= len(text) or text[cursor] != '"':
            start = at + 1
            continue
        cursor += 1
        chars = []
        while cursor < len(text):
            char = text[cursor]
            if char == "\\" and cursor + 1 < len(text):
                chars.append(text[cursor + 1])
                cursor += 2
                continue
            if char == '"':
                break
            chars.append(char)
            cursor += 1
        value = "".join(chars).strip()
        if value and (upper_allowed is None or value.upper() in upper_allowed):
            found = value
        start = at + len(key)


def parse_resolution(text: str) -> TicketResolution:
    """pull the two graded fields out by name, then validate them.

    this never builds a json object, so it survives truncated output, prose that
    contains braces, several objects in one reply, and a reply that mentions an
    example before the answer. validation happens against the action enum and the
    article list, which is a stronger check than syntactic validity.
    """
    action = _field(text, "action", allowed_actions)
    article = _field(text, "kb_article", set(article_ids()))

    if action is None:
        raise ValueError(f"no allowed action in reply:\n{text[:400]}")
    if article is None:
        raise ValueError(f"no known article id in reply:\n{text[:400]}")

    return TicketResolution(
        action=action.upper(),
        kb_article=article,
        customer_reply=_field(text, "customer_reply") or "",
        raw_completion=text,
    )


allowed_actions = {"REFUND", "REPLACE", "SEND_ARTICLE", "ESCALATE_TIER2"}
input_token_budget = (3000 - 64 * OUTPUT_PRICE) // INPUT_PRICE
system_message = (
    "JSON only: action, kb_article, customer_reply. "
    "actions: REFUND REPLACE SEND_ARTICLE ESCALATE_TIER2"
)


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


def compose_messages(ticket: dict, order: dict, ids: list[str] | None = None) -> list[ChatMessage]:
    user = "\n".join(
        [
            f"POLICY\n{compact_articles(ids)}",
            f"TICKET\n{compact_thread(ticket)}",
            f"ORDER_SNAPSHOT:{compact_order(order)} END_SNAPSHOT",
        ]
    )
    return [ChatMessage("system", system_message), ChatMessage("user", user)]


class SupportCopilot:
    """shopassist tier-1 copilot."""

    def __init__(self, session: CostSession | None = None):
        self.session = session or CostSession()
        self.llm = LlmClient(self.session)

    def build_messages(self, ticket_id: str) -> list[ChatMessage]:
        ticket = get_ticket(ticket_id)
        order = get_order(ticket["order_id"])
        return compose_messages(ticket, order)

    def handle_ticket(self, ticket_id: str) -> TicketResolution:
        messages = self.build_messages(ticket_id)
        tokens = message_tokens(messages)
        if tokens > input_token_budget:
            raise ValueError(f"prompt is {tokens} tokens; budget is {input_token_budget}")
        completion = self.llm.chat("handle_ticket", messages)
        return audit_resolution(parse_resolution(completion))
