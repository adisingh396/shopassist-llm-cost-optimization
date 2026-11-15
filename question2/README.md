# question 2: four stages, one paid call

the brief asks for triage, retrieve, compose and audit. all four exist. three of them are plain python.

## result

| ticket | input | output | points |
|---|---:|---:|---:|
| T-1001 | 270 | 46 | 1,500 |
| T-1002 | 259 | 39 | 1,362 |
| T-1003 | 248 | 39 | 1,329 |
| T-1004 | 251 | 36 | 1,293 |
| average | | | 1,371 |

target is 2,500 points per ticket.

### T-1001, a refund

| stage | points |
|---|---:|
| triage | 0 |
| retrieve | 0 |
| compose | 1,500 |
| audit | 0 |

### T-1003, an escalation

| stage | points |
|---|---:|
| triage | 0 |
| retrieve | 0 |
| compose | 1,329 |
| audit | 0 |

## the four stages

triage turns the ticket and the order into search terms. no model, no cost.

retrieve ranks the policy files by word overlap and adds them while the finished prompt still fits 513 tokens. it never decides which policy wins, it only decides what to read.

compose is the one model call. it gets the same compiled packet as question 1.

audit parses the reply, checks the action against the four allowed values, and checks that the cited article was actually one of the articles we sent.

## why the articles are not shortlisted by hand

the obvious saving is to send one or two articles instead of five. i tested that across 512 order combinations, every value of product type, delivery age, opened, licence, customized and damage.

| strategy | articles sent | cases missing the right article |
|---|---:|---|
| all five | 5 | 0 |
| default plus two | 3 | 48 |
| default plus one | 2 | 310 |
| two most similar | 2 | 196 |

every shortlist loses the article the answer needs on some orders. the 48 misses are all customized-and-damaged cases, where two policies look equally close and the right one depends on which takes priority.

sending all five costs 146 tokens and buys correctness on all 512.

## the arithmetic that shaped this

a short reply is 46 output tokens, which is 690 points. four model calls would be 2,760 before any input is paid, and the target is 2,500. so the pipeline cannot keep four paid calls, whatever the prompt looks like.

## the help centre that is not used

the original pipeline built a 210,000 token help centre at startup. the real policy is five files and 143 tokens. the pipeline no longer builds it at all.

## run

```
python question2/run.py
python -m pytest tests/test_question2.py -q
```