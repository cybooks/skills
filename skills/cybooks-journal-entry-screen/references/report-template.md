# Journal entry screen: the report format

Return this structure every run, sections in this order.

---

# Journal entry screen: [period]

**Company:** [name] · **Source:** [Cybooks, read (date and time) / file
name] · **Entries:** [n] ([n] manual, [n] system, or "the file does not say
which are manual") · **Dates:** [first] to [last] · **Tests run:** [n] of
15 · **Floor for small entries:** [amount] ([basis]) · **Run:** [date]

## How the file was read

[Only when the file needed work before it could be screened: how it was
flattened, how an entry was defined, what counts as manual, which entries
of a manual journal were counted as system (how many, by kind, and the
largest by name and amount), the totals check (debits equal credits), how
many entries are batches, entries with lines on more than one date, and
any pattern passed to the script. One short bullet each. Leave the section
out for a file that was read as it came.]

## Read this first

This screen looks for the patterns a reviewer tests in a journal. A flagged
entry matches a pattern; it is not a finding that anything is wrong. Most
have a routine explanation. The screen covers only the entries it was given
and does not see the documents behind them.

## Worked out

| Test | Result | Entries | Amount |
|---|---|---|---|
| Every entry balances | [Passed / Needs a look / Not run: reason] | | |
| No entry is booked twice | | | |
| Nothing was recorded after the close | | | |

## Patterns

| Test | What the file shows | Read |
|---|---|---|
| Backdated entries | [n] recorded more than [n] days after their date | [Nothing stands out / Worth a look / Not run: reason] |
| Period-end clustering | [x] times the daily norm in the last two working days | |
| Weekend and night | [n] weekend, [n] night | |
| Round amounts | [x]% of manual entries, [y]% of all | |
| Just under an approval limit | [n] under [limit] | |
| First digits | deviation [x], chi-square [y] on [n] entries of all kinds, or "not run: [n] entries, needs 500" | |
| Who keyed the manual entries | top person [x]% of manual amount | |
| Rare pairings | [n] manual entries above the floor | |
| Manual entries on control accounts | [n] entries, [amount] | |
| Manual credits to income | [n] entries, [amount] | |
| Weak descriptions | [n] entries above the floor | |
| Reversals | [n] pairs, [n] across months, [n] chains | |

## Entries worth opening (top [n] of [total], at most 25)

| # | Entry | Date | Amount | Debit to credit | Matches | Usual explanation | Settle by |
|---|---|---|---|---|---|---|---|
| 1 | [number] | | | [account to account] | [tests, in plain words] | [from tests.md] | [one specific step] |

## The rest, by test

[For flagged entries beyond the list above: count and total per test, from
the script's `beyond_the_list_by_test`. No rows.]

## Not run

| Test | Why | What would enable it |
|---|---|---|

[Leave the section out when every test ran.]

## Suggested order

1. [What a worked out test found first: entries that do not balance, are
   booked twice or were recorded after the close. Then manual credits to
   income, then manual entries on control accounts, then the rest. Name
   the entries.]

---

## Rules for the report

- Never the words fraud, manipulation, misstatement or error for a flagged
  entry. Never clean, verified, audited or compliant for the journal.
- A worked out test may say Passed. A pattern test never does: its best
  outcome is "nothing stands out".
- A test that did not run is "Not run" with its reason. It is not a pass.
- The first-digit test never appears against a single entry.
- Every figure comes from the script's output. Quote it; do not round a
  rate into a different one or restate a count from memory.
- "Tests run" is the script's `tests_ran`. Where a test ran in part (weekend
  without night, people without approver), say so in its row.
- Questions you would have asked (the close date, approval limits, how
  manual entries are marked) go at the end, each with the assumption you
  ran on.
- Amounts in the books' currency, two decimals, in the number format of the
  person's own message (1,234.56 when they write in English).
- Connected to Cybooks: say that times are UTC, and that the people tests
  were not run because the journal read carries no person.
