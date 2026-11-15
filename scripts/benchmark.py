from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from question1.agent import SupportCopilot, compact_articles, compact_order, compact_thread, parse_resolution
from question2.agent import SupportPipeline
from shared.billing import CostSession
from shared.kb import all_articles_blob
from shared.llm import ChatMessage, LlmClient
from shared.tools import format_thread, get_order, get_ticket

tickets = ["T-1001", "T-1002", "T-1003", "T-1004"]


def track(name: str, factory) -> None:
    print(f"\n{name}")
    print("ticket   call       input cached output points")
    total = 0
    for ticket_id in tickets:
        app = factory()
        app.handle_ticket(ticket_id)
        for call in app.session.calls:
            print(
                f"{ticket_id:<8} {call.label:<10} {call.input_tokens:>5} "
                f"{call.cached_prefix_tokens:>6} {call.output_tokens:>6} {call.points():>6}"
            )
            total += call.points()
    print(f"total {total} | average {total / len(tickets):.1f}")


def one_call(label: str, messages: list[ChatMessage]) -> tuple[int, int, int]:
    session = CostSession()
    completion = LlmClient(session).chat(label, messages)
    parse_resolution(completion)
    call = session.calls[0]
    return call.input_tokens, call.output_tokens, call.points()


def ablations() -> None:
    ticket = get_ticket("T-1001")
    order = get_order(ticket["order_id"])
    compact = compact_order(order)
    short_system = (
        "Resolve from policy. JSON only with action, kb_article, customer_reply. "
        "Allowed actions: REFUND, REPLACE, SEND_ARTICLE, ESCALATE_TIER2."
    )
    baseline_system = "\n\n".join(
        [
            "Run id benchmark",
            "You are ShopAssist, the Tier-1 customer support copilot.",
            (
                "Examples:\n"
                'unopened headphones, day 10 -> {"action":"REFUND","kb_article":"returns-within-30-days"}\n'
                'ebook, license shown -> {"action":"SEND_ARTICLE","kb_article":"digital-license-no-refund"}\n'
                'cracked custom mug -> {"action":"ESCALATE_TIER2","kb_article":"custom-items-no-replace"}\n'
                'cracked stock mug, day 2 -> {"action":"REPLACE","kb_article":"damage-replacement-7-days"}'
            ),
            "HELP CENTER:",
            all_articles_blob(),
            "Think step by step. Write full reasoning, quote any article you rely on, then output JSON.",
        ]
    )
    baseline_user = (
        f"THREAD:\n{format_thread(ticket)}\n\n"
        f"ORDER_SNAPSHOT:\n{json.dumps(order, indent=2)}\nEND_SNAPSHOT"
    )
    envelope = {
        **{key: value for key, value in order.items() if key not in {"order_id", "sku"}},
        "ticket": compact_thread(ticket),
        "policy": compact_articles(),
    }
    variants = {
        "verbose baseline": [ChatMessage("system", baseline_system), ChatMessage("user", baseline_user)],
        "whole json envelope": [
            ChatMessage("system", short_system),
            ChatMessage("user", f"ORDER_SNAPSHOT:{json.dumps(envelope, separators=(',', ':'))} END_SNAPSHOT"),
        ],
        "compiled context": SupportCopilot().build_messages("T-1001"),
        "snapshot only (invalid design)": [
            ChatMessage("system", "JSON only with action and kb_article."),
            ChatMessage("user", f"ORDER_SNAPSHOT:{compact} END_SNAPSHOT"),
        ],
    }
    print("\nq1 ablation on T-1001")
    print("variant                         input output points")
    for name, messages in variants.items():
        input_tokens, output_tokens, points = one_call(name, messages)
        print(f"{name:<31} {input_tokens:>5} {output_tokens:>6} {points:>6}")


if __name__ == "__main__":
    track("q1", SupportCopilot)
    track("q2", SupportPipeline)
    ablations()
