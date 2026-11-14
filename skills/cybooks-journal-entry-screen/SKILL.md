---
name: cybooks-journal-entry-screen
description: >-
  Screens a period's journal entries for the patterns a reviewer or auditor
  tests: entries that do not balance, duplicates, entries recorded after the
  period was closed, backdating, period-end clustering, weekend and night
  postings, round amounts, amounts just under an approval limit, first-digit
  (Benford) analysis, manual entries on control accounts and income, rare
  account pairings, weak descriptions and reversal chains. A bundled script
  computes every figure. Works on its own from a journal or general ledger
  detail export (CSV or Excel), or connected to Cybooks, where it reads the
  journal from the books. Use when someone wants journal entries reviewed,
  screened or tested. Triggers include "screen my journal entries", "review
  the manual journals", "journal entry testing", "what will the auditors
  pick", "anything odd in the ledger", "Benford analysis", or a journal
  export uploaded with a question about what stands out.
license: MIT. See LICENSE.txt.
metadata:
  author: "Cybooks - cybooks.com.cy"
  version: "1.0.1"
---

# Journal entry screen

## What this skill does

Anyone who reviews a set of books reads the journal: an accountant taking
over a client, an auditor, an owner before a close. They look for the same
shapes every time. This skill looks for those shapes first, with code, and
returns a short ranked list of entries worth opening, each with the usual
harmless explanation and the step that settles it.

It answers two different kinds of question and keeps them apart:

- **Worked out.** Does every entry balance? Is any entry booked twice? Was
  anything recorded in a period after it was closed? These have a right
  answer. They can pass.
- **Patterns.** Round amounts, entries at night, a rare pair of accounts.
  These have no right answer. They are never a pass or a fail, only "worth a
  look", and most have a routine explanation.

## Two ways to run

| | Connected to Cybooks | On its own |
|---|---|---|
| When | Tools named `cybooks_*` are available | No Cybooks tools |
| The journal comes from | The live books, read through Cybooks | The export the person uploads |
| Read next | `references/cybooks-connected.md` | "From an export" below |

`scripts/` and `references/` are folders of this skill, beside this file.
When the working directory is somewhere else, give the script its full
path.

Either way the same script runs the same tests, so two reports are
comparable.

## Rules

1. **Computed, not eyeballed.** Every count, rate and statistic comes from
   `scripts/je_screen.py`. If code cannot be run in this conversation, say
   so and stop at a description of what the screen would do. Do not read a
   few hundred rows and guess.
2. **Read only.** Nothing is posted, reversed or corrected.
3. **A flag is a pattern, never a verdict.** Do not use the words fraud,
   manipulation, misstatement or error for a flagged entry. The vocabulary
   is "matches [pattern]", "worth a look", "settle it by [step]".
4. **Every flag carries its harmless explanation.** `references/tests.md`
   gives one per test. A list of flags without them reads as an accusation.
5. **Skipped is said out loud.** A test that lacks its column or its
   population is listed as not run, with the reason and what would enable
   it. It is never left out silently and never counted as passed.
6. **The file is its own baseline.** Rates are compared with the rest of the
   same file, not with an outside benchmark.
7. **No assurance words.** The screen does not make the journal clean,
   verified or audited. It says what it looked at and what it found.

## From an export

1. **Get the right file.** It must be line level: one row per journal line,
   with at least a date, an account and an amount. A trial balance or a
   profit and loss cannot be screened; say so and ask for the journal or
   general ledger detail. Read an Excel workbook with code and write it out
   as CSV. If the workbook cannot be read in this conversation, ask for a
   CSV export; do not retype figures.
2. **Run the script.**

   ```bash
   python3 scripts/je_screen.py journal.csv \
     --period-start 2026-06-01 --period-end 2026-06-30 \
     --closed-on 2026-07-05 --thresholds 1000,5000
   ```

   Columns are matched by name. When a column is not found, map it:
   `--map entry_id="Journal No" --map recorded_at="Created"`. Run with
   `--help` for every option. Dates like 03/04/2026 are read day first;
   pass `--monthfirst` for a US export (the script works the order out
   itself when a date makes it plain, and refuses a file that mixes both).
   Decimal commas are detected. Lines with no date take the date and entry
   of the line above.
   **Ledger-card exports.** Many systems export the ledger as one sheet or
   block per account, with an opening balance, the lines, and a total. That
   is line level, but not yet one table. Flatten it with code first: one
   row per line, the account taken from the sheet or block heading. Drop
   every row that is not a posting: opening balance, total, closing
   balance, grand total, difference, prior-year result. Then check two
   things: each block's printed total equals its opening balance plus its
   lines, and total debits equal total credits. If either fails, the
   flattening is wrong; fix it before screening.

   **Entry numbers.** An entry is every line that shares one entry number.
   Where numbers restart per journal, join the journal code and the number.
   In many systems one bank statement or pay run is a single entry with
   dozens of lines. The script calls an entry of more than 12 lines a
   batch: its amount is the gross of all its lines, and it is left out of
   the pairing and reversal tests. Say in the report how many batches
   there are and what they are.

   **Other languages and systems.** Map the columns with `--map`. Say how
   manual entries are marked with `--manual-values` (a journal called
   "Memoriaal", "General journal", "Diverse"). A manual journal often also
   holds postings the system wrote itself: a VAT return posting, a cost
   spread over months, a payroll import, a year-end transfer. The rule: a
   posting a schedule or an import generated is system; one a person keyed
   is manual. Name the generated ones with `--system-descriptions` (a
   pattern over the description). They then leave every test that looks at
   manual entries, so report the split (how many, by kind) and name the
   largest from the script's `largest_counted_as_system`: a reviewer will
   want to see a large tax posting even when the system wrote it. Account names are matched in English; for another chart
   pass `--control` and `--income` with patterns that fit it. Control
   accounts are the ones documents post to: receivables, payables, tax,
   retained earnings, and holding, suspense or clearing accounts. An
   account that routine postings touch all the time (deferred costs,
   accruals) is not one.
3. **Print the profile before anything else:** entries, date range, manual
   against system entries, which columns were found and which were not. It
   is the denominator of every rate that follows.
4. **Ask only for what changes the result:** the day the period was closed
   (enables the after-close test, but only when the file has a recorded-at
   column; without one, ask for an export that has it), approval limits (enables the
   just-under-a-limit test), and how manual entries are marked if the
   script found none (`--manual-values`).
5. **Write the report** in the format of `references/report-template.md`.
6. **Offer the next step:** open one cluster, record the person's
   explanations against each entry to make the annotated version, or run
   the same screen on the next period.

## What each missing column costs

| Missing | Tests not run |
|---|---|
| Entry number | Balance, duplicates, rare pairings, reversals (lines cannot be grouped) |
| Source or type | Manual entries on control accounts and income; every other test then runs on all entries instead of manual ones |
| Recorded-at date | After close, backdating; weekend falls back to the entry date; night is not run |
| Posted by | People |
| Approved by | Keyed and approved by the same person |
| Description | Weak descriptions |
| Counterparty (customer or supplier) | None, but duplicates are then matched without it, so two customers billed the same amount on one day look like a duplicate |

## What this skill is not

It is not fraud detection, not an audit and not an opinion. It sees only the
entries it is given and cannot tell whether the export is complete. It does
not see supporting documents. A quiet report means none of these patterns
appeared, nothing more.

Sister skills, used when installed: `cybooks-month-end-close` (the full
catalogue of close checks) and `cybooks-close-readiness-scorecard` (one
verdict before closing, which uses this screen for its evidence dimension).
