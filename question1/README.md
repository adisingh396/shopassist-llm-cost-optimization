# question 1: one call per ticket

`SupportCopilot.handle_ticket(ticket_id)` still makes one model call. The prompt is compiled from three pieces: the complete ticket thread, order facts needed by the model, and the five policy articles.

## result

| ticket | input | output | points |
|---|---:|---:|---:|
| T-1001 | 278 | 46 | 1,524 |
| T-1002 | 267 | 39 | 1,386 |
| T-1003 | 256 | 39 | 1,353 |
| T-1004 | 259 | 36 | 1,317 |
| average | | | 1,395 |

The target is 3,000 points per ticket.

For T-1001, the complete calculation is:

```text
278 input * 3 + 46 output * 15 = 1,524 points
```

## prompt compiler

The original prompt paid for examples, a random run id, Markdown formatting and a request for a long explanation. None of that is used after parsing the response.

The new prompt keeps the useful context:

```text
POLICY
article-id:policy text

TICKET
C:customer message|A:agent message

ORDER_SNAPSHOT:{minified order} END_SNAPSHOT
```

Policy cleanup only removes headings, bold markers and repeated whitespace. `order_id` and `sku` stay in application code; the model receives the product title and every policy field. New order fields pass through automatically.

The compiled prompt is checked against a 680-token input budget before the call. The response is checked locally for a known action and article id.

## caching

The static prefix is below the 1,024-token cache minimum. Padding it would lower the score in this simulator while adding data the model does not need. This version leaves caching off.

## trade-offs

The local client decides from `ORDER_SNAPSHOT`, so a snapshot-only prompt would also pass the tests. I kept the ticket and verbatim policy meaning because a hosted model would need both. Field aliases, TOON and compressed binary payloads were rejected because the local parser requires normal JSON keys.

## run

```bash
python question1/run.py
python -m pytest tests/test_question1.py -q
```
