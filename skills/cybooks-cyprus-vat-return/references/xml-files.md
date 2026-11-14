# The two files

The Tax Department's portal, Tax For All (TFA), takes a VAT return and a
VIES statement as an XML file in place of typing the figures in.
`scripts/vat_return.py` writes both. This file says what goes in, what
comes out, and what the script will not do.

**Source.** The Tax Department's instructions for building the XML files
and the schemas it publishes with them. The four schema files are in
`assets/schemas/`. The instructions were written for the earlier portal,
TAXISnet, and still carry its name; the file format is the same. The
files are written the way Cybooks writes the ones its customers upload.

## The commands

| Command | Does | Writes |
|---|---|---|
| `prepare` | A draft of the thirteen boxes from a list of documents (`from-documents.md`) | `prepared-boxes.json`, `prepared-documents.csv`, `prepared-vies-lines.csv` |
| `check` | The tests on the thirteen boxes | Nothing |
| `xml` | The same tests, then the VAT return file | `VAT-return_<taxpayer>_<from>_<to>.xml` |
| `vies` | One month's VIES statement from a list of sales | `VIES_<taxpayer>_<YYYY-MM>.xml` and `.lines.csv` |
| `numbers` | Looks VAT numbers up in the EU's VIES service | Nothing |

Every command prints JSON. **Exit codes:** 0 done; 2 `xml`, `vies` or
`prepare` wrote no file, and the output says why; 1 the input or the command line could
not be read, with the reason as plain text and no JSON. `check` exits 0 whatever it finds: read
`blocks_file` in its output, not the exit code. Run a command with
`--help` for every option.

## What both files share

- UTF-8, with the XML declaration as the first line.
- One return or statement per file. The portal allows up to 50 in one
  file, each for a different taxpayer; this script writes one.
- `taxpayer`: the company's VAT registration number **without** the `CY`:
  eight digits and a letter. The script takes it with or without `CY`,
  spaces or dashes, and stops the file if what is left is not eight
  digits and a letter.
- `version="2010-1.0"`, fixed.
- At most 4 MB.
- Euros. A company that keeps its books in another currency converts
  first, and the report says so.

## How figures are read

Figures given as text are read as either 1.234,56 or 1,234.56, worked out
from all the figures of a run together. The script stops, and asks,
where a wrong reading is possible:

- the two formats are mixed (the wrong reading is a hundred or a thousand
  times too large);
- a lone `1,234` or `1.234` beside figures in the other format;
- text that is not plainly one number: a date, digits with spaces between
  them, `n/a`.

`--decimal comma` or `--decimal point` says which format is meant. The
output shows the format it read (`decimal_mark_read`): put it in the
report. `nil`, `none`, `zero` or `-` in a box is read as 0 and shown as
"given as nil". An empty cell is a box without a figure.

**When you write a CSV for the script, write it with code** (Python's
`csv` module), so that an amount containing a comma is quoted. A row with
more cells than the header stops the run: that is an amount the delimiter
has cut in two.

## The VAT return file

```bash
python3 scripts/vat_return.py check --taxpayer CY12345678X \
  --from 2026-07-01 --to 2026-09-30 --boxes boxes.csv \
  --vies "2026-07:goods=0,triangular=0,services=4301,rows=2" \
  --vies "2026-08:goods=0,triangular=0,services=3160,rows=2" \
  --vies "2026-09:goods=3200,triangular=0,services=5901,rows=3"
```

`xml` takes the same arguments, plus `--out DIR`.

**The figures.** `--boxes` takes a CSV with the columns `box` and `amount`,
or JSON: `{"1": 500.00, "2": 190.00, ...}`, the `boxes` list Cybooks
returns, or the `prepared-boxes.json` of a draft. `--box 1=500.00` gives one box and can be repeated. Box names are
read as written: `1`, `8A`, `Box 8a`, `box-8a`. A box given twice stops
the run.

**The VIES statements of the period**, for VR-10 and VR-11. One per month,
either way:

- `--vies MONTH:goods=N,triangular=N,services=N,rows=N`: the totals of a
  statement as it was filed, in whole euros, written without a thousands
  separator. All three amounts are stated, with 0 for none. `rows` is the
  number of customers on it; it sets how much rounding the test allows,
  and can be left out.
- `--vies-result FILE`: the JSON that the `vies` command printed for that
  month. Save it when you build the statement (`... > vies-2026-07.json`).

A month with nothing to report is given as zeros. A month that is not
given, or whose statement could not be built, is not taken for nil: the
two tests then say Could not be checked and name the month and what
stopped it. While box 8A or 8B holds a figure, that also holds the return
file back, until the statements are complete or the person gives a
reason for going ahead without the tie (`--note box8b="..."`).

**What the script does to a figure, and nothing else:**

| | When | Shown as |
|---|---|---|
| Works out box 3 and box 5 | They were not given | "worked out from the other boxes" |
| Sets a box to 0 | It was not given **and** `--missing-zero` was passed | "zero, as told" |
| Rounds boxes 6 to 11B to the euro, half up | `--round-values` was passed | "rounded to the euro, from 11480.75" |

- `--missing-zero` is for a person who has said "the rest are nil". Do
  not pass it to get past VR-01.
- `--round-values` does what the guide prescribes, so it needs no
  permission. Say in the report which boxes were rounded and from what.
- A VAT figure with more than two decimals is not rounded for the person:
  VR-02 stops the file and the figure is given again to the cent.

**A written reason.** Three scored tests can stop the file: VR-09, VR-10
and VR-11. The file then waits for the figures to be corrected, or for a
reason in the person's own words:

```bash
--note box2="Goods at 5%: invoices 1042 and 1057, 1,300.00 net"
--note box8a="..."   --note box8b="..."
```

The reason is printed in the output and belongs in the report. It does
not turn the answer into Looks right. Do not write a reason yourself, and
do not offer one when the lines show a mistake: a mistake is corrected.
The tests that compare figures take no reason.

**In the file:**

| Box | Element | Written as |
|---|---|---|
| 1 | `due-outflow-vat` | `1234,56` |
| 2 | `due-eu-acquisition-vat` | `1234,56` |
| 3 | `due-vat-total` | `1234,56` |
| 4 | `deducted-eu-acquisition-vat` | `1234,56` |
| 5 | `total-vat` | `1234,56`, or `-1234,56` for a credit |
| 6 | `total-outflows` | `1234,00` |
| 7 | `total-inflows` | `1234,00` |
| 8A | `total-to-eu-services` | `1234,00` |
| 8B | `total-to-eu-supplied-services` | `1234,00` |
| 9 | `total-to-eu-zero-services` | `1234,00` |
| 10 | `total-sales` | `1234,00` |
| 11A | `total-from-eu-services` | `1234,00` |
| 11B | `total-from-eu-supplied-services` | `1234,00` |

All thirteen, once each, in this order, with `0,00` for a nil box. The
element names are the schema's and do not read like the boxes (8A is goods,
though its element says services). Do not rename them.

## The VIES file

A VIES statement covers **one calendar month** and lists, per customer in
another Member State, the value sold to them.

```bash
python3 scripts/vat_return.py numbers DE123456789 EL123456789 > numbers.json
python3 scripts/vat_return.py vies --taxpayer CY12345678X --month 2026-08 \
  --lines eu-sales.csv --numbers numbers.json --out . > vies-2026-08.json
```

Beside the XML it writes `VIES_<taxpayer>_<YYYY-MM>.lines.csv`: every row
with the documents behind it and the exact amount before rounding. Keep
the two together.

**The lines.** A CSV with one row per invoice or credit note. It may cover
a whole quarter: with a date column the script uses the lines of the
month and counts the others (`lines_of_other_months`).

| Column | Needed | Notes |
|---|---|---|
| Customer VAT number | Yes | With its country code (`DE123456789`). Or a separate country column; where both are there they must name the same country |
| Net amount | Yes | In euros, excluding VAT. **A credit note is negative** |
| Kind of supply | Yes, or `--default-kind` | `goods`, `services` or `triangular` |
| Date | No | `2026-08-31`, or day first: `31/08/2026`. Without the column, every line is taken to be of the month and VS-03 says so. With it, a line whose date is empty is refused |
| Document number | No | Goes into the lines file |
| VAT amount | No | When present (also as a plain "VAT" or "Tax" column), a line that carries VAT is refused |

Columns are found by name ("VAT Reg No", "Net EUR", "Goods/Services" and
the like). Name one by hand with `--map vat_number="Tax ID"`; `--help`
lists the fields. With no column for the kind of supply the script stops:
name the column, or pass `--default-kind services` when the person has
said every line is of one kind. Do not choose the kind yourself.

**What belongs on it.** Sales to VAT-registered customers in other Member
States where the customer accounts for the VAT: goods (box 8A of the
return), services (box 8B) and triangular sales. A credit note a customer
issues on your behalf (self-billing) is a sale and belongs on it.

**The tests:**

| Code | Test | Stops the file |
|---|---|---|
| VS-01 | The taxpayer number is a Cyprus VAT number | Yes |
| VS-02 | Every line of the month can go on the statement | Yes, until `--skip-unusable` |
| VS-03 | Every line has a date that can be read | Through VS-02 |
| VS-04 | No line carries VAT | Through VS-02 |
| VS-05 | One row per customer VAT number | No |
| VS-06 | Every customer VAT number is registered in VIES | Yes, when one is not registered |
| VS-07 | The statement fits the form (12,000 rows, amount range) | Yes |
| VS-08 | The file holds the figures that were tested | Yes |

All are worked out tests. VS-06 says Could not be checked when the
numbers were not looked up or VIES gave no answer; the file is still
written, and the report says the numbers were not confirmed. `line` in
`unusable_lines` is the line of the file, the header being line 1.

**What the script does:**

- Reads the country from the first two letters of the VAT number, and
  writes Greece as `EL`.
- Adds up all documents of one customer VAT number into one row, however
  the number was typed (spaces, dots, lower case).
- Rounds each amount of a row to the whole euro, half up. The totals are
  the sums of the rounded rows.
- Leaves out a customer whose amounts all come to nil, and lists them.
- Writes no file for a month with no rows: there is nothing to report.

**What it refuses.** A line of the month that cannot go on the statement
stops the file: no VAT number, a Cyprus number, a number from outside the
EU (`GB` included), no date or one that cannot be read, no kind of supply,
services to `XI` (Northern Ireland is in the EU's VAT area for goods
only), or a line that carries VAT. Each is listed with its reason
(`unusable_lines`). Correct the file. Or, when the person has said the
lines do not belong on the statement, pass `--skip-unusable`: they are
left off and still listed. A customer number that VIES does not know
(VS-06) is not skipped this way: the number is corrected, or the sale
comes off the list.

**Not built:** the call-off stock table the schema allows as an optional
part of the statement. A business that moves goods under call-off stock
arrangements fills that part in on the portal.

## VAT numbers

`numbers` asks the European Commission's VIES service whether each number
is registered, and returns the registered name and address where the
Member State publishes them. It is the one command that sends anything
out of the conversation: the VAT numbers, to `ec.europa.eu`.

- **Say so.** It is a notice, not a request for permission: run the
  lookup and say in the reply, before the results, where the numbers went.
- **Unless the person said not to.** Then run `vies` without `--numbers`:
  VS-06 says Could not be checked and the file is still written. Report
  the numbers as "not looked up, at your request", with what the person
  said about them.
- **Registered / Not registered / Could not be checked.** A number that is
  not registered is most often a typing or scanning error: compare it with
  the invoice before asking the customer.
- Could not be checked: the service or a Member State is down or busy,
  the number is from outside the EU, or there is no network in this
  conversation (the command then stops waiting after the first number).
  Only a plain yes or no from VIES counts as an answer about a number.
  The person can run the same lookup at
  `ec.europa.eu/taxation_customs/vies`.
- A sale to a number that is not registered does not belong in box 8A or
  8B, or on the VIES statement.

## Three layers of checking before a file exists

1. **The tests**: VR-01 to VR-16 for the return (`boxes.md` section 3),
   VS-01 to VS-07 for a statement. One open test that stops the file, and
   nothing is written.
2. **Read back.** The script parses the XML it built and compares every
   figure with the figure it tested (VR-17, VS-08).
3. **The published schema.** With `lxml` or `xmllint` available, the file
   is tested against the Tax Department's schema and is not written if it
   fails. With neither, the output says the schema was not run. Report
   which it was.

## What no file can pass in advance

The Tax Department's instructions list what the portal checks on upload:
the taxpayer is a registered user of the portal; the person uploading has
been named by the taxpayer as its representative; no return was already
submitted for the same taxpayer and period; and the day of the upload
falls in the time allowed for that period.

## After the upload

- The file that was uploaded is kept exactly as it is. The script will not
  overwrite a file of the same name; `--replace` is for a draft that was
  never uploaded.
- A submitted return is not rebuilt. A mistake in it is corrected in a
  later return, as the guide describes (`boxes.md` section 5), or through
  the portal, as the person's accountant advises.
- The return is filed when the portal says so, not when the file exists.
