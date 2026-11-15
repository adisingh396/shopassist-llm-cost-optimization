from __future__ import annotations

from shared.kb import expanded_help_center_blob
from shared.tokens import count_tokens
from shared.tools import get_order, get_ticket
from eval.reference import TICKET_EXPECTATIONS
from question2.agent import SupportPipeline, input_token_budget

PUBLIC = ["T-1001", "T-1002", "T-1003", "T-1004"]


def test_help_center_exceeds_context():
    assert count_tokens(expanded_help_center_blob()) > 200_000


def test_resolves_public_tickets():
    pipe = SupportPipeline()
    for tid in PUBLIC:
        expected = TICKET_EXPECTATIONS[tid]
        got = pipe.handle_ticket(tid)
        assert got.action == expected.action
        assert got.kb_article == expected.kb_article


def test_holdout_subscription():
    pipe = SupportPipeline()
    got = pipe.handle_ticket("T-1091")
    expected = TICKET_EXPECTATIONS["T-1091"]
    assert got.action == expected.action
    assert got.kb_article == expected.kb_article


def test_each_ticket_stays_under_target():
    for tid in PUBLIC:
        pipe = SupportPipeline()
        pipe.handle_ticket(tid)
        assert len(pipe.session.calls) == 1
        assert pipe.session.calls[0].label == "compose"
        assert pipe.session.total_points() <= 2_500


def test_all_current_policies_fit_the_budget():
    pipe = SupportPipeline()
    ticket = get_ticket("T-1001")
    context = pipe._triage(ticket, get_order(ticket["order_id"]))
    articles = pipe._retrieve(context)
    messages = pipe._messages(context, articles)

    assert len(articles) == 5
    assert count_tokens("\n\n".join(f"{m.role.upper()}:\n{m.content}" for m in messages)) <= input_token_budget


def test_audit_rejects_an_article_outside_context():
    draft = '{"action":"REFUND","kb_article":"returns-within-30-days"}'
    try:
        SupportPipeline._audit(draft, ["digital-license-no-refund"])
    except ValueError:
        pass
    else:
        raise AssertionError("audit accepted an article the model never saw")
