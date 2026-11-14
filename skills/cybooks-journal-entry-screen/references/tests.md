# The tests

`scripts/je_screen.py` runs all of them in this order. Each test below
gives: what it computes, when it runs, the usual harmless explanation, and
how a flag is settled. The key in brackets is the test's name in the
script's JSON.

Most pattern tests run on **manual entries** only, because a person chose
those amounts, dates and accounts. If the file has no source column, they run
on all entries and the report says so.

**Materiality.** Several tests ignore small entries. The floor is
`--materiality` when given, otherwise the 75th percentile of entry totals in
the file. State the floor and its basis in the report.

## Worked out (these can pass)

### 1. Every entry balances [`balance`]

Debits equal credits per entry, to the cent. Also lists entries with a
single line. Needs an entry number.
*Usual explanation:* the export was cut (one side filtered out by account or
date), or amounts were rounded on export. Check the export before the books.
*Settle by:* re-exporting without filters; if it still differs, open the
entry.

### 2. No entry is booked twice [`duplicates`]

Entries above the floor with the same date, the same accounts and the same
amounts under different numbers. When the file has a counterparty column,
the counterparty must be the same too; without it, say that two customers
billed the same amount on one day will show up here.
*Usual explanation:* two real payments of the same amount on one day (rent
for two units, two identical subscriptions).
*Settle by:* matching each to its own document.

### 3. Nothing was recorded after the close [`after_close`]

Entries dated in the period but recorded after the day it was closed. Needs
the recorded-at column, `--period-end` and `--closed-on`.
*Usual explanation:* a late supplier bill or an accountant's adjustment,
both legitimate. Each should have a reason and, where a return was already
filed, a correction in the open period instead.
*Settle by:* a reason per entry; move the ones that touch a filed return.

## Timing patterns

### 4. Backdated entries [`backdated`]

Recorded more than `--backdate-days` (30) after their own date.
*Usual explanation:* catching up on a backlog, an imported history, a late
document.
*Settle by:* confirming the date on the document.

### 5. Period-end clustering [`period_end`]

For each month with 20 or more entries: entries in the last two working days
against the month's daily average. A signal above three times the daily
norm. Entries are flagged only in a month that trips it.
*Usual explanation:* a normal close. Most closes cluster. What matters is a
change against earlier months, so read the month table, not one figure.
*Settle by:* comparing with the prior months in the same table.

### 6. Weekend and night [`weekend_night`]

Recorded on a Saturday or Sunday, or between 22:00 and 06:00 (needs a time
in the recorded-at column). Without that column it uses the entry date and
says so, and it leaves out entries dated the last day of a month: a
month-end date says nothing about when the entry was keyed.
*Usual explanation:* a small team closing on a Sunday, a scheduled job, a
person in another time zone. Timestamps are often UTC: check before reading
anything into an hour.
*Settle by:* asking who keyed it.

## Amount patterns

### 7. Round amounts [`round`]

Entries of exactly a whole thousand. Reports the rate among manual entries
beside the rate in the whole file.
*Usual explanation:* estimates, accruals and loan movements are round by
nature. The question is whether each has a basis written down.
*Settle by:* the schedule or calculation behind it.

### 8. Just under an approval limit [`below_limit`]

Entries within 2 percent below each limit in `--thresholds`. Counts are
always reported; entries are flagged only where three or more sit under one
limit.
*Usual explanation:* coincidence at low counts, or a supplier whose price
happens to sit there.
*Settle by:* checking whether one purchase was split.

### 9. First digits [`first_digits`]

In amounts that arise naturally, the first digit is 1 about 30.1 percent of
the time and 9 about 4.6 percent (Benford's law). The script compares the
file with that curve and reports the mean absolute deviation and a
chi-square statistic. It signals only when the deviation is above 0.015
**and** the chi-square is above 15.507 (8 degrees of freedom, 5 percent).

Guardrails, enforced by the script:

- It runs on all entries, not only manual ones: the curve needs a
  population. Say the population in the report.
- **At least 500 qualifying entries.** Below that the test is skipped and
  the report says so. On a small population it produces confident noise.
- Recurring identical amounts (the same account and amount six or more
  times: rent, salaries, depreciation) and amounts under 10 are left out.
- **It never flags an entry.** It points at a digit range to sample from.

*Usual explanation:* price lists (many 99s and 49s), one large recurring
contract, currency conversion, fixed fees.
*Settle by:* sampling entries starting with the digits above expected.

## People patterns

Need a posted-by column.

### 10. Who keyed the manual entries [`people`]

Share of manual amount by person, entries above the floor keyed by someone
with fewer than five entries in the file (`rare_poster`), and entries keyed
and approved by the same person (`self_approved`, needs an approver
column).
*Usual explanation:* a small team. One bookkeeper keying everything is
normal; report it as an observation about separation of duties, not a flag.
*Settle by:* knowing who has access and why.

## Account patterns

### 11. Rare pairings [`rare_pairing`]

The largest debit account against the largest credit on a different account
of each entry.
A pair that appears twice or less in the file, on an entry above the floor.
Batches are left out.
*Usual explanation:* a one-off event: an asset purchase, a loan, a
correction.
*Settle by:* the document behind the entry.

### 12. Manual entries on control accounts [`control_accounts`]

Manual entries that touch receivables, payables, VAT, retained earnings or a
holding account. In books where invoices, bills and bank lines post to
those accounts, a manual entry there bypasses the customer or supplier
ledger and, for a VAT account, the VAT return. Needs a source column. The
account pattern is `--control`; adjust it to the chart in use.
*Usual explanation:* opening balances, a year-end adjustment by the
accountant, a correction that could not be made on the document.
*Settle by:* checking that the customer or supplier ledger and the VAT
return still tie to the account afterwards.

### 13. Manual credits to income [`manual_income`]

Manual entries that credit an income account. Income normally arrives
through invoices. Pattern: `--income`, less the accounts it matches by
accident (`--not-income`: cost of sales, income tax, deferred income).
*Usual explanation:* accrued income at the period end, a reclassification
between income accounts, grant or interest income with no invoice.
*Settle by:* the contract or calculation behind it. Open these first.

## Description pattern

### 14. Weak descriptions [`descriptions`]

Entries above the floor with no description, or one that says nothing
("adjustment", "reclass", "correction", "misc").
*Usual explanation:* haste. It is not a sign of anything wrong; it is a
question someone will have to answer later.
*Settle by:* writing the reason on the entry now.

## Reversal pattern

### 15. Reversals [`reversals`]

Entries whose lines are the exact mirror of another entry. A pair inside
one month is counted, not flagged. Flagged: a pair that spans two months
(`reversal_across_months`, it moves an amount between periods) and three or
more entries of the same shape within 21 days of an opposite one
(`reversal_chain`: post, reverse, post again). The same posting recurring
month after month (a fixed fee) is not part of a chain. When the file has a
counterparty column, both entries must name the same counterparty.
*Usual explanation:* an accrual reversed the next month, which is how
accruals work; an error corrected in two attempts.
*Settle by:* confirming the reversal was meant to fall in the other month.

## How entries are ranked

- One row per entry, with all its flags.
- An entry that fails a worked out test ranks first.
- Then entries at or above the floor, before entries below it.
- Then by the number of different test families it trips (timing, amounts,
  people, accounts, descriptions, reversals): an entry in two families
  ranks above an entry in one.
- Then by number of flags, then by amount.
- The report shows the top 25. The rest are summarised per test with a
  count and a total, from the script's `beyond_the_list_by_test`. A list of
  400 rows is a dump, not a screen.

## Batches and two-way entries

An entry with more than 12 lines is a batch (a bank statement, a pay run).
Its net movement is not the shape of one posting, so it is left out of the
rare pairing and reversal tests. So is an entry that moves money in and out
of the same account. The profile counts the batches.

## Reading order for the person

Anything a worked out test found first (does not balance, booked twice,
recorded after the close). Then manual credits to income, then manual
entries on control accounts, then the rest.
