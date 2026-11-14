# VAT return review: the format

Return this structure every run, sections in this order.

---

# VAT return review: [period, for example July to September 2026]

**Company:** [name, if given] · **VAT number:** [number] · **Period:**
[from] to [to] · **Due:** [date; "passed n days ago" when it has; the Tax
Department sometimes extends a date: confirm it on the portal] ·
**Source:** [Cybooks, read (date and time), draft or filed / files: list
each, with its export date if it has one / typed in the conversation; say
which number format was read; say if any figure was read from a picture
or a PDF and confirmed by the person, or converted to euros] · **Guide:**
Tax Department VAT Guide, 6 August 2024 [or the edition the person gave] ·
**Run:** [date]

## Result: [Draft prepared from n documents / Draft held: n questions / Files built / No file yet: n tests open / Review only / File comes from Cybooks]

[Where two results apply, name both: "Draft prepared from 15 documents;
files built". Then two or three sentences: what the result rests on, the
one open item that matters most, and what would change it. Say what was not checked. When a
due date has passed, say so here. When more than one file was asked for,
give the result of each first: "VAT return: no file yet. VIES July and
August: built, numbers not confirmed. VIES September: not built." A due
date that has passed, the return's or a statement's, is said here too.]

**Box 5:** [amount] [payable / credit carried forward or refundable / nil]
[add "as given; the open findings would change it" when they would]

## The documents

[Only for a draft from documents. Leave the section out otherwise.]

**Read:** [n] documents · **In the return:** [n] · **Left out:** [n] ·
**Of other periods:** [n, by month] · **Questions:** [n] · **Said to be
complete:** ["the person's statement, in their words" / not yet]

| How it was placed | Documents | Net | VAT on the documents | VAT the company accounts for | Boxes |
|---|---|---|---|---|---|
| [treatment, as the script names it; add "(practice)" where the output marks it] | | | | [the reverse charge, where there is one] | |

[Say once, in a sentence, that a service bought under the reverse charge
also counts in box 6: the guide asks for it, and it surprises people.]

**VAT not claimed:** [each document: number, supplier, the VAT left out of
box 4, and why. Or "none"]

**Euro amounts that are not on the document:** [each document in another
currency: the printed amount, the euro amount used and who gave it. Leave
out when there is none]

**Left out of the return:** [each document and why: not addressed to the
company, private, no supply; and what you did not put in the list at all:
reminders, quotes, receipts for a listed invoice, unreadable scans]

**Tests on the draft:** [PD-01 to PD-08, each with its answer and what was
found. PD-08 is always "Could not be checked"]

**This is a draft.** [One sentence: the list of every document and its
boxes is in `prepared-documents.csv`; read it, or have your accountant
read it, before anything is uploaded. While the draft is held that file
does not exist: say so, and show each document with its boxes from the
output's `placed` list.]

## The thirteen boxes

| Box | What it is | Amount | Where the figure comes from |
|---|---|---|---|
| 1 | VAT due on sales and other outputs | | [given / given as nil / prepared from n documents / from the documents that could be placed; draft held / worked out from the other boxes / rounded to the euro, from x / zero, as told / Cybooks] |
| ... | | | |

[All thirteen, always. An amount that was not given is "not given", never
0.]

## Tests on the figures

| Code | Test | Answer | What was found |
|---|---|---|---|
| VR-01 | Every box has a figure | [Passed / Needs a look / Could not be checked / Not relevant] | |
| VR-09 | Box 2 against 19% of box 11A | [Looks right / Worth a look / Could not be checked / Not relevant] | [the two figures, the gap, and the written reason if one was given] |

**Totals:** [n] passed · [n] need a look · [n] look right · [n] worth a
look · [n] could not be checked · [n] not relevant

[Every test of the last run, in code order: VR-01 to VR-16 from `check`,
and VR-17 as well from `xml`. The totals are that run's `counts`. A scored
test is never counted under passed. While a draft is held these tests
have not run: write "Not run: the draft is held" and leave the table out.]

## Tests on the lines

| Code | Test | Answer | Lines |
|---|---|---|---|
| VL-03 | Reverse charge VAT on services is in box 1, never box 2 | | [document, supplier, amount, the box it is in, the box it belongs in] |

**Totals:** [as above, for the twelve line tests, counted from your own
results]

[All twelve, VL-01 to VL-12, passed ones included. Leave the section out when no lines were given, and say under "Not
checked" that the lines were not seen. Mark a finding that rests on
practice, not on the guide, with "(practice)" and word it as a question.]

**What the corrections would do to the boxes:** [one line per finding:
the document, and each box it would raise or lower, by how much. A guide
for the person; the correction is made in their books. An effect that
depends on an answer still owed is given as "if ...". Leave out when no
line test has an open finding.]

## VIES statement: [month]

[One section per month of the period: built, given as filed, or not
built. A month with no sale to an EU business among the documents gets
one line: no statement, once the person confirms it; no table. For a month that was not built, put the tests that stopped it in
the heading, "(not built: VS-02, VS-06)", and show the rows as they would
be. A row's `note` (a Greek number given as GR) goes beside its number. For one given as filed, show
its totals and leave the table out.]

**Rows:** [n] · **Goods:** [amount] · **Triangular:** [amount] ·
**Services:** [amount] · **Due:** [date; "passed n days ago" when it has]

| Row | Customer VAT number | In VIES | Goods | Triangular | Services | Documents |
|---|---|---|---|---|---|---|
| | | [Registered / Not registered / Could not be checked / Not looked up] | | | | |

**Tests:** [each VS test that is not Passed, with what was found, those
that stop the file first; or "all passed"]

**Left off the statement:** [each unusable line: document, customer,
amount, reason; each customer that came to nil; and how many lines of
other months the file held]

## VAT numbers

[n] registered · [n] not registered · [n] could not be checked. [Name each
that is not registered or could not be checked. Say that the numbers were
sent to the EU's VIES service, and when. When no number was looked up,
say so in one line, with the reason ("not looked up, at your request: you
confirmed them with the customers"), and repeat it under "Not checked".]

## Adjustments and items waiting

[Connected to Cybooks only: every manual adjustment to a box, with its
amount and reason; import VAT that is waiting and for what. Leave the
section out otherwise.]

## Not checked

| What | Why | What would enable it |
|---|---|---|
| Whether each invoice is in the right box | Only the thirteen figures were given | The VAT report by transaction |
| Whether every document of the period was given | Documents cannot show what is missing | A bank statement of the period |

[Always present. From thirteen figures alone the tests show that the boxes
agree with each other, not that each is right.]

## The files

| File | Size | Schema | SHA-256 |
|---|---|---|---|
| [name] | [bytes] | [passed, with lxml or xmllint / not run: no validator in this conversation] | [first 12 characters] |

[Leave the section out when no file was written. When a test stopped a
file, say which, under Result. A VIES file whose customer numbers were not
confirmed in VIES is marked "numbers not confirmed" here.]

## Before you upload

1. [What is still open, in the order to clear it: figures to correct in
   the books first, then reasons to write down, then VAT numbers to
   confirm. Leave the step out when nothing is open.]
2. Compare the thirteen boxes above with the VAT report of your own
   software, figure by figure. [For a draft from documents: "Read
   `prepared-documents.csv`, or have your accountant read it."]
3. Upload the file in Tax For All, signed in as a person who may act for
   the company. Keep the file as it was uploaded. [When no file was
   built: "Then send the corrected figures, and the files follow."]

[Connected to Cybooks: step 3 is "Download the file in Cybooks with
Download TFA XML, upload it, and record the outcome in Cybooks."]

---

## Questions

[Each question a finding rests on, one line each. Then the offer: go
through the open items one by one, or run again after corrections. Leave
the section out when there is nothing to ask.]

---

*This review tests the figures as they were given on [date of the export
or of the Cybooks read; the date the figures were given, when an export
carries none]. It shows whether the boxes agree with each other,
with the Tax Department's guide and with the published file format. It
does not say the return is correct, and it is not tax advice. Nothing was
filed: a return is filed when a person uploads it and the portal accepts
it.*

---

## Rules for the report

- Every figure is the one the script printed or Cybooks returned. None is
  typed from memory or rounded by hand. Showing it in the person's number
  format is not changing it.
- Show the table of tests with the boxes, never the boxes alone.
- Four answers for a worked out test; a scored test says Looks right or
  Worth a look. "Could not be checked" is never counted as passed.
- A written reason is quoted in the person's words beside its test.
- Never correct, compliant, clean, verified, audited, approved or
  certified. A file "passed the tests of this skill and the published
  schema".
- Amounts in euros, two decimals, in the number format of the person's own
  message, or of their files when the message has no figures (1,234.56
  when neither shows one and they write in English). The file itself
  always uses the portal's format.
- The same sections in the same order every run.
