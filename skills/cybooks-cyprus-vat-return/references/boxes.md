# The VAT return, box by box

The Cyprus VAT return has thirteen boxes, numbered 1 to 11B. This file says
what belongs in each, which tests the script runs on the thirteen figures,
and which tests you run on the lines behind them when the person gives you
the lines. All figures are in euros.

**Source.** Tax Department, Republic of Cyprus, "VAT Guide: Fill in your VAT
Return", Taxpayers' Service and Education Unit, 6 August 2024. Text in
quotation marks is the guide's own wording; p.4 is the guide's page 4. The
guide says of itself that it "does not replace the Legislation". The guide
is not bundled with this skill. If the person has a newer edition, theirs
wins: say which edition you used.

**[Practice]** marks a rule the guide does not state: common practice or
the law behind it. Say so when a finding rests on one, and word the finding
as a question for the person or their accountant.

## 1. Filing basics

- **Due date:** "no later than the tenth day after the end of the month
  that follows the end of the period" (p.3). A quarter ending 30 June is
  due 10 August; one ending 30 September, 10 November. The script prints
  the date and whether it has passed. The Tax Department sometimes extends
  a date: tell the person to confirm it on the portal. When the date has
  passed, say so at the top of the report; the guide says nothing about
  penalties.
- **Where:** "only electronically via TAX FOR ALL (TFA)" (p.3).
- **Every box is completed.** "All boxes in the VAT Return, numbered 1-11B,
  should be completed" (p.4), with 0 where nothing applies (p.3).
- **Boxes 1 to 5** are VAT amounts with two decimals, a decimal comma, no
  thousands separator and a minus sign for a negative (p.3).
- **Boxes 6 to 11B** are values excluding VAT, rounded to the nearest euro,
  no thousands separator (p.3).
- **Payment** uses the payment code printed on that return (p.12).
- **A negative box 5** is a credit: carried forward, or claimed as a refund
  with Form 4B when the return is submitted (p.12).
- **The monthly VIES statement** is due by the 15th of the following month.
  A sale goes on the statement of the month of its tax point: for a service
  normally the invoice date; for goods the invoice date, or the 15th of the
  month after dispatch if that is earlier. **[Practice]**: the guide gives
  no VIES rule.

## 2. What belongs in each box

| Box | The guide's definition | Belongs | Does not belong, or watch | Page |
|---|---|---|---|---|
| **1** | "VAT due in the period, on sales and other outputs" | VAT on sales in Cyprus; distance sales; commissions received; the reverse charge on **services received from abroad, EU and non-EU**; reverse charge under Articles 11 and 11A to 11D; VAT on self-billed invoices issued by customers; sales of assets; private use of goods; gifts over 17 euros; VAT on a bad debt that was later paid; VAT on the value of goods or services taken in exchange | Less the VAT on **credit notes you issued**. Less VAT refunded to visitors from outside the EU. Not the VAT on goods bought from the EU (box 2). Not an assessment by the Tax Department | 4 to 5 |
| **2** | "VAT due on all goods and related cost, bought from VAT-registered suppliers in EU" | Goods, and the costs the supplier charges with them (transport, packing, insurance) | **Never services.** Tax point: the supplier's invoice date, or the 15th of the month after dispatch if earlier | 5 |
| **3** | "Total VAT due (sum of boxes 1 and 2)" | Box 1 + box 2 | | 3, 5 |
| **4** | "total amount of deductible VAT charged on your business purchases" | VAT on proper VAT invoices; import VAT; the VAT of box 2, with an invoice issued under the law of the other Member State; reverse charge VAT on services; bad debt relief; self-billed invoices you issued | No proper VAT invoice, no claim. Not private use, not business entertainment, not goods bought under the used goods scheme. Less the VAT on **credit notes from suppliers**. Not a payment to or from the Tax Department. Limited where the business is partly exempt | 6 |
| **5** | "VAT payable or refundable" | Box 3 minus box 4. Positive is payable, negative is a credit | See section 6 on the sign | 3, 7 |
| **6** | "Total value of sales and all other output excluding VAT" | All sales: standard, reduced, zero rated, exempt; the amounts of boxes 8A, 8B, 9 and 10; **the value of services received under the reverse charge**; triangular sales | Money the owner put into the business, loans, dividends, insurance claims | 7 to 8 |
| **7** | "Total value of purchases and all other inputs (excluding VAT)" | All purchases, exempt ones included; goods and services from the EU; imports; **services from outside the EU**; triangular purchases | Wages and salaries; contributions to funds; gifts of money; interest, dividends and taxes; "Fees and taxes"; anything not bought for the business. Never the gross amount | 8 |
| **8A** | "Total value, excluding VAT, of intra community supplies of goods" | Goods sent to a VAT-registered customer in another Member State, with related freight and insurance; goods sent for installation or assembly there | Also in box 6. Reported on the monthly VIES | 8 to 9 |
| **8B** | "Total value of services provided in other Member States" | Services to business customers in the EU "for which the VAT is payable by the recipient" | Also in box 6. Reported on the monthly VIES. Services to EU consumers are not 8B | 9 |
| **9** | "Total value of zero rated output transactions (0%)", other than 8A and 8B | Zero rated supplies in Cyprus, exports of goods included | Also in box 6 | 9 |
| **10** | Sales "outside the scope" of Cyprus VAT "with the right of deduction", other than 8B | Supplies made outside Cyprus that would be taxable in Cyprus; the sales value of triangular transactions (p.11, question 1); sales under the "mini one stop shop", today the One Stop Shop **[Practice]** | Also in box 6 | 9, 11 |
| **11A** | "Total value of goods and services acquisitions and related cost (excl. VAT) from other EU member states" | Goods from VAT-registered EU suppliers, freight in the price included; goods installed or assembled in Cyprus. The heading names services, the text covers goods only | Also in box 7. Its VAT is in box 2 and box 4 | 9 to 10 |
| **11B** | "Total Value of Services Received from other Member States" | Services from VAT-registered suppliers **in the EU** | Also in boxes 6 and 7. Its VAT is in box 1 and box 4. **Suppliers outside the EU are not 11B** | 10 |

## 3. Tests on the thirteen figures

`scripts/vat_return.py check` runs these, always all of them, in this
order. A *worked out* test compares figures and says Passed or Needs a
look. A *scored* test weighs likelihood and says Looks right or Worth a
look; it never says Passed. A test without its input says Could not be
checked. Figures are compared to the cent; where a test allows a
difference, the output states it.

| Code | Test | Grade | Stops the file |
|---|---|---|---|
| VR-01 | Every box has a figure | Worked out | Yes |
| VR-02 | Boxes 1 to 5 are in euros and cents | Worked out | Yes |
| VR-03 | Boxes 6 to 11B are in whole euros | Worked out | Yes |
| VR-04 | Box 3 is box 1 plus box 2 | Worked out | Yes |
| VR-05 | Box 5 is box 3 minus box 4 | Worked out | Yes |
| VR-06 | Box 6 covers boxes 8A, 8B, 9, 10 and 11B | Worked out | Yes |
| VR-07 | Box 7 covers boxes 11A and 11B | Worked out | Yes |
| VR-08 | Box 2 has acquisitions behind it in box 11A | Worked out | Yes |
| VR-09 | Box 2 against 19% of box 11A | Scored | Until a reason is written down |
| VR-10 | Box 8A against the goods on the period's VIES statements | Scored | Until a reason is written down. Also while the box is not nil and the tie could not be made |
| VR-11 | Box 8B against the services on the period's VIES statements | Scored | The same |
| VR-12 | Box 1 against 19% of box 11B | Scored | No |
| VR-13 | Box 4 covers the acquisition VAT of box 2 | Scored | No |
| VR-14 | The taxpayer number is a Cyprus VAT number | Worked out | Yes |
| VR-15 | The period is whole months | Scored | No |
| VR-16 | Every figure fits the form (ten digits) | Worked out | Yes |
| VR-17 | The file holds the figures that were tested | Worked out | Yes |

VR-17 belongs to the `xml` command: it reads the built file back. `check`
stops at VR-16.

What each one rests on:

- **VR-04, VR-05:** the definitions of boxes 3 and 5 (p.3). No difference
  is allowed, not one cent.
- **VR-06, VR-07:** box 6 includes boxes 8A, 8B, 9, 10 and 11B; box 7
  includes 11A and 11B (p.4). Each box is rounded to the euro on its own,
  so the boxes inside may exceed the box they sit in by the rounding: 50
  cents for the box and for each box inside it that holds a figure.
- **VR-08, VR-09:** box 2 is the VAT on the goods whose value is in 11A
  (p.5). At the standard rate they tie to within 50 cents. Goods at a
  reduced rate are the one ordinary reason for a gap: name the lines. The
  usual mistakes are a supplier credit note that reached box 11A but not
  boxes 2 and 4, and a service whose reverse charge VAT went to box 2.
- **VR-10, VR-11:** box 8A is the goods and box 8B the services reported
  on the monthly VIES statements (p.8 to 9). Goods are compared with
  goods and services with services, so a swap shows. Every month of the
  period is needed; a month without a statement is not taken for nil.
  While box 8A or 8B holds a figure and a month is missing, or its
  statement could not be built, the answer is Could not be checked and
  the return file waits: a sale that cannot go on VIES is not a sale for
  box 8A or 8B either. The person's written reason lets the return go
  ahead without the tie. Each VIES row is rounded to the euro, so the
  test allows 50 cents per row, and 50 cents for the box. Triangular sales have their own VIES column and the guide puts
  them in boxes 6 and 10, not 8A; where box 8A agrees only with the
  triangular column added, the test says so and asks.
- **VR-12:** the reverse charge on services received is output VAT in box 1
  (p.4). A weak test: box 1 also holds the VAT on sales, so it shows only
  a shortfall. It does not show reverse charge VAT that went to box 2;
  VR-09 and the line test VL-03 do.
- **VR-13:** acquisition VAT is also input VAT in box 4 for a business that
  deducts in full (p.6). Weak in the same way.

**Could not be checked from thirteen figures alone:** whether a figure is
right. The tests show that the boxes agree with each other and with the
VIES statements. Whether each invoice is in the right box needs the lines.

## 4. Tests on the lines

Run these with your own code when the person gives you the lines behind
the return: a VAT report by transaction, a sales and a purchase list, or
the transactions Cybooks returns. Each needs the columns named; without
them the answer is Could not be checked, with the column that would enable
it. Show all twelve in the report, with their codes.

The script knows nothing of the line tests, so they do not stop it. You
do: when a worked out line test needs a look, the figures are known to be
wrong, and `xml` is not run until the books are corrected and the figures
given again. A scored line test that is worth a look is a question: the
file may be built, and the question goes first under "Before you upload".

| Code | Test | Grade | Needs, per line |
|---|---|---|---|
| VL-01 | Each box equals the sum of its lines | Worked out | The box, net, VAT |
| VL-02 | Every line is dated in the period | Worked out | Document date |
| VL-03 | Reverse charge VAT on services is in box 1, never box 2 | Worked out | Goods or services; the box |
| VL-04 | Box 11B holds suppliers from the EU only | Worked out | Supplier VAT number or country |
| VL-05 | A service received under the reverse charge is in boxes 6 and 7 as well | Worked out | The boxes of the line |
| VL-06 | Reverse charge VAT is in box 1 and box 4 at the same amount | Scored | The VAT per box |
| VL-07 | Every 8A and 8B line has a customer VAT number from another Member State | Worked out | Customer VAT number |
| VL-08 | Box 4 holds no VAT without a supplier VAT number, and no foreign VAT | Scored | Supplier VAT number, VAT rate, country |
| VL-09 | A supplier credit note lowers every box its invoice raised | Worked out | Document type; the boxes |
| VL-10 | No document is counted twice | Scored | Supplier, document number, amount, date |
| VL-11 | Boxes 6 and 7 hold nothing the guide leaves out | Scored | Account name |
| VL-12 | Every box 9 line is an export or a zero rated sale in Cyprus | Scored | Customer country or VAT number |

How to read them:

- **VL-01.** A box of the return in whole euros differs from its lines by
  the rounding, and by no more.
- **VL-03.** The most common mistake on this return. Box 2 is goods from
  the EU. A service from abroad is box 1 (and 4, 6, 7; 11B if the supplier
  is in the EU).
- **VL-04.** Decide per invoice, from the entity that issued it and the VAT
  number printed on it, not from the brand. A number that starts with `EU`
  is a One Stop Shop registration of a business outside the EU: that
  supplier is not in the EU and not in 11B. A supplier can move from a
  US entity to an EU one in the middle of a period. **[Practice]**
- **VL-05, VL-06.** A purchase under the reverse charge is a purchase
  document with VAT in both box 1 and box 4. The amounts are equal for a
  business that deducts in full; lower in box 4 where deduction is
  restricted. Ask before calling it wrong.
- **VL-07.** A Greek number is often recorded with `GR`. The code on VIES
  is `EL`; the script writes it so and says so on the row. Tell the
  person, so the customer's record can be corrected.
- **VL-08.** Box 4 needs "a proper VAT invoice" (p.6). A 19% invoice whose
  record has no supplier VAT number is checked against the document, not
  dropped: records often lose a number the paper invoice prints. VAT of
  another Member State is never box 4; it is reclaimed from that state,
  or from the supplier when it was charged by mistake, and the reverse
  charge is then accounted for on the net. Cyprus VAT charged by a
  supplier outside Cyprus through the One Stop Shop is not deductible
  either. **[Practice]** Foreign VAT shows as a supplier from another
  Member State with VAT in box 4 and nothing in box 1 or box 2.
- **VL-09.** The supplier's credit note lowers box 4 (p.6) and box 7. For
  goods from the EU it also lowers boxes 2 and 11A; for a reverse charge
  service, boxes 1, 6 and 11B. An item is in every box it touches or in
  none. Where the credit note carries no VAT, the VAT it should have
  moved is the rate of its invoice on its net amount.
- **VL-10.** A reminder or a statement of account is not an invoice. US
  dates (04/06 read as 4 June) put one invoice in two quarters.
- **VL-11.** The guide leaves out of box 6: money the owner put in, loans,
  dividends, insurance claims (p.7 to 8). Out of box 7: wages and salaries,
  contributions to funds, interest, dividends, taxes, "Fees and taxes"
  (p.8). Read from account names, so it is a question.
- **VL-12.** Goods sold at 0% to a customer with no VAT number are box 9
  only when they left the EU. Ask for the export evidence. When the
  person has already said it was an export and that they hold the papers,
  that is enough for Looks right: quote them and say the papers were not
  seen. **[Practice]**

When a line test finds a mistake, say what the correction would do to each
box, as a guide for the person. The correction itself is made in their
books, and the figures are then given again.

## 5. Rules that trip people up

- **Services received from abroad:** box 1 and box 4 (the VAT), boxes 6 and
  7 (the value), and 11B only when the supplier is in the EU.
- **Goods from the EU:** boxes 2, 4, 7 and 11A. Not box 1.
- **Values are without VAT.** Box 7 filled from gross amounts is a common
  mistake.
- **Self-billing:** a credit note a customer issues on your behalf is your
  sale (p.4). Use the value before any foreign withholding tax; withholding
  tax is not VAT. **[Practice]** To a business in the EU it is 8B and VIES.
- **Your own credit notes** lower box 1 (p.5). A refund with no credit note
  does not. **[Practice]**
- **No invoice, still due.** The reverse charge on a service received is
  due in box 1 whether or not the invoice has arrived, but box 4 needs "a
  proper VAT invoice" (p.6). A foreign subscription with no invoice on
  file costs the VAT: quantify it and ask for the invoice before filing.
  **[Practice]**
- **Invoices in a director's or an employee's name:** no input VAT, and out
  of box 7 unless the company is the customer. **[Practice]**
- **Private items paid by the company:** in neither box 4 (p.6) nor box 7
  (p.8).
- **Exports of goods:** box 9 and box 6. **Services to businesses outside
  the EU:** box 10 and box 6. **[Practice]**
- **Digital services to EU consumers:** Cyprus VAT in box 1 below the
  EU-wide 10,000 euro threshold; above it, or once the One Stop Shop is
  chosen, the One Stop Shop return, with the value in boxes 10 and 6.
  **[Practice]**
- **Credit carried forward** from the period before is a balance on the VAT
  account, not input VAT. It is not added to box 4. **[Practice]**
- **A mistake in a return already filed** is not corrected by filing that
  period again. The guide's way is a correction in a later return, "subject
  to conditions": output VAT that was under or over declared goes into box
  1 (p.4), input VAT that was over claimed comes out of box 4 (p.6). The
  conditions are in the law, not in the guide: the person's accountant
  decides.

## 6. Where the guide is unclear

Say so when a finding touches one of these.

- **The sign of box 5.** Page 3 says only that the difference between
  boxes 3 and 4 equals box 5. The paragraph on box 5 (p.7) describes the
  subtraction the other way round. The Tax Department's own sample file
  settles it: box 3 below box 4 is written as a negative figure. So box 5
  is box 3 minus box 4, positive when VAT is payable.
- Boxes 6 to 11B: "Round the amounts to the nearest Euro", yet the guide's
  example shows "10000,00". The file writes whole euros followed by ",00".
- The heading of box 11A mentions services; the text and the questions
  cover goods only.
- The guide is silent on: the One Stop Shop thresholds, refunds without a
  credit note, missing invoices for the reverse charge, refunds of foreign
  VAT, penalties, the VIES dates, and the tax point for services.
