# The rubric

Six dimensions, in this order. Apply every test. Each finding names its
account (code, name, balance) or its Cybooks check code, and is labelled
**Worked out** or **Read from the balances**.

The key in brackets is where the figure sits in the output of
`scripts/tb_compare.py`. Check codes (CB-...) are the checks of the
`cybooks-month-end-close` catalogue; connected to Cybooks, their results
come from the books.

**The floor.** Several tests ignore small amounts. The floor is 0.5 percent
of income to date, or 0.5 percent of expenses when there is no income yet,
or the figure the person gives. State the floor and its basis on the
scorecard. "Material" below means at or above the floor.

## 1. Bank and cash agree

- **Holding accounts** [`holding_accounts`]. Any holding, suspense, clearing
  or undeposited funds account with a balance is a finding. It blocks the
  close when the balance is at or above the floor, or when it grew since
  the prior period and is at or above a tenth of the floor: items land
  there faster than they are cleared. Below that it is a note. A balance
  that changed side [`changed_side`] is not smaller: read both figures.
  (CB-LDG-04, CB-LDG-06)
- **A bank or cash balance identical to the prior period**
  [`unchanged`, with the bank note]. Either nothing happened or nothing was
  booked: the two look the same from here, so ask. Read from the balances.
- **Cash on the wrong side** [`wrong_side`, bank and cash accounts]. A bank
  account in credit is an overdraft or an error. It blocks the close until
  the person confirms an overdraft facility; after that it is a note to
  show the balance with liabilities. (CB-BNK-06)
- **Bank reconciliation, when given.** The ledger balance equals the
  statement balance plus or minus the listed open items. Worked out.
  (CB-BNK-01)
- **Transfers.** A transfer account that does not net to zero means one
  side of a transfer between own accounts is missing. (CB-BNK-04)

Without a bank statement or reconciliation, say that the balances were not
agreed to the bank. The dimension can still be scored from the tests above;
it cannot be Clear.

## 2. Everything is in

- **Accruals and prepayments that did not move** [`unchanged`]. A prepaid
  balance identical to last month suggests the monthly release was not
  booked. An accrual identical to last month suggests it was booked once
  and forgotten. Read from the balances.
- **Recurring accruals that vanished** [`emptied_accounts`]. Accrued
  payroll, bonus, leave or audit fee present last period and zero now:
  either it was settled or it was forgotten. Blocks the close until
  answered.
- **Stock that did not move** [`unchanged`, with the stock note] in a
  business that buys and sells goods. Is stock only adjusted at the year
  end, or should this period carry a count? Read from the balances.
- **Accumulated depreciation that did not move** [`unchanged`, with the
  depreciation note]. Was the period's depreciation booked? Read from the
  balances.
- **Round balances with no schedule** [`round_balances`]. A round accrual or
  provision is an estimate. Fine, when its basis is written down. Read from
  the balances.
- **Deferred income that did not move** in a business that bills ahead.
  A cut-off question.
- **Receivables and payables tie, when aged reports are given.** The aged
  total equals the control account at the same date. Worked out.
  (CB-AR-01, CB-AP-01)
- **An account that went quiet** [`went_quiet`]. An income or expense
  account that ran every month and has nothing in the period (needs
  `--prior-months`). Rent, a subscription, a salary line: is the bill or
  the accrual missing? Read from the balances.
- **Recurring costs that skipped the month**, when the ledger by supplier is
  available. (CB-AP-07)

## 3. Tax and payroll tie

- **The VAT account.** Many charts spread VAT over several accounts (input
  VAT, output VAT, VAT payable). Read them together as one position, here
  and not one by one in dimension 5. Its balance should be the open
  period's VAT, after the returns filed and the payments made. A balance that keeps growing
  across periods without payments, or a VAT account on the wrong side with
  no refund expected, is a finding. With the VAT workings: worked out.
  (CB-VAT-02)
- **Reverse charge pairs**, when the workings are given. (CB-VAT-03)
- **EU sales**, when the business sells to EU businesses: the VIES
  statement ties to the invoices. (CB-VIE-03)
- **Payroll liabilities.** Tax, social insurance and health contributions
  owed should be about one month's worth. A balance of several months means
  payments were not booked or not made. With the payroll summary: worked
  out. (CB-PPL-02, CB-PPL-03)
- **Filings.** Nothing overdue for the period being closed. (CB-VAT-06)

From a trial balance alone most of this dimension is read from the
balances. Say so. If nothing here could be tested, the dimension is Not
assessed.

## 4. Movements are explained

- The script flags [`movements`]:
  - balance sheet accounts that moved by at least 10 percent **and** at
    least the floor;
  - income and expense accounts whose activity in the period differs from
    the monthly run rate before by at least 10 percent **and** at least the
    floor (needs `--prior-months`; without it they are listed on the floor
    alone and the scorecard says the run rate was not available).
- Every flagged account needs one of three statuses:
  - **Explained**: the person gave the reason, a document shows it, or the
    ledger lines behind it are identified and ordinary. The lines can come
    from Cybooks or from a ledger export; name them (three invoices to one
    customer, the quarter's rent, one manual journal).
  - **Likely reason**: you can propose one but cannot point at the lines.
    Label it as a proposal.
  - **Unexplained**: nobody knows yet.
- A material movement that is Unexplained blocks the close.
- A Likely reason does not block, but it is an open item: the dimension is
  Notes, not Clear, and the verdict is at best Ready with notes until the
  person confirms it.
- Do not explain a movement with a guess and then count it as Explained. A
  movement that rests on one manual journal with a weak description is not
  ordinary: ask.
- The script's percentages read the same on both sides of the books: a
  positive figure means more activity than the run rate, or a balance that
  grew. Use its `reads_as`.

## 5. The balance sheet makes sense

- **The trial balance balances** [`totals`]. If not, stop: nothing else is
  reliable until it does. (CB-LDG-01)
- **Balances on the wrong side** [`wrong_side`]. An asset in credit, a
  liability in debit, income in debit, an expense in credit. Each is a
  reclassification waiting to happen or an error. Accounts the script marks
  `looks_like_contra_account` (accumulated depreciation, allowances) are
  expected to sit on the other side: leave them out. So are tax accounts
  that form one position together (dimension 3). Material ones block the
  close; the rest are notes, largest first. Needs an account class column;
  if you assigned the classes yourself, say so beside each finding.
- **New accounts** [`new_accounts`]. An account at zero last period with a
  material balance now deserves a line.
- **Emptied accounts** [`emptied_accounts`]. A material balance gone to
  zero: paid, reclassified or written off?
- **Retained earnings** [`retained_earnings`]. Inside a financial year it
  should not move at all; across a year end it moves by the year's result
  and by dividends. Any other movement is a finding. (CB-YE-02)
- **Receivables and payables in proportion.** Receivables growing much
  faster than income is a collection or a cut-off question. A note, not a
  block.

## 6. Evidence and trail

When `cybooks-journal-entry-screen` has run for the period, this dimension
is its result: failed worked out tests block the close; manual credits to
income, entries recorded after the close and manual entries on control
accounts are notes until explained.

Reduced version, without a journal:

- Which balances would a reviewer ask support for, and was any given? List
  the largest that are unsupported as they stand: estimates, provisions,
  accruals, stock, director accounts, balances that look entered by hand.
  These are notes.
- If a close checklist was given: every item still open that corresponds to
  a balance is a finding.
- From a ledger export you may look for bills that look entered twice (same
  supplier, same amount, days apart). Word each as a question; it is a
  note. Only an entry the journal screen worked out as booked twice blocks
  the close.
- Without a journal screen the dimension is Notes at best, never Clear. It
  is Not assessed only when there is no account-level trial balance to
  list from.

## Scoring a dimension

| Status | Means |
|---|---|
| **Clear** | Every test ran and none has a finding |
| **Notes** | Findings exist; none blocks the close |
| **Open** | At least one finding blocks the close |
| **Not assessed** | The input for the dimension was missing |

A finding blocks the close when it is one of these:

- the trial balance does not balance;
- a holding account at or above the floor, or one that grew and is at or
  above a tenth of the floor;
- a material movement that is Unexplained;
- a recurring accrual that vanished with no answer;
- a material balance on the wrong side that is not a contra account and not
  part of one tax position;
- an entry that does not balance, or is booked twice;
- connected to Cybooks: a check that needs a look with high severity, or a
  month the close itself is still waiting on.

**Open items** of a dimension are its findings that block the close or are
to be done before closing, plus, in dimension 4, each flagged movement that
is not Explained. Items for next month are not open items.

One finding, one dimension: put it where the person will fix it (a bank
account in credit is dimension 1, not 5).

**Weight of a finding that does not block.** "Before closing": the answer
could change this period's figures (a balance that did not move, a
liability several months old, a possible duplicate). "Next month": tidying
that changes nothing material now (a balance under a tenth of the floor on
the wrong side, a dormant account). Small items of one kind may share a
row, as long as the row names every account and balance.

## The verdict

| Verdict | When |
|---|---|
| **Ready to close** | Dimensions 1, 2, 4 and 5 are Clear or carry only notes for next month, nothing blocks the close, and both periods were read. If dimension 3 or 6 is Not assessed, the best verdict is Ready with notes, and the note names what was not assessed. |
| **Ready with notes** | Nothing blocks the close. Open items exist; each has a next step, each amount is below the floor, and together they are below twice the floor. Open items with no amount (a Likely reason, a question about a balance that did not move) do not count towards that total. |
| **Not yet** | Anything blocks the close. |
| **Limited read** | One trial balance only, or a summary-level file. List what was tested, what was not, and what to provide for a full verdict. Never Ready to close. |

The verdict sentence says what it rests on: "Ready with notes: nothing in
the six dimensions blocks the close; tax and payroll were not assessed
because no VAT workings were given."
