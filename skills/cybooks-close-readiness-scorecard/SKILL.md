---
name: cybooks-close-readiness-scorecard
description: >-
  Answers one question before a period is closed: are the books ready, or
  not yet? Compares the trial balance at the period end with the prior
  period, scores six dimensions (bank and cash, completeness, tax and
  payroll, movements explained, balance sheet sense, evidence and trail)
  with a fixed rubric, and returns a one-page scorecard with a verdict and
  the shortest path to ready. A bundled script computes every movement and
  balance test. Works on its own from trial balance exports (CSV or Excel),
  or connected to Cybooks, where it reads the live trial balance, the checks
  Cybooks ran and the month's open to-dos. Use when someone asks whether a
  close is ready or wants the books reviewed before closing or locking a
  period. Triggers include "is the close ready", "can we close June", "can
  we lock the period", "review my close", "close readiness", or a trial
  balance uploaded with a request for a pre-close review.
license: MIT. See LICENSE.txt.
metadata:
  author: "Cybooks - cybooks.com.cy"
  version: "1.0.2"
---

# Close readiness scorecard

## What this skill does

Before a month is closed someone has to decide that it is done. That
decision is usually a feeling. This skill makes it a scorecard: the same six
dimensions, the same tests, the same page, every close. A scorecard made on
day 3 and another on day 5 can be laid side by side.

It is the verdict layer. It does not do the close and it does not fix what
it finds. It says what stands between the books and a close, in the order to
clear it.

## Two ways to run

| | Connected to Cybooks | On its own |
|---|---|---|
| When | Tools named `cybooks_*` are available | No Cybooks tools |
| Inputs | The live trial balance at both dates, the checks Cybooks ran, the month's open to-dos | Trial balance exports, plus whatever supporting files the person has |
| Read next | `references/cybooks-connected.md` | "From exports" below |

`scripts/` and `references/` are folders of this skill, beside this file.
When the working directory is somewhere else, give the script its full
path.

## Rules

1. **Computed, not eyeballed.** Every movement, percentage and balance test
   comes from `scripts/tb_compare.py`, from a check Cybooks ran, or from
   your own code over a file you name (a ledger export, a bank statement). If code
   cannot be run in this conversation and Cybooks is not connected, say so
   and stop.
2. **Read only.** The scorecard closes nothing and changes nothing.
3. **Every finding names an account** (code, name, balance) or a Cybooks
   check code. No finding without a source.
4. **Two kinds of finding, always labelled.** **Worked out**: a figure
   compared with a figure (the trial balance does not balance, the aged
   receivables differ from the control account, a Cybooks check). **Read
   from the balances**: an inference (a prepaid balance that did not move
   suggests the release was not booked). An inference is a question for the
   person, never an accusation, and is worded as one.
5. **A gap is never filled with an assumption.** A dimension without its
   input is "Not assessed", with the file that would enable it.
6. **One trial balance is a limited read.** Without a prior period there
   are no movements, and the verdict is never "Ready to close".
7. **No assurance words.** "Ready to close" means nothing in this rubric
   stands in the way. It does not mean the books are correct, clean,
   verified or audited, and the scorecard says so.
8. **A filed or closed period is not edited.** The next step for a finding
   in one is a correction in the open period.

## From exports

1. **Check the input.** A trial balance: one row per account with a balance
   or debit and credit columns, at a stated date. A profit and loss alone
   cannot support the rubric; say so and ask for the trial balance. Read an
   Excel workbook with code and write it out as CSV; if it cannot be read
   in this conversation, ask for a CSV export.
2. **Run the script.**

   ```bash
   python3 scripts/tb_compare.py --current tb-june.csv --prior tb-may.csv --prior-months 5
   ```

   `--prior-months` is how many months of the financial year the prior
   trial balance covers (5 for May in a calendar year). Income and expense
   balances are cumulative, so the script reads their movement as the
   period's activity and compares it with the monthly run rate before.
   Columns are matched by name; map them with
   `--map code="Account No"` when they are not found. An account class or
   type column enables the wrong-side test and tells income and expense
   accounts from the rest. Without one, pass `--income` and `--expense`
   with a pattern over "code name" (`--income "^4" --expense "^[5-7]"`);
   otherwise ordinary monthly activity shows up as a movement and the
   script says so under `not_assessable`. Run with `--help` for every
   option.
   Account names are matched in English (suspense, accrued, prepaid, bank,
   stock, accumulated depreciation, retained earnings). For a chart in
   another language pass your own patterns for all of them: `--holding`,
   `--accrual`, `--bank`, `--stock`, `--contra`, `--retained`. A pattern is
   matched against "code name", so it can be tied to a range of codes
   (`^11\d{3} ` for bank accounts) as well as to words; that is safer than
   a word that also appears in a cost account's name. Say in the report
   which patterns you used.

   **No trial balance, only a general ledger export?** If it carries an
   opening balance per account, build both trial balances from it with
   code:
   - balance at a date = opening balance plus the movements up to that
     date (by posting date, or by financial period if the export has one);
   - check each account against the closing balance the export prints, and
     total debits against total credits, before going on. Exports differ in
     whether a total row includes the opening balance and on which side a
     special row sits: trust the reading that ties, and say which you used;
   - if the export shows last year's result on its own row, add it as its
     own line named "Prior year result";
   - add a class column (Assets, Liabilities, Equity, Income, Expenses) if
     you can tell the class from the chart's numbering or names. Where the
     two disagree, the name wins. Say that the classes are yours: the
     wrong-side test rests on them. Leave blank what you cannot tell;
   - say what the export leaves out, if its header says so (a filter on
     corrections or on unposted entries).

   A ledger export also holds every line, so it can explain a movement the
   way a live ledger can: see dimension 4 in the rubric.
3. **Do not compare across a year end.** If the script warns that income
   accounts shrank, the two files sit either side of a year end. Compare
   balance sheet accounts only and say so.
4. **Ask for explanations of the flagged movements** before scoring
   dimension 4. One message, the list of accounts, one line each. If the
   person wants the scorecard first, score dimension 4 on what the ledger
   shows and put the same list at the end of the scorecard.
5. **Score the six dimensions** with `references/rubric.md`, in order,
   skipping none.
6. **Write the scorecard** in the format of
   `references/scorecard-template.md`.
7. **Offer the next step:** go through the open items one by one, or run
   again after fixes.

Supporting files raise an inference to a worked out finding, or clear it:
a bank reconciliation, aged receivables and payables, the VAT workings, the
payroll summary, an accruals schedule, the close checklist. Use each one
the person gives; do not ask for all of them up front.

## Sister skills

Use them when installed. Do not invoke a skill with a similar name that is
not one of these.

- `cybooks-month-end-close`: the full check catalogue. When it has been run
  for the period, its findings feed dimensions 1, 2, 3 and 5.
- `cybooks-journal-entry-screen`: screens the period's journal entries.
  When a journal export or a Cybooks connection is available, its result is
  dimension 6. Without it, dimension 6 runs the reduced tests in the rubric.
- `cybooks-cyprus-vat-return`: reviews the Cyprus VAT return box by box.
  When it has been run for the period, its open findings belong in
  dimension 3.

## What this skill is not

It reviews the books as they stand. On its own it cannot tell whether the
balances agree with the bank, the payroll provider or the tax portal: that
needs those documents, or books that are connected to them. It is not an
audit and not tax advice.
