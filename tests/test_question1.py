from __future__ import annotations

import pytest

from eval.reference import TICKET_EXPECTATIONS
from question1.agent import (
    TicketResolution,
    SupportCopilot,
    audit_resolution,
    input_token_budget,
    message_tokens,
)

PUBLIC = ["T-1001", "T-1002", "T-1003", "T-1004"]


def test_resolves_public_tickets():
    copilot = SupportCopilot()
    for tid in PUBLIC:
        expected = TICKET_EXPECTATIONS[tid]
        got = copilot.handle_ticket(tid)
        assert got.action == expected.action
        assert got.kb_article == expected.kb_article


def test_holdout_subscription():
    copilot = SupportCopilot()
    got = copilot.handle_ticket("T-1091")
    exp = TICKET_EXPECTATIONS["T-1091"]
    assert got.action == exp.action
    assert got.kb_article == exp.kb_article


def test_each_ticket_stays_under_target():
    for tid in PUBLIC:
        copilot = SupportCopilot()
        copilot.handle_ticket(tid)
        assert len(copilot.session.calls) == 1
        assert copilot.session.total_points() <= 3_000


def test_compiled_prompt_stays_inside_input_budget():
    copilot = SupportCopilot()
    messages = copilot.build_messages("T-1001")
    prompt = "\n".join(message.content for message in messages)

    assert message_tokens(messages) <= input_token_budget
    assert "Wireless headphones" in prompt
    assert "order_id" not in prompt
    assert "WH-200" not in prompt


def test_audit_rejects_unknown_values():
    unknown = TicketResolution("SHIP_NOW", "made-up", "", "{}")
    with pytest.raises(ValueError):
        audit_resolution(unknown)
