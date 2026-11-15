from __future__ import annotations

import re
from dataclasses import dataclass

from question1.agent import (
    allowed_actions,
    compact_articles,
    compact_order,
    compact_thread,
    message_tokens,
    parse_resolution,
)
from shared.billing import INPUT_PRICE, OUTPUT_PRICE, CostSession
from shared.kb import article_ids, load_article
from shared.llm import ChatMessage, LlmClient
from shared.tools import get_order, get_ticket


input_token_budget = (2500 - 64 * OUTPUT_PRICE) // INPUT_PRICE


def terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2}


@dataclass
class TicketResolution:
    action: str
    kb_article: str


@dataclass
class TicketContext:
    thread: str
    order: str
    query: str


class SupportPipeline:
    """triage, retrieve, compose and audit with one model call."""

    system = (
        "Resolve from policy. JSON only with action, kb_article, customer_reply. "
        "Allowed actions: REFUND, REPLACE, SEND_ARTICLE, ESCALATE_TIER2."
    )

    def __init__(self, session: CostSession | None = None):
        self.session = session or CostSession()
        self.llm = LlmClient(self.session)

    def handle_ticket(self, ticket_id: str) -> TicketResolution:
        ticket = get_ticket(ticket_id)
        order = get_order(ticket["order_id"])
        context = self._triage(ticket, order)
        ranked = self._retrieve(context)
        draft, supplied = self._compose(context, ranked)
        return self._audit(draft, supplied)

    @staticmethod
    def _triage(ticket: dict, order: dict) -> TicketContext:
        thread = compact_thread(ticket)
        facts = " ".join(
            key.replace("_", " ") if value is True else str(value)
            for key, value in order.items()
            if key not in {"order_id", "sku"} and value is not False
        )
        return TicketContext(thread, compact_order(order), f"{thread} {facts}")

    @staticmethod
    def _retrieve(context: TicketContext) -> list[str]:
        query = terms(context.query)

        def score(article_id: str) -> int:
            article = f"{article_id.replace('-', ' ')} {load_article(article_id)}"
            return len(query & terms(article))

        return sorted(article_ids(), key=lambda article_id: (-score(article_id), article_id))

    def _messages(self, context: TicketContext, articles: list[str]) -> list[ChatMessage]:
        user = "\n".join(
            [
                f"POLICY\n{compact_articles(articles)}",
                f"TICKET\n{context.thread}",
                f"ORDER_SNAPSHOT:{context.order} END_SNAPSHOT",
            ]
        )
        return [ChatMessage("system", self.system), ChatMessage("user", user)]

    def _compose(self, context: TicketContext, ranked: list[str]) -> tuple[str, list[str]]:
        supplied = []
        for article_id in ranked:
            trial = supplied + [article_id]
            if message_tokens(self._messages(context, trial)) <= input_token_budget:
                supplied = trial
        if not supplied:
            raise ValueError("no policy article fits the input budget")
        messages = self._messages(context, supplied)
        return self.llm.chat("compose", messages), supplied

    @staticmethod
    def _audit(draft: str, articles: list[str]) -> TicketResolution:
        parsed = parse_resolution(draft)
        if parsed.action not in allowed_actions:
            raise ValueError(f"unknown action: {parsed.action}")
        if parsed.kb_article not in set(articles):
            raise ValueError(f"article was not supplied: {parsed.kb_article}")
        return TicketResolution(parsed.action, parsed.kb_article)
