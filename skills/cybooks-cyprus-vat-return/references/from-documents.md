# A draft return from the documents

Use this when the person has no return yet and gives you the documents of
the period: the invoices they issued and the bills they received. You read
each document into one list. The script places every row in its boxes by
fixed rules, adds the boxes up and tests the result. What comes out is a
**draft** of the return, with the list of what went where.

Two things stay true however good the draft looks:

- **Documents cannot show what is missing.** A bill that was never
  uploaded leaves no trace. The draft is only written once the person has
  said, in their own words, that the documents are all of the period's.
- **The rules place a document; they do not decide a difficult case.** A
  document the rules cannot place is asked about, never guessed.

## Step 1: who the company is

Before reading anything, know the company's name and its VAT number. They
tell a sale from a purchase: a document the company issued is a sale, one
addressed to it is a purchase. Ask if the person has not said. Know the
period too.

## Step 2: read every document into the list

Open every file. For each document write one row, with code (Python's
`csv` module), into `documents.csv`:

| Column | What goes in | Notes |
|---|---|---|
| `document` | The document's own number | As printed |
| `date` | The document's date | Write it as `2026-08-31`. Day first as printed (`31/08/2026`, `31.08.2026`) and a month in words (`18 July 2026`) are read too. A date printed month first in figures (`09/02/2026` for 2 September) is written as `2026-09-02` |
| `type` | `sale`, `sale credit note`, `purchase`, `purchase credit note`, `import vat` | See below |
| `counterparty` | The customer's or the supplier's name | The legal name on the document |
| `vat_number` | The **other** party's VAT number | As printed, with its country code if it has one. Empty if the document shows none. A company registration number (`HE 123456`) is not a VAT number |
| `country` | The other party's country, two letters | Needed when there is no VAT number. From the address on the document; a town with no country named gives its country (Nicosia is `CY`) |
| `supply` | `goods` or `services` | Your reading of what the document is for |
| `currency` | Empty or `EUR`; else the currency printed | See "Euros" below |
| `net` | The amount before VAT, in euros | The figure printed, written with a decimal point and no thousands separator: `2000.00` for a printed 2.000,00 |
| `vat` | The VAT charged on the document, in euros | The same way. `0` when none is charged |
| `rate` | The VAT rate printed, in percent | Lets the script catch a misread amount. Empty when the document prints no percentage |
| `addressed_to_company` | For purchases: `yes`, `no` or `not shown` | `no` when the bill is in a director's or an employee's own name. `not shown` for a receipt made out to no one |
| `treatment` | Empty, or a special case the person has stated | See "Special cases" |
| `cy_rate` | Empty, or the Cyprus rate for a reverse charge purchase that is not at 19% | `5`, `9`, `3`, `0` or `exempt` |
| `note` | Anything worth keeping | The file name is useful |

Rules for reading:

- **Only what the document shows.** A VAT number, a country or a rate that
  is not on the document stays empty. Do not look one up, do not complete
  one from another document, and do not work the VAT out from the net.
  The script asks about what is missing.
- **One row per VAT rate, and per kind of supply.** A document with two
  rates, or with goods and services, is two rows with the same number.
- **Amounts unchanged.** Write the figure the document prints, in one
  number format for the whole list. For a credit note write the amounts
  as printed; the script takes them as negative.
- **Euros.** For a document in another currency use the euro amount
  printed on it. If it prints none, put the currency in the `currency`
  column, leave `net` and `vat` empty and keep the printed amount in the
  note. The script then asks the person for the euro amount (their bank
  or card statement shows it) or the rate they use. Do not pick a rate.
  Once the person has given it, write the euro amount in `net`, keep the
  printed currency in `currency`, and say where the figure comes from in
  a column `euro_amount_from` ("card statement, per the person"). The
  output lists every such figure, and so does the report.
- **`import vat`** is a customs declaration: the VAT paid at the border
  goes in `vat`. The supplier's own invoice for those goods is a separate
  `purchase` row with no VAT.
- **A document you cannot read** (a blurred scan, a cut-off page) is not
  typed from what you can make out. List it for the person.

Not rows of the list:

- Reminders, statements of account, quotes, pro-forma invoices, order
  confirmations, delivery notes.
- A payment receipt for an invoice that is already in the list. Where
  there is a receipt and no invoice, the receipt is the row.
- Bank statements, payslips, loan and tax papers. They are not in a VAT
  return at all.

List what you left out, with the reason, so the person can see nothing
was dropped by accident.

### Special cases: the `treatment` column

Leave it empty unless the person, or the document itself, says one of
these:

| `treatment` | Use for |
|---|---|
| `exempt` | A sale or a purchase that is exempt from VAT by its nature (rent of a home, insurance, most financial services). **Not** a sale to another Member State or an export that the document calls "VAT exempt": leave those empty, and the rules place them |
| `zero rated` | A sale in Cyprus at 0% |
| `outside the scope` | A sale outside the scope of Cyprus VAT that the rules below would not place |
| `triangular` | A sale as the middle party of a triangular transaction |
| `not business` | A private item among the documents |
| `outside the return` | A document that is no supply at all (a deposit returned, a fine) |

For a purchase only `exempt`, `not business` and `outside the return`
apply. `exempt`, `zero rated`, `outside the scope` or `triangular` on a
document that shows VAT contradict it, and the script asks which is
right. A private bill needs one mark, not two: `not business`, or
`addressed_to_company` `no`.

Do not choose a treatment to make a question go away. A question goes to
the person.

### Show the list before preparing

Tell the person what you read: how many sales and purchases, their totals,
what you left out and why, and what you could not read. Ask whether these
are all the documents of the period. Their answer, in their words, is what
`--note documents=` carries. When they already said so ("here are all our
invoices for Q3"), that sentence is the statement.

## Step 3: prepare

```bash
python3 scripts/vat_return.py prepare --from 2026-07-01 --to 2026-09-30 \
  --documents documents.csv --out . \
  --note documents="Here are all our bills and invoices for Q3"
```

The output is JSON: the thirteen boxes, every document with its boxes
(`placed`), the documents grouped by how they were placed, the questions,
the VAT that was not claimed, what was left out, the due dates, and eight
tests.

Exit code 2 means the draft is held and no file was written: the boxes in
the output are then the boxes as they would be from the rows that could
be placed. While a draft is held nothing is built from it: no VIES
statement, no return file. Each run replaces the files of the run before,
and a held run removes them.

### How a document is placed

Sales, by what the document shows:

| The sale | Boxes | VIES |
|---|---|---|
| With Cyprus VAT | 1 (the VAT), 6 | |
| Goods to a customer with a VAT number of another Member State, no VAT | 8A, 6 | Goods |
| Services to a customer with a VAT number of another Member State, no VAT | 8B, 6 | Services |
| Goods to a customer outside the EU, no VAT (an export) | 9, 6 | |
| Services to a customer outside the EU, no VAT | 10, 6 | |
| `zero rated` | 9, 6 | |
| `exempt` | 6 | |
| `outside the scope` | 10, 6 | |
| `triangular` | 10, 6 | Triangular |

Purchases:

| The purchase | Boxes |
|---|---|
| Cyprus supplier with a VAT number, with VAT | 4 (the VAT), 7 |
| Cyprus supplier, no VAT | 7 |
| Goods from a supplier with a VAT number of another Member State, no VAT | 2 and 4 (19% of the net), 7, 11A |
| Services from a supplier with a VAT number of another Member State, no VAT | 1 and 4 (19% of the net), 6, 7, 11B |
| Services from a supplier outside the EU, no VAT | 1 and 4 (19% of the net), 6, 7 |
| Goods from a supplier outside the EU, no VAT | 7. The import VAT is on the customs declaration |
| `import vat` | 4 |
| `exempt` | 7 |

A credit note goes where its invoice went, with the sign turned. That
includes the reverse charge: a credit note from an EU goods supplier
lowers boxes 2, 4, 7 and 11A.

A Cyprus VAT number printed without its `CY` is written with it in the
output. A supplier whose number starts with `EU` holds a One Stop Shop
registration and is outside the EU. A `GB` number is outside the EU. `XI`
(Northern Ireland) counts as the EU for goods only.

The reverse charge is worked out at 19% unless `cy_rate` says otherwise.
With `cy_rate` `exempt` no VAT is due and the value still goes in its
boxes.

Placing exports in box 9 and services to customers outside the EU in box
10 rests on practice, not on the guide's wording: the output marks those
groups, and the report says so.

### What is asked, not decided

The draft waits (PD-01) for an answer on each of these:

- No VAT on a sale to a customer in Cyprus.
- No VAT on a sale to a customer in another Member State who has no VAT
  number. A sale to a consumer carries VAT.
- No VAT on a purchase from a supplier in another Member State who shows
  no VAT number.
- No country and no VAT number, or letters in front of a number that are
  not a country the list knows.
- A document in another currency with no euro amount.
- A treatment that contradicts the VAT on the document, or that does not
  apply to a purchase.
- No VAT on a sale or a purchase abroad, and the list does not say goods
  or services.
- A country column and a VAT number that name two countries.

Put each question to the person as the output words it. Their answer
changes the row: a VAT number, a country, or a treatment.

### VAT that is not claimed, and documents left out

The script leaves VAT out of box 4, and says so, when:

- a Cyprus supplier's document shows VAT but no supplier VAT number on
  the record. Box 4 needs "a proper VAT invoice". Have the person check
  the invoice itself: records often lose a number the paper prints;
- the document is a receipt made out to no one (`not shown`). The person
  asks the supplier for a VAT invoice in the company's name;
- the VAT is another country's. It is reclaimed from that country, or
  from the supplier when it was charged by mistake.

The first two make PD-05 say Needs a look: the person can still get that
VAT back with the right document. VAT of another country is listed and
PD-05 still passes.

The net amount still goes in box 7. A purchase that is not addressed to
the company is left out of the return altogether. Both lists go into the
report in full: this is money the person may expect to get back.

### The tests on a draft

| Code | Test | Grade | Stops the draft |
|---|---|---|---|
| PD-01 | Every document could be placed in the return | Worked out | Yes |
| PD-02 | No document is in the list twice | Worked out | Yes |
| PD-03 | Every document has a date that can be read | Worked out | Yes |
| PD-04 | The VAT on each document agrees with its rate | Worked out | Yes |
| PD-05 | Input VAT is claimed only where the document supports it | Worked out | No |
| PD-06 | Your own invoice numbers run without a gap | Scored | No |
| PD-07 | Input VAT can be deducted in full | Scored | No |
| PD-08 | The documents are all of the period's | Worked out | Until the person has said so |

- **PD-01** also stops a list in which no document is dated in the
  period: that is a wrong period or dates read the wrong way round, not a
  nil return.
- **PD-02.** A row is there twice when everything about it is the same.
  Two rows of one document, at two rates or for goods and services, are
  not a duplicate.
- **PD-03.** Documents dated outside the period are left out and counted
  by month. Tell the person: a late bill may belong in the next return.
- **PD-04** catches a misread figure: 109.00 where the document says 19%
  of 1,000.00. Read the document again; do not adjust the amount to fit.
  It allows 5 cents, or half a percent of the VAT for a long bill whose
  lines are rounded one by one.
- **PD-06** is the one sign of completeness the documents carry. A gap in
  the company's own numbering is a cancelled number or a missing sale.
- **PD-07.** A company with exempt sales may deduct only part of its input
  VAT. The draft claims all of it and says so: the accountant works out
  the part.
- **PD-08** never passes. With the person's statement it stays "Could not
  be checked" and the draft is written, carrying the statement.

## Step 4: from the draft to the files

When the draft is written, three files are in the folder:

| File | What it is | Goes to |
|---|---|---|
| `prepared-boxes.json` | The thirteen boxes | `check` and `xml`, as `--boxes` |
| `prepared-vies-lines.csv` | The sales to EU customers, one row each | `vies`, as `--lines`, once per month |
| `prepared-documents.csv` | Every document with its treatment and its boxes | The person, and the report |

Then go on as SKILL.md describes: build the VIES statement of each month
from `prepared-vies-lines.csv`, run `check` with `--boxes
prepared-boxes.json` and the statements, and build the return with `xml`.
The boxes then show "prepared from n documents" as their source. A draft
prepared for one period is refused for another, and so is one whose
figures were changed by hand: a correction goes into `documents.csv`, and
`prepare` runs again. A month with no row in `prepared-vies-lines.csv`
has no statement: give it to `check` as zeros once the person has
confirmed they sold nothing to EU businesses that month.

Run the line tests of `boxes.md` section 4 on `prepared-documents.csv`
too. Most pass by construction, since the script placed the lines. Three
still ask the person something:

- **VL-10.** A document dated in this period that describes an earlier
  one ("services June", "Q2") may already be in the return before: Worth
  a look, as a question.
- **VL-11** is Could not be checked: documents carry no account names.
- **VL-12.** Each export in box 9 asks for the export evidence.

## What a draft cannot know

Say these in the report, under "Not checked":

- Whether every document of the period is there.
- Whether a document belongs to this period by its tax point. Goods from
  the EU are due by the invoice date, or the 15th of the month after
  dispatch if that is earlier; the draft goes by the document's date.
- How much input VAT a partly exempt business may deduct.
- Sales to consumers in other Member States above the EU-wide 10,000 euro
  threshold, which belong on a One Stop Shop return.
- Special schemes: second-hand goods, travel agents, cash accounting, bad
  debt relief, private use of business goods, the sale of assets.
- Anything that was never on a document: a payment with no bill.

A draft is where a return starts. The person, or their accountant, reads
`prepared-documents.csv` before anything is uploaded.
