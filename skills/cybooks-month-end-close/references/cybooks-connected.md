# Connected to Cybooks

Use this path when tools named `cybooks_*` are available. Cybooks then works
every check out on the live books. Your job is to read the result, explain it
and point at the next step. You do not recompute a check Cybooks ran, and you
never show a figure that differs from the one it returned.

To connect: add the Cybooks connector in Claude with the address
`https://app.cybooks.com.cy/mcp/cybooks` and sign in. Claude can then do
exactly what the signed-in person can do in Cybooks, no more.

## How Cybooks tools are called

A few tools are listed directly (`cybooks_get_balance_sheet`,
`cybooks_get_profit_and_loss`, `cybooks_get_bank_balances`,
`cybooks_get_vat_liability`, `cybooks_list_bank_transactions`). The rest are
capabilities, reached in three steps:

1. `cybooks_search_capabilities` with plain words ("books review", "to-do")
   finds the capability.
2. `cybooks_describe_capability` publishes its arguments. Do this once per
   capability before the first call.
3. `cybooks_read_capability` runs a read; `cybooks_write_capability` runs
   anything that changes data.

Arguments are passed as the description publishes them, usually
`{ "query": { ... } }` for a read.

## The steps

**1. Who and what.** Call `cybooks_auth_status`. It names the company and the
person's permissions. Reading a review needs `view_books_review`.

**2. Read the latest review.** `cybooks_read_capability` with
`cybooks_get_books_review` and

```json
{ "query": { "period_from": "2026-06-01", "period_to": "2026-06-30", "profile": "month_end" } }
```

`profile` is `quick`, `month_end` or `year_end`. The answer is either
`status: completed` with the `review`, or `status: none`.

**3. No review yet, or it is old.** Ask before starting one. A run is a
write: it records a review in the company's history, writes a summary, and
may email the review to the people on the company's review schedule. With a
yes, call `cybooks_write_capability` with `cybooks_run_books_review`, the
same three fields in `body`, and an `idempotency_key`. It needs
`resolve_books_review`. One run at a time per company: if one is already in
flight, follow that one. Then read the review again until it is
`completed`. Compare `completed_at` with today and say how old the review
is.

**4. Read the findings as written.**

- `outcome_counts`: `pass`, `exception`, `insufficient_data`,
  `not_applicable`. These are Passed, Needs a look, Could not be checked and
  Not relevant.
- `claim_counts` splits the same checks by what each may claim: `passed`,
  `needs_a_look`, `looks_right`, `worth_a_look`, `could_not_be_checked`,
  `not_relevant`. Use this split for every total in the report, so a scored
  check is never counted as passed.
- `findings[]`: `check_code`, `title`, `scope`, `grade` (`ledger` is worked
  out, `judgment` is scored), `status`, `claim`, `severity`, `count`,
  `monetary_impact`. Use the `title` and the `claim` Cybooks returns.
- At most 50 findings come back. When `findings_truncated` is true, say how
  many there are in total.
- `not_checked_for_you` lists what the checks could not look at. Carry it
  into the report in full.

**5. Evidence for one finding.** Read `cybooks_get_books_review` again with
`finding_id`. It returns the records behind the finding (at most 50 rows,
with the total), the standard, and whether the finding was resolved and with
what note. Open evidence only for findings the person asks about, or for the
ones that need a look.

**6. What a person still has to answer.** `cybooks_list_todos` with
`{ "query": { "filter": { "period": "2026-06" } } }` lists the month's
to-dos, including findings that became a to-do. Count those whose `status`
is `open`, `waiting` or `later`: all three still hold the close. The row
with `kind: close` is the month's close itself. Needs `view_dashboard`.

**7. Is the month already closed?** `cybooks_get_period_lock` returns the
dates up to which the books are closed. It needs `manage_period_lock`; when
the person does not have it, say the close state was not read.

## Rules for this path

- **`monetary_impact: null` means no amount, not zero.** Do not print 0.
- **Withheld figures.** `payroll_withheld: true` or `salary_hidden: true`
  means the person may not see pay. Report the check, its answer and its
  count; say the amount is withheld.
- **A refusal is an answer.** A `403` names a missing permission. Say which
  check or step could not be read and why. Do not look for another route to
  the same data.
- **Fixes are made in Cybooks.** Each finding has an owning screen (the
  bill, the bank line, the VAT return). Name it. Answering a to-do can
  change the books, so it is done in Cybooks under To do, not from this
  skill. `cybooks_get_todo` may be read to show what the to-do asks.
- **Closing the month is the person's act.** The month is closed in Cybooks
  under To do. This skill does not close or reopen a month.
- **Findings in a filed or closed period** are corrected in the open period.
  Cybooks routes them there; say so rather than suggesting an edit to the
  old period.
- **Rate limits.** A `429` carries the seconds to wait. Wait, then go on.

## When Cybooks and a file disagree

If the person also uploads an export, the live books win for anything
Cybooks worked out. Show the difference as its own line ("the uploaded trial
balance differs from the books by ...") and do not blend the two.
