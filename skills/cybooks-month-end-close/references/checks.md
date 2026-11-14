# The check catalogue

Every check has a stable code. A report always shows the code, so this
month's report can be compared with last month's, and a report made from
files lines up with one made by Cybooks.

## How to read a check

Each check has a head line and three parts.

- **Head line:** grade · severity · depths it runs in · the standard it
  rests on.
  - *Worked out* checks compare figures and may say Passed or Needs a look.
    *Scored* checks weigh likelihood and may only say Looks right or Worth a
    look.
  - Depths: **quick**, **month end**, **year end**.
- **Cybooks checks:** what Cybooks tests on the live books. Connected, this
  is what the result means.
- **From files:** the nearest test you can run from exports, with code.
  It is an equivalent, not the same test: say so in the report. "Cybooks
  only" means the check reads links between records that an export does not
  carry; from files the answer is Could not be checked.
- **Cannot see:** what the check cannot tell, even when it passes. Carry
  the relevant ones into the report.

Outcomes that are not a pass or a finding:

- **Not relevant:** the subject does not exist in the business (no
  employees, no stock, no EU sales). Give the reason.
- **Could not be checked:** an input is missing, or the records changed
  after the period end in a way that makes the figure unsafe. Give the input
  that would enable it.

Figures are compared to the cent. Where a check allows one cent of
difference it says so.

## 1. Bank and cash

### CB-BNK-01 · Every bank line is matched to a record
Worked out · high · quick, month end, year end · IAS 7.45

- **Cybooks checks:** every statement line dated in the period, on a
  connected or online bank account, has a matched booking. One direction
  only: it starts from the bank lines. The amount is the total of the
  unmatched lines. Could not be checked when an account has no lines in the
  period.
- **From files:** bank statement against the bank account's ledger. List
  statement lines with no ledger posting. Also list ledger postings with no
  statement line and say this second list is your own addition.
- **Cannot see:** a matched record may still name the wrong counterparty or
  purpose.

### CB-BNK-02 · Matched bookings do not exceed the statement line
Worked out · medium · quick, month end, year end · IAS 7.45

- **Cybooks checks:** the bookings matched to a bank line do not add up to
  more than the line, by more than one cent. Only over-matching is caught.
- **From files:** Cybooks only. Nearest equivalent, labelled as such: the
  ledger balance of each bank account equals the statement's closing
  balance plus or minus the listed unmatched items.
- **Cannot see:** whether each partial booking is the right one.

### CB-BNK-03 · No duplicate active transfer bookings
Worked out · low · quick, month end, year end · IAS 7.45

- **Cybooks checks:** no bank line is booked twice as the same side of a
  transfer between own accounts.
- **From files:** Cybooks only.
- **Cannot see:** two different bank lines that are really one payment.

### CB-BNK-04 · Transfers between your accounts pair up
Worked out · medium · month end, year end · IAS 7.45

- **Cybooks checks:** every transfer with a side in the period has exactly
  two sides, each on its own bank line, each equal to its line to the cent,
  in opposite directions, pointing at each other. A transfer where one side
  is a placeholder and the other is real is a finding. Both sides
  placeholders: Could not be checked. The two sides need not be the same
  amount (currencies differ).
- **From files:** ledgers of all own accounts. For each transfer out, find
  the transfer in. List those with no counterpart. A transfer account that
  does not net to zero is the same finding; say this is an equivalent.
- **Cannot see:** a transfer to an account that is not in the books.

### CB-BNK-05 · Foreign currency accounts use the dated closing rate
Worked out · medium · month end, year end · IAS 21.23(a)

- **Cybooks checks:** for each foreign currency account, the ledger balance
  at the period end equals the account's own-currency balance times the
  reference rate of exactly that date. Books kept in euro only. No rate for
  that date: Could not be checked, never a nearby rate.
- **From files:** the foreign currency balance, the base currency balance
  and the closing rate of the period end. Balance times rate equals the
  base figure. Name the rate and its source.
- **Cannot see:** whether the foreign currency balance itself agrees with
  the bank.

### CB-BNK-06 · No negative balances are presented as cash
Worked out · low · month end, year end · IAS 7.8

- **Cybooks checks:** no connected or online bank account has a credit
  balance in the ledger at the period end. Cash-in-hand accounts are not
  covered.
- **From files:** trial balance. A bank account in credit is an overdraft
  and belongs with liabilities, or it is an error.
- **Cannot see:** the bank's overdraft terms.

## 2. Money in

### CB-AR-01 · The receivables ledger ties to your open invoices
Worked out · high · month end, year end · IAS 1.54(h)

- **Cybooks checks:** the receivables control account equals the total
  still owed on open invoices dated up to the period end, within one cent,
  in the books' currency. Could not be checked when an invoice or a
  control-account entry of the period was changed or reversed after it, or
  a foreign currency invoice has no rate.
- **From files:** aged receivables total against the receivables control
  account in the trial balance, same date.
- **Cannot see:** whether each balance will be paid.

### CB-AR-02 · No credit balances hiding in receivables
Worked out · low · month end, year end · IAS 1.32 with IFRS 15.106

- **Cybooks checks:** no single invoice carries a credit balance on the
  receivables control account. It works per invoice, not per customer.
  Could not be checked when the control account holds entries that belong
  to no invoice (a manual journal, an unallocated receipt).
- **From files:** aged receivables. List negative lines per invoice, and
  customers whose total is negative. Each needs a refund, an allocation, or
  to be shown as a liability.
- **Cannot see:** a balance assigned to the wrong customer.

### CB-AR-03 · Voided and cancelled documents are out of outstanding
Worked out · medium · month end, year end · IFRS 15

- **Cybooks checks:** no voided or cancelled invoice dated up to the period
  end still has its original posting in effect.
- **From files:** list of voided invoices against the aged receivables and
  the ledger. None may still be outstanding or still be in income.
- **Cannot see:** whether a document should have been voided.

### CB-AR-04 · Invoice numbering runs without gaps
Worked out · medium · month end, year end · Cyprus VAT Law

- **Cybooks checks:** between the lowest and the highest number issued in
  the period, per prefix, no number is missing. A number counts as present
  if it exists at any date. Duplicates are not part of this check. Imported
  or custom numbers that do not follow the numbering format: Could not be
  checked.
- **From files:** invoice list. Use the number the customer sees, not the
  system's internal booking number. Invoices only: a credit note that
  reuses an order number is not an invoice. Sort by number within each
  prefix and list the gaps between the lowest and highest issued in the
  period. A number counts as present if it appears anywhere in the files.
- **Cannot see:** numbering formats it cannot put in order.

### CB-AR-05 · Old unpaid invoices are flagged for a provision decision
Scored · medium · month end, year end · IFRS 9

- **Cybooks checks:** open invoices 90 days or more past their due date at
  the period end. Invoices with no due date are left out. The amount is the
  unpaid total.
- **From files:** aged receivables with due dates. Same 90 days.
- **Cannot see:** what the customer has said about paying.

### CB-AR-06 · Each invoice's category fits its context
Scored · medium · month end, year end · IFRS 15

- **Cybooks checks:** an invoice line in the period on an income account
  other than the one that customer is most often invoiced on. A customer
  needs at least three earlier lines to have a usual account. No customer
  with that history: Could not be checked.
- **From files:** invoice lines with income accounts, including earlier
  periods for the baseline. Same rule. A tie between two accounts means the
  customer has no usual account; leave lines of zero out.
- **Cannot see:** a category that was always wrong looks consistent. With
  one income account for all sales the test says nothing.

## 3. Money out

### CB-AP-01 · The payables ledger ties to your open bills
Worked out · high · month end, year end · IAS 1.54(h)

- **Cybooks checks:** the payables control account equals the total still
  owed on open bills dated up to the period end, within one cent. Same
  Could not be checked cases as CB-AR-01.
- **From files:** aged payables total against the payables control account,
  same date.
- **Cannot see:** a supplier obligation that was never recorded.

### CB-AP-02 · No debit balances hiding in payables
Worked out · low · month end, year end · IAS 1

- **Cybooks checks:** no single bill carries a debit balance on the
  payables control account. Per bill, not per supplier. Could not be
  checked when the control account holds entries that belong to no bill.
- **From files:** aged payables. List negative lines per bill, and
  suppliers whose total is negative: a prepayment or a refund due.
- **Cannot see:** a balance assigned to the wrong supplier.

### CB-AP-03 · Likely duplicate bills surfaced
Scored · medium · month end, year end · IAS 1

- **Cybooks checks:** two bills in the period from the same supplier, in
  the same currency, for the same amount, 30 days or less apart. A matching
  bill number strengthens the reason; a matching number alone is not a
  finding.
- **From files:** bill list. Same rule. Bills only: leave credit notes out.
  A pair that straddles the period's first day goes under "Also noticed".
- **Cannot see:** a real repeat charge of the same amount looks the same.

### CB-AP-04 · Card and bank spend without a receipt
Worked out · medium · month end, year end · VAT Law 95(I)/2000 s.20 and the six-year records duty

- **Cybooks checks:** a matched, categorised payment out of a bank or card
  account in the period with no document attached, where it does not pay a
  bill that has one and is not a transfer. Bank and card fees are left out.
- **From files:** a spend list that says whether a document is attached.
  Without that column: Could not be checked.
- **Cannot see:** whether an attached file is readable or supports the
  whole spend.

### CB-AP-05 · Each bill's category fits its vendor and context
Scored · medium · month end, year end · IAS 1

- **Cybooks checks:** a bill line whose account differs from the category
  people confirmed for that supplier before, where Cybooks is confident of
  that category.
- **From files:** Cybooks only: the confirmed categories are not in an
  export. Nearest equivalent, labelled as such: a supplier's line on an
  account other than the one it is most often booked to, given at least
  three earlier lines. A tie means no usual account; leave lines of zero
  out.
- **Cannot see:** a supplier that genuinely sells across categories.

### CB-AP-06 · Equipment-shaped spend is not sitting in expenses
Scored · medium · month end, year end · IAS 16

- **Cybooks checks:** a bill line of 1,000 or more on an expense account,
  with no fixed asset record, whose description or account names equipment:
  words such as laptop, computer, server, monitor, printer, furniture,
  machinery, vehicle, camera. Bill lines only. Software is not detected.
- **From files:** bill or expense lines. Same amount and the same kind of
  words.
- **Cannot see:** how long the thing will be used, which decides whether it
  is an asset.

### CB-AP-07 · Recurring costs that skipped a month
Worked out · low · month end, year end · IAS 1

- **Cybooks checks:** over the six months ending with the period, a
  supplier billed in at least three months, with at least two pairs of
  months back to back, has a month with no bill. Every missing month from
  its first billed month onward counts, not only the last.
- **From files:** bills by supplier and month for those six months. Same
  rule.
- **Cannot see:** a seasonal or paused supplier looks like a missing month.

### CB-AP-08 · Inbox documents that never became a bill
Worked out · medium · month end, year end · IAS 1

- **Cybooks checks:** a supplier invoice in the document inbox, matched to
  a supplier and dated in the period, that never became a bill.
- **From files:** Cybooks only.
- **Cannot see:** documents that never reached the inbox.

### CB-AP-09 · Expense claims waiting too long for approval or payout
Worked out · low · month end, year end · IAS 1

- **Cybooks checks:** at the period end, a claim submitted more than 30
  days ago and not yet approved, or approved more than 30 days ago and not
  yet paid.
- **From files:** expense claim list with dates and status. Same 30 days.
- **Cannot see:** spend that was never filed as a claim.

## 4. People

Not relevant when the business runs no payroll. Payroll figures are
private: if the person asking is not meant to see pay, report the check,
its answer and its count, and say the amounts are withheld.

### CB-PPL-01 · Payroll is booked and internally consistent
Worked out · medium · month end, year end · IAS 19

- **Cybooks checks:** each approved pay run ending in the period has
  exactly one posting, dated the run's end date, that balances, and whose
  salary cost equals the run's gross to the cent.
- **From files:** payroll summary against the payroll journal. Gross in the
  summary equals the salary cost posted; the journal balances; its date is
  the period's.
- **Cannot see:** whether the tax rates and each person's eligibility are
  right.

### CB-PPL-02 · PAYE, social insurance and GeSY payables tie to payslips
Worked out · medium · month end, year end · IAS 19

- **Cybooks checks:** in each run's posting, the amount credited to each
  liability (income tax, employee and employer social insurance, employee
  and employer GeSY) equals the payslips' total, to the cent.
- **From files:** payroll summary against the liability lines of the
  payroll journal. Comparing with the liability balances in the trial
  balance is a weaker test (they include earlier months); say which you
  ran.
- **Cannot see:** whether each employee's tax declaration is right.

### CB-PPL-03 · Payments to the authorities are matched
Worked out · medium · month end, year end · Social Insurance Law 59(I)/2010 and the Assessment and Collection of Taxes Law

- **Cybooks checks:** this check never says Passed and never says Needs a
  look. If any payroll liability has a balance at the period end, it
  answers Could not be checked and lists the balances for a person to
  agree with the payments. All zero: Not relevant.
- **From files:** liability account ledgers. List each open balance, the
  period's own charge, and what is older. Leave the judgement to the
  person. Count it as Could not be checked.
- **Cannot see:** which payment settles which month.

### CB-PPL-04 · Untaken leave is counted
Worked out · low · month end, year end · IAS 19

- **Cybooks checks:** the liability for leave that is paid out on leaving
  (days left times the daily rate, plus the employer's contributions) is
  booked at the period end as one accrual of exactly that amount. Not
  booked, or booked at another amount: Needs a look. No such leave: Not
  relevant.
- **From files:** leave balances and pay rates, and the accrual in the
  ledger. Without a leave report: Could not be checked.
- **Cannot see:** missing salary, schedule or leave policy data.

### CB-PPL-05 · Payroll accounts are mapped correctly
Worked out · low · month end, year end · IAS 19.11 with IAS 1.69

- **Cybooks checks:** the payroll setup, not the journal: each payroll
  account exists, is active, is of the right kind (cost or liability) and
  carries no VAT. A custom mapping is Could not be checked: an accountant
  has to confirm it.
- **From files:** the payroll journal's accounts against the chart. Salary
  cost on expense accounts, amounts owed on liability accounts.
- **Cannot see:** the intent behind a custom mapping.

## 5. Assets and stock

### CB-AST-01 · Depreciation booked for every asset in use
Worked out · medium · month end, year end · IAS 16

- **Cybooks checks:** every asset in use has a depreciation charge for each
  month of the period, and each charge reached the ledger.
- **From files:** fixed asset register against the depreciation postings of
  the period.
- **Cannot see:** whether the useful life is right. A wrong life still
  produces a charge every month.

### CB-AST-02 · Disposals carry their gain or loss
Worked out · medium · month end, year end · IAS 16

- **Cybooks checks:** for each disposal in the period, the gain or loss
  recorded on the asset is the amount posted to the gain or loss account.
  It does not work the gain or loss out again.
- **From files:** disposals in the period. Recompute proceeds less book
  value yourself and compare with the posting; say this goes further than
  the Cybooks check.
- **Cannot see:** whether the sale price was the right one.

### CB-AST-03 · IP Box percentages are never assumed
Worked out · low · year end · Cyprus IP Box

- **Cybooks checks:** where the IP Box is used, no ledger line claims a
  percentage without a category, or a percentage its source document never
  set. A category with no percentage decided: Could not be checked. It is
  never read as a full claim.
- **From files:** the IP Box schedule. Every qualifying line has a
  percentage a person chose. A blank is Could not be checked.
- **Cannot see:** whether a decided percentage is the right one.

### CB-STK-01 · Your stock records match your stock accounts
Worked out · high · month end, year end · IAS 2.36

- **Cybooks checks:** for each stock account, the value of all stock
  movements up to the period end equals the ledger balance, to the cent.
- **From files:** stock valuation report against the stock accounts in the
  trial balance.
- **Cannot see:** what is on the shelves. Lost or unrecorded stock matches
  as long as both sides agree.

### CB-STK-02 · No product is carried above what it will sell for
Worked out · medium · month end, year end · IAS 2.9

- **Cybooks checks:** no product in stock is valued above its saved selling
  price times the quantity held. Costs to sell are not deducted. No product
  with a price: Could not be checked.
- **From files:** stock list with cost and selling price. Same comparison.
- **Cannot see:** an out-of-date price, and costs to sell.

## 6. VAT, VIES and OSS

Written for Cyprus. For another country keep the shape (the tax account
clears to the return, reverse charge pairs, cross-border sales are
evidenced). The Cyprus-only parts are the return boxes in CB-VAT-01 and the
due dates in CB-VAT-06; SKILL.md says when a local rule may stand in for
them. "Filed" means the return as filed; if all you have is the ledger's
own posting of the return, say so.

### CB-VAT-01 · Every return box re-derived independently and tied to the filed value
Worked out · high · month end, year end · Cyprus VAT Law

- **Cybooks checks:** for each VAT return that overlaps the period, open or
  filed, every box is rebuilt from the ledger lines and compared, to the
  cent, with the return as Cybooks prepares it, with the filed figures, and
  with the file sent to the tax portal.
- **From files:** ledger lines with tax codes and the return. Build each
  box from the lines yourself, then compare with the workings and with what
  was filed. A box copied from the workings proves nothing. Where a return
  picks up entries recorded late, a month's lines will not equal that
  month's return: compare the returns and the lines added up over the year
  to date, and report the difference that is left.
- **Cannot see:** whether a supply was given the right VAT treatment.

### CB-VAT-02 · The VAT account ties to filed returns
Worked out · medium · month end, year end · Cyprus VAT Law

- **Cybooks checks:** for each filed return, the VAT control account clears
  to zero over the return's dates, the filing entry moves the net to the
  VAT payable account in the right direction, and the VAT payable account
  equals the VAT still unpaid. The open period's balance is not tested.
- **From files:** VAT control and VAT payable accounts against the returns
  filed and the payments made. Some systems keep input VAT, output VAT and
  the return on separate accounts that clear once a year: take all the VAT
  accounts together, less the open period's own VAT, and report what is
  left.
- **Cannot see:** each box, and the tax treatment underneath.

### CB-VAT-03 · Reverse charge entries pair correctly across boxes
Worked out · medium · month end, year end · Cyprus VAT Law

- **Cybooks checks:** for each EU purchase, EU acquisition and reverse
  charge document, the output VAT and the input VAT each equal the net
  amount times the rate, to the cent. Both sides must be right, not only
  equal to each other.
- **From files:** reverse charge lines with net, rate, output VAT and input
  VAT. Same test, in the books' currency. Allow one cent a document where
  a foreign currency line was converted.
- **Cannot see:** a wrong goods or services classification.

### CB-VAT-04 · No unresolved late-recorded VAT transactions
Worked out · medium · month end, year end · Cyprus VAT Law

- **Cybooks checks:** an entry that touches the VAT control account, is
  dated inside a filed return's period, was recorded after that return was
  filed, and has not been dealt with in the next return.
- **From files:** journal detail with the date each entry was recorded, and
  the filing dates. Entries on VAT accounts dated in a filed period and
  recorded after it was filed.
- **Cannot see:** a transaction with no VAT line.

### CB-VAT-05 · Each sale's VAT rate fits what was sold
Scored · medium · month end, year end · Cyprus VAT Law

- **Cybooks checks:** an invoice line whose tax rule differs from the one
  most often used on that income account. An account needs at least five
  earlier lines to have a usual rule. Credit notes are not included.
- **From files:** sales lines with tax codes, including earlier periods.
  Same rule.
- **Cannot see:** what was actually supplied. Only a change in habit shows.
  Where one income account takes all sales and the rate follows the
  customer's country, the test flags many correct lines; say so.

### CB-VAT-06 · No VAT filing is overdue
Worked out · high · quick, month end, year end · Cyprus VAT Law

- **Cybooks checks:** no VAT return had its due date before the period end
  without being filed by then. A return due on the period's last day is
  not overdue. VAT returns only: the VIES statement and the OSS return are
  not part of this check.
- **From files:** the filing history against the due dates below. The
  ledger's own posting of a return is not proof that it was filed; say so
  if that is all you have.
- **Cannot see:** a return period that was never set up.

Cyprus due dates, as Cybooks holds them. Confirm against the Tax
Department's current calendar before relying on one: the Commissioner
often extends a deadline, and the date on a VAT registration certificate
takes precedence.

| Filing | Due |
|---|---|
| VAT return | The 10th day of the second month after the VAT period ends (a quarter ending 31 March is due 10 May) |
| VIES statement | The 15th of the month after the month reported |
| OSS return | The last day of the month after the calendar quarter |
| PAYE, social insurance, GeSY | The last day of the month after the pay month |

The Tax Department moves a VAT or VIES date that falls on a weekend or
holiday to the next working day. The OSS date does not move.

### CB-VIE-01 · Every EU customer VAT ID checked live against VIES
Worked out · low · month end, year end · Council Regulation (EU) 904/2010 Art. 31

- **Cybooks checks:** every customer with an EU address outside Cyprus on
  an entry in the period has a VAT ID that VIES confirms as valid today. A
  missing ID is a finding too, so consumers show up here. VIES down, slow
  or rate limited: Could not be checked.
- **From files:** a VIES result for each such customer, with its date.
  Never assume an ID is valid. Without results: Could not be checked.
- **Cannot see:** that the customer received a supply. VIES confirms
  registration only.

### CB-VIE-02 · Every zero-rated EU sale is backed by a valid VAT ID
Worked out · high · month end, year end · EU VAT Directive

- **Cybooks checks:** every income line taxed as an EU sale of goods or
  services, to a customer billed in another EU country, has a VAT ID that
  VIES confirms as valid.
- **From files:** zero-rated EU sales against the customer VAT IDs and
  their VIES results.
- **Cannot see:** transport, the place of supply, or business use.

### CB-VIE-03 · The VIES return ties to your EU B2B invoices
Worked out · medium · month end, year end · EU VAT Directive

- **Cybooks checks:** for each VIES statement in the period, goods,
  triangular sales and services are rebuilt from the EU sales lines, in
  whole euro, and compared with the statement in total and per customer. EU
  sales with no statement covering them are a finding.
- **From files:** VIES statement against the EU business invoices of the
  same period, per customer.
- **Cannot see:** dispatch evidence or the place of supply.

### CB-OSS-01 · EU consumer sales sit on the right OSS return
Worked out · medium · month end, year end · EU VAT Directive

- **Cybooks checks:** per calendar quarter, a sale to another EU country
  carries OSS tax when the customer has no valid VAT ID, and does not when
  it has one; and the quarter's OSS return exists and equals those sales
  line for line.
- **From files:** cross-border consumer sales by country and quarter
  against the OSS return.
- **Cannot see:** evidence of where the customer is, beyond the recorded
  address.

## 7. The ledger itself

### CB-LDG-01 · Your books balance to the cent
Worked out · high · quick, month end, year end · Companies Law Cap. 113 s.141 and s.142, IAS 1.15

- **Cybooks checks:** total debits equal total credits across every entry
  from the start of the books to the period end.
- **From files:** trial balance. Total debits equal total credits.
- **Cannot see:** a balanced entry on the wrong account or in the wrong
  period.

### CB-LDG-02 · The period opens where the last one closed
Worked out · medium · quick, month end, year end · ISA 510.6 with IAS 1.36

- **Cybooks checks:** the financial years join up with no gap between one
  year's last day and the next year's first, and every entry in the period
  sits inside its own financial year. It does not compare closing balances
  with opening balances.
- **From files:** the prior period's closing trial balance against this
  period's opening balances. This is a different and stronger test than
  the Cybooks one; say so.
- **Cannot see:** whether the opening balances are right.

### CB-LDG-03 · No unbalanced or orphaned journal entries
Worked out · medium · quick, month end, year end · Cap. 113 s.141 with IAS 1.15

- **Cybooks checks:** every entry up to the period end has at least two
  lines and balances to the cent. A one-line entry is a finding even when
  it balances.
- **From files:** journal detail. Sum debits and credits per entry; list
  entries that do not balance or have one line.
- **Cannot see:** a balanced entry that is a duplicate or sits on the wrong
  document.

### CB-LDG-04 · Holding and suspense accounts are at zero
Worked out · medium · quick, month end, year end · IAS 1.54

- **Cybooks checks:** every account named holding or suspense has a zero
  balance at the period end. Withholding accounts are left out.
- **From files:** trial balance. Any holding or suspense account with a
  balance. Clearing and "ask my accountant" accounts are worth listing too;
  say that is your own addition.
- **Cannot see:** a holding account that is not named as one.

### CB-LDG-05 · No unexplained entries were backdated
Worked out · high · quick, month end, year end · IAS 8.41-42 with IAS 10.8

- **Cybooks checks:** an entry recorded during the period, dated on or
  before the date the books were closed up to at that moment, with no
  recorded override. Closed means the period close, a filed tax period or a
  hard lock. No close on record: Not relevant. A close history that cannot
  be read reliably: Could not be checked.
- **From files:** journal detail with the recorded date, and the date each
  earlier period was closed. Entries dated in a closed period and recorded
  after its close.
- **Cannot see:** entries recorded before the current close date was set.

### CB-LDG-06 · Payment processor clearing accounts net out
Worked out · medium · month end, year end · IAS 1.54(h) with IAS 1.57

- **Cybooks checks:** for each connected Stripe or PayPal account, the
  ledger balance at the period end equals its opening balance plus the
  matched money in less the matched money out, to the cent. A foreign
  currency processor account: Could not be checked.
- **From files:** the processor's own balance report at the period end
  against the processor account in the trial balance.
- **Cannot see:** a processor account that is not connected.

### CB-LDG-07 · No entries left behind by an undone bank match
Worked out · high · quick, month end, year end · Cap. 113 s.141 with IAS 1.15

- **Cybooks checks:** no entry is still in effect whose bank match was
  undone, leaving a payment in the ledger with nothing behind it.
- **From files:** Cybooks only.
- **Cannot see:** a payment recorded twice while its match is in place, or
  one never matched to a bank line.

### CB-LDG-08 · Every bill still counts in your reports
Worked out · high · quick, month end, year end · Cap. 113 s.141 with IAS 1.15

- **Cybooks checks:** no bill that is open or paid has had every one of its
  postings reversed, so that the books cancel a bill that still stands.
- **From files:** Cybooks only.
- **Cannot see:** a bill on the wrong category or for the wrong amount, and
  sales invoices.

### CB-LDG-09 · Every voided and restored bill nets to what it says
Worked out · high · quick, month end, year end · Cap. 113 s.141 with IAS 1.15

- **Cybooks checks:** for a bill that was voided at least once, its
  postings and their reversals net to its status: nothing when it is
  voided, its full posting when it is not.
- **From files:** Cybooks only.
- **Cannot see:** bills never voided, and sales invoices, credit notes and
  vendor credits.

## 8. Related parties and year end

### CB-REL-01 · Related party transactions are tagged for disclosure
Worked out · medium · month end, year end · IAS 24

- **Cybooks checks:** every bank line booked to a director's or
  shareholder's account in the period names the related party, and every
  employee marked as a director is recorded as a related party.
- **From files:** ledgers of the director and shareholder accounts. Each
  line names the person. No lines in the period: Not relevant. A list of
  directors, shareholders and their companies checked against the whole
  ledger goes further: report it under "Also noticed".
- **Cannot see:** a related party trading through an ordinary customer or
  supplier account.

### CB-REL-02 · Director loans and balances surfaced
Worked out · medium · year end · IAS 24

- **Cybooks checks:** every account held with a related party that has a
  balance at the period end is listed. Any balance is reported, because it
  has to be disclosed; this is a list, not a judgement.
- **From files:** director and shareholder accounts in the trial balance.
- **Cannot see:** the terms of the loan.

### CB-YE-01 · Comparatives tie to the prior year close
Worked out · medium · year end · IAS 1

- **Cybooks checks:** no entry dated in the prior financial year was
  recorded after the period under review began. Such an entry moved last
  year's figures after the fact.
- **From files:** journal detail with recorded dates. Same test. With the
  prior year's signed accounts, also compare them with the prior year
  figures now in the books; say that goes further.
- **Cannot see:** anything changed before the period began.

### CB-YE-02 · Retained earnings roll forward cleanly
Worked out · medium · year end · IAS 1

- **Cybooks checks:** no posting in the period goes straight to retained
  earnings, other than an opening balance or a dividend. Retained earnings
  are worked out from the profit and loss, so anything else distorts them.
- **From files:** the retained earnings ledger for the period. Same test.
- **Cannot see:** an error in the profit and loss carries straight through.

### CB-YE-03 · Provisional tax paid against the estimate
Worked out · medium · year end · IAS 12

- **Cybooks checks:** for the tax year, every instalment marked paid has
  its entry in the ledger, no instalment past its due date is underpaid,
  and the total paid equals what the ledger shows as tax paid on account.
- **From files:** the provisional tax schedule against the payments in the
  ledger.
- **Cannot see:** whether the estimate itself is reasonable.

### CB-YE-04 · Going concern indicators reported, not judged
Worked out · low · year end · IAS 1

- **Cybooks checks:** nothing is tested. Six ratios are reported for the
  period and for the same dates a year earlier, with the change: current
  ratio, debt ratio, current liabilities to net worth, debt to equity,
  working capital to total assets, fixed assets to net worth.
- **From files:** the same six ratios from the two balance sheets. Report
  the figures. Form no opinion.
- **Cannot see:** funding, contracts and intentions.

### CB-YE-05 · Scope limitations declared in the findings pack
Worked out · low · year end · IAS 1

- **Cybooks checks:** states four limitations every time (whether things
  exist, rights and obligations, events after the period, going concern),
  and adds a fifth as a finding when the review covers less than the
  financial year.
- **From files:** the report itself. It states the same limitations, and
  says so when the files cover less than the year.
- **Cannot see:** a limitation nobody has thought of.

## What no check can see

Say this in every report, in these words or close to them:

- Anything not recorded in the books.
- What the documents actually say.
- Whether things exist: the stock, the equipment, the customer.
- What happened after the period.
- Whether the business can keep going.
