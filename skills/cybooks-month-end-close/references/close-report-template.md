# Close report: the format

Return this structure every run, sections in this order. Leave a section out
only where it says so.

---

# Month-end close: [month year]

**Company:** [name] · **Period:** [first day] to [last day] · **Depth:**
[quick / month end / year end] · **Source:** [Cybooks, review completed
(date and time) / files: list each file] · **Run:** [date]

## Where the close stands

[Two or three sentences. How many checks need a look, the one that matters
most and why, and what would change the picture. If the read is limited,
say so in the first sentence.]

| | Checks |
|---|---|
| Passed | [n] |
| Needs a look | [n] |
| Looks right (scored) | [n] |
| Worth a look (scored) | [n] |
| Could not be checked | [n] |
| Not relevant | [n] |

## By area

| Area | Passed | Needs a look | Looks right | Worth a look | Could not be checked | Not relevant |
|---|---|---|---|---|---|---|
| Bank and cash | | | | | | |
| Money in | | | | | | |
| Money out | | | | | | |
| People | | | | | | |
| Assets and stock | | | | | | |
| VAT, VIES and OSS | | | | | | |
| The ledger | | | | | | |
| Related parties and year end | | | | | | |

[The columns add up to the table above. Checks outside the chosen depth are
not counted; name them in one line under the table.]

## Needs a look

One row per finding, largest effect first. Every row names its check.

| Check | What was found | Records | Amount | Next step |
|---|---|---|---|---|
| [code, title] | [one plain sentence] | [count] | [amount, "no amount" or "withheld"] | [where it is fixed and how] |

## Worth a look

Scored checks only. These are likelihoods, not errors.

| Check | What stands out | Records | Next step |
|---|---|---|---|

[Leave the section out when there are none.]

## Could not be checked

| Check | Why | What would enable it |
|---|---|---|

[Leave the section out when there are none.]

## Answered without a finding

- **Passed:** [each check, with the figure that shows it in a few words]
- **Looks right (scored):** [each check; say when the test had little to
  work with]
- **Not relevant:** [each check, with the reason]

## Also noticed

[Things outside a check's own test: the result of a test the catalogue
says "goes further", or something no check covers (a loan in debit, an
accrual used three times). One line each, with the account and amount.
Not counted in the tables. Leave the section out when there is nothing.]

## What was not checked for you

- Anything not recorded in the books.
- What the documents actually say.
- Whether things exist.
- What happened after the period.
- Whether the business can keep going.

[Connected: use the list Cybooks returned instead.]

## Next steps

[A numbered list in the order to do them. Bank first, the ledger last. End
with how the month is closed: in Cybooks under To do, or in the person's own
system.]

---

## Rules for the report

- Plain words. "Needs a look", not "exception". "Could not be checked", not
  "insufficient data". "Holding account", not "suspense account", unless the
  account is named that.
- Never compliant, clean, audited, verified or certified.
- A scored check is never in the Passed row or the Passed column.
- Amounts in the books' currency, two decimals, in the number format of the
  person's own message (1,234.56 when they write in English). A missing amount is "no amount"; a hidden one is "withheld".
- Every figure is either returned by Cybooks or computed by code from a
  named file. Say which in the Source line.
- Made from files: say once, under "Where the close stands", that each test
  is the nearest equivalent of the Cybooks check with that code, and that
  checks marked "Cybooks only" could not be run.
- Made from files: a check that only lists (CB-PPL-03, CB-REL-02,
  CB-YE-04) is reported as what it lists, not as passed; CB-PPL-03 is
  counted as Could not be checked. Connected: use the answer Cybooks
  returned.
- Where a local rule stood in for a Cyprus one, or an account was taken for
  a holding account by its meaning, say so in that check's row.
- "Records" is the count of what the finding is about: lines, documents,
  accounts or returns. Say which.
- What a check "cannot see" goes into its row when it bears on the answer
  ("a real repeat charge looks the same").
- The same sections in the same order every run, so two reports can be laid
  side by side.
