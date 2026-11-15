# shopassist cost lab

A support bot for an online shop. It reads a ticket, looks up the order, checks the policy, and answers with an action and the policy article that backs it.

Two tracks. Both hit their target with one paid model call per ticket.

| track | target | what i hit | calls |
|---|---:|---:|---:|
| question 1 | 3,000 | 1,395 average | 1 |
| question 2 | 2,500 | 1,395 average | 1 |

## what i changed

Question 1 is one call per ticket. The old prompt carried a random run id, four worked examples, the full help center with its markdown, a request to think step by step, and a pretty printed order. Most of that never reached the answer.

I replaced it with a compact packet: the policy articles with their headings and bold marks removed but every sentence kept, the customer thread with short role markers, and the order as single line json with the internal ids dropped. Then one sentence telling the model what shape of answer to return.

Question 2 wants four stages. I kept all four and stopped paying for three of them. Triage and retrieval are plain python. Compose is the one model call. Audit is a check.

## numbers

| | baseline | now |
|---|---:|---:|
| question 1, one ticket | 8,856 | 1,524 |
| question 2, one ticket | 73,554 | 1,353 |

Eighty four percent of the old bill came from the reply, not the prompt. The instruction to explain its reasoning was the expensive part. Removing it drops the reply from about 488 tokens to 46.

## what i did not do

I did not use caching. The floor is 1,024 identical tokens and the prompt is 278. Padding it to qualify would lower the local score and add work a real provider bills for. I measured that trade and left it.

I did not delete the policy or the customer thread, even though the local client only reads the order snapshot. That version scores 873 points and would fail with a real model, so it is not the version here.

I did not copy the decision rules into python. The local reference file is the answer key and importing it would be copying the exam.

## run

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python question1/run.py
python question2/run.py
python scripts/benchmark.py
```

The benchmark prints input, cached input, output and points for each public ticket, then compares the shipped prompt against a verbose one, a single json envelope, and a snapshot only control.

## tests

Eleven tests. They check the four public tickets, the subscription holdout, that each ticket makes one call and stays under target, that the prompt stays inside the budget, and that the audit rejects unknown values.

One test was replaced. The original suite asserted the baseline stayed above 15,000 points, which no solution meeting the target can satisfy. It is now a per ticket ceiling. The correctness assertions are untouched.

## billing

| input | cached input | output |
|---:|---:|---:|
| 3 | 0.3 | 15 |

```
points = uncached_input * 3 + cached_input * 0.3 + output * 15
```