---
name: cybooks-month-end-close
description: >-
  Walks a month-end close the way Cybooks does: a fixed catalogue of checks
  over bank and cash, money in, money out, VAT and VIES, payroll, assets and
  the ledger, each answered as passed, needs a look, could not be checked or
  not relevant, with a close report and a next step for every open item.
  Works on its own from exports (trial balance, journal detail, bank
  statements, aged receivables and payables), or connected to Cybooks, where
  it reads the checks Cybooks ran on the live books. Use when someone wants
  to close the month, run a month-end review, go through a close checklist,
  or see what is still open before closing a period. Triggers include "close
  the month", "month-end close", "month-end review", "close checklist",
  "what is left before we close", "run the checks", and "year-end prep".
  Built for Cyprus companies (VAT, VIES, GeSY); the ledger, bank and cut-off
  checks apply to any double-entry books.
license: MIT. See LICENSE.txt.
metadata:
  author: "Cybooks - cybooks.com.cy"
  version: "1.0.1"
---

# Month-end close

## What this skill does

A close is a list of questions about one period: does the bank agree, is
everything that was sold and bought in the books, does the VAT account tie to
the return, was payroll booked. This skill asks the same questions in the
same order every month and writes down the answer to each, so the close does
not depend on who runs it.

The questions are the check catalogue in `references/checks.md`. It is the
catalogue Cybooks runs on its own customers' books, published so anyone can
use it.

It runs in one of two ways. Decide which before anything else:

| | Connected to Cybooks | On its own |
|---|---|---|
| When | Tools named `cybooks_*` are available in this conversation | No Cybooks tools |
| Who works the checks out | Cybooks, on the live books | You, with code, on the files the person gives you |
| Coverage | The whole catalogue | The checks the files can support; the rest are "could not be checked" |
| Read next | `references/cybooks-connected.md` | "Working from files" below |

Never mix the two in one figure. A number in the report is either what
Cybooks returned or what your code computed from a named file.

## Rules that hold in both modes

These are not style. Breaking one makes the report wrong.

1. **Read only.** This skill looks at the books. It posts nothing, edits
   nothing and closes nothing. If the person asks for a fix, say where it is
   made; do not make it as a side effect of a review.
2. **Four answers, never three.** Every check ends as one of: **Passed**,
   **Needs a look**, **Could not be checked**, **Not relevant**. "Could not
   be checked" is its own answer. It is never shown, counted or summarised as
   passed, and never as a failure either.
3. **Two grades of check.** A *worked out* check compares figures and can say
   "passed". A *scored* check weighs likelihood (a bill that looks like a
   duplicate, a category that looks wrong) and can only say **Looks right**
   or **Worth a look**. Never word a scored result as passed, in a row or in
   a total.
4. **Figures are computed, never estimated.** Connected: use the figures
   Cybooks returns, unchanged. On its own: run code over the file. If you
   cannot compute it, the answer is "could not be checked".
5. **No assurance words.** Never call the books compliant, clean, audited,
   verified or certified. This is a review of what the books show, not an
   opinion on them.
6. **A filed or closed period is not edited.** When a finding sits in a
   period whose VAT return is filed or whose books are closed, the next step
   is a correction in the open period, never a change to the old one.
7. **Say what was not looked at.** Every report ends with what the checks
   could not see: anything not recorded in the books, what the documents
   actually say, whether things exist, what happened after the period, and
   whether the business can keep going.
8. **Withheld is not zero.** If a figure is hidden from the person asking
   (payroll, for example), say it is withheld. Do not print 0 and do not add
   it into a total.

## The order of a close

Work the areas in this order. Earlier areas feed later ones: an unmatched
bank line is often the missing bill.

1. **Bank and cash** (BNK)
2. **Money in** (AR)
3. **Money out** (AP)
4. **People** (PPL)
5. **Assets and stock** (AST, STK)
6. **VAT, VIES and OSS** (VAT, VIE, OSS)
7. **The ledger itself** (LDG)
8. **Related parties and year end** (REL, YE). Most run at year end only;
   CB-REL-01 also runs at month end

Three depths: **quick** (the core ledger and bank checks, and overdue VAT
returns), **month end** (everything a monthly close needs; the default),
**year end** (adds the IP Box, director balances, comparatives, retained
earnings, provisional tax and the limitations a pack for the accountant has
to state). Each check in the catalogue names the depths it runs in. Ask
which depth only if the request does not make it plain.

## Working from files

1. **Name the period.** First and last day. Ask if it is not given.
2. **Take stock of the files.** For each file say what it is, the period it
   covers and its row count. The list in `references/checks.md` says which
   files each check needs. Minimum useful set: the trial balance at the
   period end and the journal or general ledger detail for the period.
   Better: add the prior period's trial balance, bank statements or a bank
   reconciliation, aged receivables and aged payables, the VAT workings and
   the payroll summary.
   **A general ledger export on its own** is enough to start.
   - If it is one sheet or block per account, flatten it to one row per
     line. Find the column header row on each sheet (the header block
     above it varies in length) and take the account from the heading.
   - Drop the rows that are not postings (opening balance, total, closing
     balance, grand total) and check that the postings' debits equal their
     credits.
   - Build the trial balance from each account's own closing balance as the
     export prints it. A prior-year result row is part of the opening
     position, not a posting. Say in the Source line that the trial balance
     comes from the same file: CB-LDG-01 then tests the file's own
     arithmetic, not an independent document.
   - Bills are the purchase journal's entries that credit payables, with
     the supplier from that line; invoices are the sales journal's entries
     that debit receivables. Credit notes are neither.
   - Say what the export's own header says it leaves out (a filter on
     corrections or on unposted entries). If you cannot read the header
     with confidence, give your reading and say it is uncertain.
   - If the export was made long after the period end, say the books are
     shown as they stood on that date.
3. **Run every check the files support, in catalogue order, with code.** Use
   the "From files" test of each check. A check's answer comes from that
   test alone. Where the catalogue says a further test "goes further", or
   you notice something no check covers, report it under "Also noticed":
   it is not counted and does not change the check's answer. "Earlier
   lines" in a scored check means everything before the period that the
   files hold. It is the nearest equivalent of what
   Cybooks tests on live books, not the same test; where the catalogue says
   the two differ, say so beside the result. No check is skipped silently:
   one that lacks its file, or is marked "Cybooks only", is "could not be
   checked", with what would enable it.
4. **Write the report** in the format of
   `references/close-report-template.md`.
5. **Offer the next step:** go through the open items one by one, or run
   again after fixes so the two reports can be laid side by side.

If the person gives only a profit and loss, say that most checks need the
trial balance and ask for it. Do not produce a thin report from a summary.

## Books that are not Cypriot, or not in English

- **Account names.** The catalogue names accounts in English (holding,
  suspense, clearing, retained earnings). Match by meaning, not by word,
  and say in the report which accounts you took for which.
- **Cyprus-only parts.** These rest on Cyprus rules: the VAT return boxes
  in CB-VAT-01, the due dates in CB-VAT-06, GeSY in CB-PPL-02, the IP Box
  in CB-AST-03 and provisional tax in CB-YE-03. For another country, run
  the general part of each check (the tax account clears to the return,
  the payroll liability ties to the payslips). CB-VAT-06 has no general
  part: it is all due dates. You may use the local rule
  in place of the Cyprus one only if you state the rule in the report and
  say that it is yours, not this catalogue's. Otherwise the part is "could
  not be checked".
- **Corrections to a filed period.** Say that the correction belongs in the
  open period. How it is filed in that country is a question for their
  adviser; do not advise on it.

## Sister skills

Three other Cybooks skills go deeper on one part of the close. Use them when
they are installed; do not invoke a skill with a similar name that is not one
of these.

- `cybooks-journal-entry-screen`: screens the period's journal entries for
  the patterns a reviewer tests (timing, round amounts, reversals, entries on
  control accounts).
- `cybooks-close-readiness-scorecard`: turns the close into one verdict,
  ready to close or not yet, with the shortest path to ready.
- `cybooks-cyprus-vat-return`: reviews the Cyprus VAT return box by box and
  builds the files for the tax portal (the VAT return and the monthly VIES
  statement).

## What this skill is not

It is not an audit, not tax advice and not a substitute for the accountant
who signs the accounts. Cyprus due dates are in the catalogue as Cybooks holds
them; the Tax Department often extends one, so confirm a date against its
current calendar before relying on it. On its own, the skill sees only the files it
is given and cannot tell whether they are complete.
