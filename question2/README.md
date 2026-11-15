# question 2: four stages, one model call

The pipeline keeps triage, retrieval, composition and audit as separate stages. Triage, retrieval and audit run locally. Composition is the only model call.

```text
ticket -> local triage -> budgeted policy retrieval -> model compose -> local audit
```

## result

| ticket | input | output | points |
|---|---:|---:|---:|
| T-1001 | 278 | 46 | 1,524 |
| T-1002 | 267 | 39 | 1,386 |
| T-1003 | 256 | 39 | 1,353 |
| T-1004 | 259 | 36 | 1,317 |
| average | | | 1,395 |

The target is 2,500 points per ticket.

### physical fulfilment: T-1001

| stage | input | output | points |
|---|---:|---:|---:|
| triage | 0 | 0 | 0 |
| retrieve | 0 | 0 | 0 |
| compose | 278 | 46 | 1,524 |
| audit | 0 | 0 | 0 |

### escalation: T-1003

| stage | input | output | points |
|---|---:|---:|---:|
| triage | 0 | 0 | 0 |
| retrieve | 0 | 0 | 0 |
| compose | 256 | 39 | 1,353 |
| audit | 0 | 0 | 0 |

## retrieval

The retriever ranks policy files by overlap with the ticket and order facts. It then adds ranked articles while the complete prompt stays under 513 input tokens.

All five current articles fit in 143 tokens, so all five are supplied. This matters for fallback cases. An unrevealed digital item contains digital terms, but its final article can be `returns-within-30-days`. A top-three lexical search can omit that article.

If the policy collection grows, the same loop stops adding articles when the budget is full. There are no action-specific routing rules in retrieval.

## audit

The audit parses the response and checks two facts: the action belongs to the public enum, and the cited article was present in the supplied context. It never tries to reproduce the policy decision in Python.

The old audit generated another answer from the same inputs. The local audit catches structural errors without another output bill.

## large help center fixture

`expanded_help_center_blob()` remains available for the context-size test, but it is no longer loaded by the pipeline. Its builder now reaches 210,000 tokens in linear time instead of tokenizing an expanding string on every loop.

## run

```bash
python question2/run.py
python -m pytest tests/test_question2.py -q
```
