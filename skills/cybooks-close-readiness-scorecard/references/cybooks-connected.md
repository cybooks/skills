# Connected to Cybooks

Use this path when tools named `cybooks_*` are available. The scorecard is
then built from the live books: the trial balance at both dates, the checks
Cybooks already ran, and the month's open to-dos. This path only reads,
with one exception that needs a yes (starting a review, step 4).

To connect: add the Cybooks connector in Claude with the address
`https://app.cybooks.com.cy/mcp/cybooks` and sign in. Claude can then read
what the signed-in person can read in Cybooks, no more.

## How Cybooks tools are called

A few tools are listed directly. The rest are capabilities, reached in
three steps:

1. `cybooks_search_capabilities` with plain words ("trial balance") finds
   the capability.
2. `cybooks_describe_capability` publishes its arguments. Do this once per
   capability before the first call.
3. `cybooks_read_capability` runs a read, with arguments shaped as
   described, usually `{ "query": { ... } }`.

## The steps

**1. Who and what.** `cybooks_auth_status` names the company and the
person's permissions. The trial balance needs `view_reports`, the review
`view_books_review`, to-dos `view_dashboard`.

**2. The two trial balances.** `cybooks_get_trial_balance` with
`{ "query": { "as_of_date": "2026-06-30", "per_page": 200 } }`, then again
for the prior period end. Page until `last_page`. Check that
`debit_minus_credit` is 0; if it is not, that is the first finding and it
blocks the close.

Write each to a CSV with the headers `code,account,class,debit,credit`
(the `accounts[]` rows carry exactly these) and run:

```bash
python3 scripts/tb_compare.py --current tb-current.csv --prior tb-prior.csv --prior-months 5
```

`--prior-months` is the number of months of the financial year up to the
prior date. Ask for the financial year start if it is not known; a
calendar year is the usual case in Cyprus. Say which you used.

**3. Explain the movements from the ledger.** For each account the script
flags, read `cybooks_get_general_ledger` with the account code and the
period's dates. The lines behind the movement are then known: three
invoices to one customer, one manual journal, a loan drawdown. A movement
whose lines are identified and ordinary is **Explained**. One that rests on
a single manual journal with a weak description is not; ask.

**4. The checks Cybooks ran.** `cybooks_get_books_review` with
`{ "query": { "period_from": "...", "period_to": "...", "profile": "month_end" } }`.

- `status: none`: ask before starting a run. A run is a write
  (`cybooks_write_capability`, `cybooks_run_books_review`): it records a
  review in the company's history and may email it to the people on the
  company's review schedule. Without a yes, score from the trial balances
  alone and say the checks were not read.
- `status: completed`: say when (`completed_at`). A review older than the
  last change to the books may be stale; say how old it is.

Place each finding that is not a pass in its dimension:

| Finding's `scope` | Dimension |
|---|---|
| `bank` | 1 Bank and cash agree |
| `receivables`, `payables` | 2 Everything is in |
| `vat`, `vies`, `oss`, `people` | 3 Tax and payroll tie |
| `ledger`, `assets`, `stock`, `related_parties`, `year_end` | 5 The balance sheet makes sense |

Three exceptions by code: `CB-LDG-04` and `CB-LDG-06` belong in dimension
1; `CB-LDG-03`, `CB-LDG-05` and `CB-AP-04` in dimension 6.

Read each finding as Cybooks wrote it: `status` `exception` needs a look,
`insufficient_data` could not be checked (never a pass, never a failure),
`not_applicable` is not relevant. A check with `grade: judgment` is scored:
it can only be worth a look, and it is a note, never a block. A `severity`
of `high` on a check that needs a look blocks the close. A
`monetary_impact` of `null` is no amount, not zero; `payroll_withheld` or
`salary_hidden` means the figure is withheld from this person.

**5. What a person still has to answer.** `cybooks_list_todos` with
`{ "query": { "filter": { "period": "2026-06" } } }`. Count those whose
`status` is `open`, `waiting` or `later` (all three still hold the close)
and name the largest. The row with `kind: close` is the month's
close; if it reports that the close is waiting on something, the verdict is
Not yet and the scorecard names what it waits for.

**6. Is the month already closed?** `cybooks_get_period_lock` returns the
dates up to which the books are closed. It needs `manage_period_lock`. If
the period is already closed, say so at the top: the scorecard is then a
look back, and anything it finds is corrected in the open period.

**7. The journal, for dimension 6.** When `cybooks-journal-entry-screen` is
installed, run it for the period and use its result. Otherwise use the
checks from step 4 that sit in dimension 6 and say the journal was not
screened.

## Rules for this path

- A figure on the scorecard is either what Cybooks returned or what the
  script computed from the two trial balances. Never a blend, never an
  estimate.
- Do not recompute a check Cybooks ran. If the script and a Cybooks check
  disagree on the same question, show both and say so.
- A `403` names a missing permission. Mark that input as not read and score
  the dimension accordingly. Do not look for another route to the same
  data.
- A `429` carries the seconds to wait. Wait, then go on.
- The scorecard does not close the month. The month is closed in Cybooks
  under To do, by a person.
