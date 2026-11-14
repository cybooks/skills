---
name: cybooks-cyprus-vat-return
description: >-
  Prepares a draft Cyprus VAT return from the period's bills and invoices,
  reviews a return box by box against the Tax Department's guide, and
  builds the XML files for upload to Tax For All (TFA): the VAT return and
  the monthly VIES statement. A bundled script places each document in its
  boxes by fixed rules, tests the thirteen boxes against each other and
  against the VIES statements, reads the built file back, tests it against
  the published schema, and writes no file while a test that stops it is
  open. It can also look up EU VAT numbers in VIES. Works on its own from
  uploaded documents or from the figures of any accounting software, or
  connected to Cybooks, where it reads the live return. Use when someone
  prepares, checks or files a Cyprus VAT return or VIES statement. Triggers
  include "prepare my VAT return", "here are my invoices", "check my VAT
  boxes", "which box does this go in", "VAT XML", "TFA upload", "VIES
  statement", "VIES XML", "reverse charge box", and "is this VAT number
  valid". Cyprus only.
license: MIT, except the Tax Department's schema files in assets/schemas. See LICENSE.txt.
metadata:
  author: "Cybooks - cybooks.com.cy"
  version: "1.1.0"
---

# Cyprus VAT return

## What this skill does

A Cyprus VAT return is thirteen figures. Most mistakes on it are not
arithmetic: they are a figure in the wrong box, a box left out, or a return
that does not agree with the VIES statements filed for the same months.
This skill asks the same questions of every return, in the same order, and
only then builds the file for the portal.

It does four things:

1. **Prepares a draft return** from the period's bills and invoices: each
   document is read into a list and placed in its boxes by fixed rules.
2. **Reviews a return.** Tests the thirteen boxes against each other, and,
   when the lines behind them are given, tests each line against what the
   Tax Department's guide says belongs in each box.
3. **Builds the VAT return file** for upload to Tax For All.
4. **Builds the monthly VIES file** from the month's sales to EU customers.

It does not file anything. A person uploads the file.

## Two ways to run

| | Connected to Cybooks | On its own |
|---|---|---|
| When | Tools named `cybooks_*` are available | No Cybooks tools |
| The figures | The live return in Cybooks, with its transactions | The person's figures, typed or exported from any software; or their bills and invoices |
| The file | Comes from Cybooks, which builds and tests it. This skill reviews | Built by this skill's script |
| Read next | `references/cybooks-connected.md` | "On its own" below |

`scripts/` and `references/` are folders of this skill, beside this file.
When the working directory is somewhere else, give the script its full
path.

## Rules

These are not style. Breaking one makes the return wrong.

1. **Computed, not eyeballed.** Every test and every figure in a file comes
   from `scripts/vat_return.py`, from Cybooks, or from your own code over a
   file you name. If code cannot be run in this conversation and Cybooks is
   not connected, say so and stop. Never write the XML by hand.
2. **Nothing is filed and nothing is changed.** The skill writes a file. It
   does not upload it, and connected to Cybooks it only reads.
3. **No file while a test that stops it is open.** The script enforces it.
   Do not work around it by building the XML another way. Which tests
   stop a file is in `references/boxes.md` and `references/xml-files.md`.
4. **The figures are the person's.** Never change a figure so that the
   boxes agree. Report the disagreement; the correction is made in the
   books. The script changes a figure in three stated cases only, each
   printed with its reason (`references/xml-files.md`). A draft from
   documents holds only what the documents show: nothing is looked up,
   completed or worked out by you, and the list of what went where goes
   to the person with it.
5. **A gap is never filled with an assumption.** A box that was not given
   is not zero. A sale whose kind is not stated is not a service. A figure
   that could be read two ways is asked about. A month without a VIES
   statement is not a month with nothing to report. A document the rules
   cannot place is a question for the person, and documents never show
   which documents are missing.
6. **Four answers, two grades.** A *worked out* test compares figures:
   **Passed**, **Needs a look**, **Could not be checked** or **Not
   relevant**. A *scored* test weighs likelihood: **Looks right** or
   **Worth a look**, never Passed. "Could not be checked" is its own
   answer, never counted as passed.
7. **The guide is the source.** A finding quotes the box definition it
   rests on. A rule the guide does not state is marked as practice and
   worded as a question.
8. **No assurance words.** A file "passed the tests of this skill and the
   published schema". It is never correct, compliant, clean, verified,
   audited, approved or certified. The return stays the taxpayer's.
9. **A submitted return is not rebuilt.** A mistake in it is corrected in
   a later return or through the portal, as the person's accountant
   advises. The uploaded file is kept as it was.

## From documents

When the person gives you bills and invoices and no return, start with
`references/from-documents.md`. In short:

1. Know the company's name, its VAT number and the period.
2. Read every document into `documents.csv`, one row per document and VAT
   rate, with only what the document shows.
3. Tell the person what you read and what you left out, and ask whether
   these are all the documents of the period.
4. Run `prepare`. Put its questions to the person; a question is never
   answered by choosing the likelier reading.

   ```bash
   python3 scripts/vat_return.py prepare --from 2026-07-01 --to 2026-09-30 \
     --documents documents.csv --out . \
     --note documents="Here are all our bills and invoices for Q3"
   ```

5. Go on with "On its own" from step 3, with the draft's files: the VIES
   statements from `prepared-vies-lines.csv`, the tests and the return
   file from `prepared-boxes.json`.

The result is a draft. Say so at the top of the report, list the VAT that
was not claimed and every document that was left out, and tell the person
to read `prepared-documents.csv`, or have their accountant read it,
before anything is uploaded.

## On its own

1. **Find out what is needed**, unless the request already says: a draft
   from documents, a review, the VAT return file, a VIES file, or all of
   them. Then collect the
   company's VAT number, the period, and the thirteen figures from the VAT
   report of the person's software, in euros. If the person has not said,
   ask whether the return or any of the period's VIES statements was
   already submitted: a submitted one is not rebuilt (rule 9).
2. **Get the figures in as data.** Read a CSV or an Excel workbook with
   code, and write the boxes to a CSV with the columns `box` and `amount`,
   using Python's `csv` module so that amounts are quoted. Figures read
   from a picture or a scanned PDF are read back to the person, box by
   box, and confirmed before use.
3. **The VIES statements come first.** The return is tested against them.
   For each month of the period, either build the statement from the
   person's list of EU sales:

   ```bash
   python3 scripts/vat_return.py numbers DE123456789 EL123456789 > numbers.json
   python3 scripts/vat_return.py vies --taxpayer CY12345678X \
     --month 2026-08 --lines eu-sales.csv --numbers numbers.json \
     --out . > vies-2026-08.json
   ```

   or, when it was already filed, ask for its totals (goods, triangular,
   services, and the number of rows). One list of sales may cover the
   whole quarter: run `vies` once per month on the same file. `numbers`
   sends the VAT numbers to the EU's VIES service: say so
   (`references/xml-files.md`). A month with no sales to EU customers has
   no statement: give it to the next step as zeros, once the person has
   said so.
4. **Run the tests on the thirteen boxes.**

   ```bash
   python3 scripts/vat_return.py check --taxpayer CY12345678X \
     --from 2026-07-01 --to 2026-09-30 --boxes boxes.csv \
     --vies-result vies-2026-07.json --vies-result vies-2026-08.json \
     --vies "2026-09:goods=0,triangular=0,services=0"
   ```

   The output is JSON: the thirteen boxes with where each figure comes
   from, the due date and whether it has passed, and every test with its
   answer. The tests are listed in `references/boxes.md` section 3; the
   options in `references/xml-files.md`.
5. **Test the lines, if the person has them.** A VAT report by transaction
   or a sales and a purchase list lets you run the tests in
   `references/boxes.md` section 4 with your own code. Without the lines,
   say plainly that the review shows the boxes agree with each other, not
   that each is right.
6. **Go through what is open.** A worked out test that needs a look is
   corrected in the books and the figures given again. A scored test that
   is worth a look takes either a correction or the person's written
   reason. Do not offer a reason yourself, and never for a gap the lines
   show to be a mistake. In a conversation, take the items one at a time.
   When the report has to stand on its own, put them in its "Questions"
   section, in the order to clear them.
7. **Build the VAT return file** once nothing stops it: no test of the
   script that stops a file, and no worked out line test that needs a
   look. The same command with `xml` in place of `check`, plus `--out .`.
   Exit code 2 means no file was written; the output says which test
   stopped it.
8. **Write the report** in the format of
   `references/vat-return-report-template.md`, and hand over the files
   with it. Never the file without the table of tests.
9. **Say what happens next:** a person who may act for the company uploads
   the file in Tax For All, and keeps the file as it was uploaded.

**Only a VAT number to look up?** Run `numbers`, answer in a few lines
(registered or not, the registered name, when it was asked, where the
number was sent), and leave the report out.

## Reference files

- `references/from-documents.md`: a draft return from bills and invoices:
  how to read them, how each is placed, what is asked.
- `references/boxes.md`: what belongs in each box, the tests on the
  figures and on the lines, the rules that trip people up.
- `references/xml-files.md`: the two files, the script's options, what it
  refuses.
- `references/cybooks-connected.md`: reading the return from Cybooks.
- `references/vat-return-report-template.md`: the report.
- `assets/schemas/`: the Tax Department's published schemas.

## Sister skills

Use them when installed. Do not invoke a skill with a similar name that is
not one of these.

- `cybooks-month-end-close`: its VAT checks ask whether the VAT account in
  the ledger ties to the returns and whether a filing is overdue. This
  skill looks at the return itself.
- `cybooks-close-readiness-scorecard`: an open finding here belongs in its
  dimension "Tax and payroll tie".
- `cybooks-journal-entry-screen`: screens the period's journal entries,
  manual postings to the VAT account included.

## What this skill is not

It is not tax advice, not a tax agent and not bookkeeping. It tests a
return against the Tax Department's published guide and file format. A
draft from documents places each document by a fixed rule and asks about
the rest: it does not decide a difficult case, and it cannot see a
document that was never given to it. Due dates are worked out from the guide's rule; the Tax
Department sometimes extends one, so the person confirms the date on the
portal. It covers the VAT return and the VIES statement. It does not
cover the One Stop Shop return, payroll returns, or any country other than
Cyprus. On its own it sees only what the person gives it.
