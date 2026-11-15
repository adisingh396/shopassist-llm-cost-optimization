# question 1: one call per ticket

`SupportCopilot.handle_ticket` makes one model call. the prompt is built from three things: the customer thread, the order facts the policy cares about, and the five policy articles.

## result

| ticket | input | output | points |
|---|---:|---:|---:|
| T-1001 | 270 | 46 | 1,500 |
| T-1002 | 259 | 39 | 1,362 |
| T-1003 | 248 | 39 | 1,329 |
| T-1004 | 251 | 36 | 1,293 |
| average | | | 1,371 |

target is 3,000 points per ticket.

for T-1001 that is:

```
270 input * 3 + 46 output * 15 = 1,500 points
```

## what the prompt looks like

```
JSON only: action, kb_article, customer_reply. actions: REFUND REPLACE SEND_ARTICLE ESCALATE_TIER2

POLICY
article-id:policy text

TICKET
C:customer message|A:agent message

ORDER_SNAPSHOT:{minified order} END_SNAPSHOT
```

policy cleanup removes the heading, the bold marks and the blank lines. not one policy word is rewritten. `order_id` and `sku` stay in the application, the model gets the title and every policy field, and any new order field passes through on its own.

before the call the finished prompt is counted and compared to 680 tokens. after the call the reply is checked for a known action and a known article id.

## why the reply is short

the old prompt asked the model to think step by step and quote its source. that single instruction produced a reply of about 488 tokens. it is now 46. output costs 15 per token, so most of the saving is here and not in the prompt.

## caching

off. the floor is 1,024 identical tokens and the prompt is 270. padding it to qualify would improve the local score while adding text a real provider bills for.

## what i did not do

the local client decides from the order snapshot, so a prompt with only the snapshot would pass the tests at 873 points. i kept the thread and the policy because a hosted model needs both.

i also did not write the policy rules into the prompt. that is cheaper, but the day a policy file changes the prompt would not.

## run

```
python question1/run.py
python -m pytest tests/test_question1.py -q
```