# Cybooks finance skills for Claude

Four skills that teach Claude how a careful bookkeeper closes a month and
prepares a VAT return. Each asks the same questions in the same order
every time, works its figures out with code, and writes down an answer for
every question, also when the answer is "could not be checked".

They work with Claude Code, the Claude apps, and any agent that reads
[Agent Skills](https://agentskills.io). They work on their own, from the
exports of any accounting software, and they read the live books when
[Cybooks](https://cybooks.com.cy) is connected.

Built by [Cybooks](https://cybooks.com.cy), accounting software for Cyprus
companies. Free, and open source under the MIT licence.

## What are skills?

A skill is a folder with instructions, reference material and sometimes a
script. Claude loads it when a task calls for it. These four hold the
checks Cybooks runs on its own customers' books, published so anyone can
use them.

## The skills

| Skill | The question it answers |
|---|---|
| [cybooks-month-end-close](skills/cybooks-month-end-close/) | What is still open before this month can be closed? |
| [cybooks-journal-entry-screen](skills/cybooks-journal-entry-screen/) | Which journal entries would a reviewer want to look at? |
| [cybooks-close-readiness-scorecard](skills/cybooks-close-readiness-scorecard/) | Are the books ready to close: yes, with notes, or not yet? |
| [cybooks-cyprus-vat-return](skills/cybooks-cyprus-vat-return/) | Here are my invoices: what is my Cyprus VAT return? Is each figure in the right box, and can I have the file for the portal? |

The first three apply to any double-entry books. The fourth is for Cyprus
only.

### How they fit together

```
cybooks-month-end-close ────────┐  the full catalogue of checks
cybooks-journal-entry-screen ───┼──►  cybooks-close-readiness-scorecard
cybooks-cyprus-vat-return ──────┘     one verdict, and the path to ready
```

Each works alone. When more than one is installed, the scorecard uses what
the others found.

## Installation

### Option 1: in a terminal (recommended)

[`npx skills`](https://github.com/vercel-labs/skills) installs skills into
Claude Code and other coding agents:

```bash
# See the four skills
npx skills add cybooks/skills --list

# Install them (it asks which, and where)
npx skills add cybooks/skills

# Install one, for Claude Code, for every project on this machine
npx skills add cybooks/skills --skill cybooks-cyprus-vat-return -a claude-code -g
```

`skills` is Vercel's open tool. It needs Node.js 22.20 or later, and it
reports each install to skills.sh (the skill's name, its files and a
timestamp) unless `DISABLE_TELEMETRY=1` is set.

### Option 2: as a Claude Code plugin

Inside Claude Code:

```
/plugin install cybooks-finance --marketplace cybooks/skills
```

Or from a shell:

```bash
claude plugin marketplace add cybooks/skills
claude plugin install cybooks-finance@cybooks
```

The skills then appear under the plugin's name, for example
`/cybooks-finance:cybooks-month-end-close`.

### Option 3: in the Claude apps

Download a `.skill` file from
[cybooks.com.cy/claude-finance-skills](https://cybooks.com.cy/claude-finance-skills/).
In Claude, open Customize, then Skills, press +, choose Create skill, then
Upload a skill, and pick the file. Switch on "Code execution and file
creation" under Settings, Capabilities: the skills compute their figures
with code. A terminal install does not reach the Claude apps.

### Option 4: clone and copy

```bash
git clone https://github.com/cybooks/skills.git cybooks-skills
cp -r cybooks-skills/skills/cybooks-* ~/.claude/skills/
```

`./build.sh` packages each skill as `dist/<name>.skill` for the Claude
apps.

## Usage

Ask in your own words. Claude picks the skill:

```
"Can we close June? Here are the trial balances for May and June."
→ cybooks-close-readiness-scorecard

"Run the month-end checks on these exports."
→ cybooks-month-end-close

"Screen this general ledger for anything a reviewer would test."
→ cybooks-journal-entry-screen

"Here are all our bills and invoices for Q3. Prepare the VAT return."
→ cybooks-cyprus-vat-return

"Check my Q3 VAT return and give me the XML for TFA."
→ cybooks-cyprus-vat-return
```

In Claude Code a skill can also be called by name, for example
`/cybooks-month-end-close`.

## The skills in detail

### cybooks-month-end-close

Walks a close with a fixed catalogue of 57 checks, each with a stable
code, so this month's report lines up with last month's.

- **Covers:** bank and cash, money in, money out, people and payroll,
  assets and stock, VAT with VIES and the One Stop Shop, the ledger
  itself, related parties and year end.
- **Three depths:** quick, month end (50 of the checks) and year end.
- **You give it:** a trial balance and journal detail. Bank statements,
  aged receivables and payables, and the VAT and payroll workings let more
  checks run.
- **You get:** a close report by area, with an answer for every check and
  a next step for every open item.
- **Good to know:** each check says what it tests, the nearest test from
  files, and what it cannot see even when it passes. The VAT and payroll
  checks are written for Cyprus; the bank, ledger and cut-off checks apply
  anywhere.

### cybooks-journal-entry-screen

Screens the journal entries of a period for the patterns an auditor or a
reviewer tests, and ranks what it finds so the entries worth opening come
first.

- **15 tests:** entries that do not balance, duplicates, entries recorded
  after the close, backdating, clustering at the period end, weekends and
  nights, round amounts, amounts just under an approval limit, first
  digits (Benford, from 500 entries), who keyed the manual entries, rare
  pairings of accounts, manual entries on control accounts, manual credits
  to income, weak descriptions, and reversals.
- **You give it:** a journal or general ledger detail export, as CSV or
  Excel. Each missing column switches off the tests that need it, and the
  report says which.
- **You get:** a ranked list of entries, each with the tests it met and
  what to ask about it.
- **Bundled script:** `scripts/je_screen.py`. A flagged entry is a
  question, never an accusation.

### cybooks-close-readiness-scorecard

Turns "I think we are done" into one page: six dimensions, the same tests
every month, and a verdict.

- **Six dimensions:** bank and cash agree; everything is in; tax and
  payroll tie; movements are explained; the balance sheet makes sense;
  evidence and trail.
- **Verdicts:** Ready to close, Ready with notes, Not yet, or Limited
  read when only one trial balance was given.
- **You give it:** the trial balance at the period end and at the prior
  period end. A general ledger export works too.
- **You get:** a scorecard with every finding tied to an account, the
  movements that need an explanation, and the shortest path to ready.
- **Bundled script:** `scripts/tb_compare.py`.

### cybooks-cyprus-vat-return

Prepares a draft Cyprus VAT return from your bills and invoices, reviews
a return box by box against the Tax Department's guide, and builds the
XML files for upload to Tax For All (TFA): the VAT return and the monthly
VIES statement.

- **A draft from documents:** drop in the period's invoices and bills.
  Claude reads each one into a list, and the script places it in its
  boxes by fixed rules: a sale with VAT, a service to an EU business, a
  purchase under the reverse charge, a supplier's credit note. A document
  the rules cannot place is a question for you, never a guess. VAT that
  cannot be claimed is listed with the reason. The draft is written once
  you have said the documents are complete, because documents cannot
  show what is missing.

- **17 tests on the thirteen boxes,** against each other and against the
  period's VIES statements. For example: box 3 is box 1 plus box 2, box 2
  against 19% of box 11A, box 8B against the services on VIES.
- **12 tests on the lines** behind the return, when you have them. For
  example: reverse charge VAT on a service booked in box 2 where it
  belongs in box 1, a supplier from outside the EU in box 11B, a supplier
  credit note that lowered the purchases but not the VAT.
- **The VIES statement:** built from a list of your EU sales, one row per
  customer VAT number, with a lookup of each number in the EU's VIES
  service.
- **You give it:** your bills and invoices; or the thirteen figures from
  any accounting software, typed or as a file, and a list of EU sales.
- **You get:** a review that quotes the guide for each finding, and the
  files, once nothing that stops them is open.
- **Bundled script:** `scripts/vat_return.py`. It writes no file while a
  test that stops it is open, reads each file back, and tests it against
  the Tax Department's published schema.
- **It does not file anything.** You upload the file yourself. Not
  covered: the One Stop Shop return and payroll returns.

## What every skill holds to

- **Computed, not eyeballed.** Figures come from a script or from code
  over a file you named. If code cannot run, the skill says so and stops.
- **Four answers.** Passed, Needs a look, Could not be checked, Not
  relevant. "Could not be checked" is its own answer and is never counted
  as passed.
- **Two grades of test.** A test that compares figures can pass. A test
  that weighs likelihood can only say Looks right or Worth a look.
- **Read only.** Nothing is posted, changed, closed or filed.
- **A gap is not filled with a guess.** A missing figure is not zero.
- **No assurance words.** A report never says the books are correct,
  compliant, verified or audited.

## Connect Cybooks (optional)

Add a custom connector in Claude with the address
`https://app.cybooks.com.cy/mcp/cybooks` and sign in. The skills then read
the live books, the checks Cybooks already ran and the open to-dos, with
the permissions of the person who signed in. The one thing a skill can
start in Cybooks, and only after you say yes, is a new review run.

## What the skills need

- Code execution, in whichever Claude you use.
- Python 3.9 or later for the bundled scripts. They use the standard
  library only.
- For the VAT return skill: `lxml` or `xmllint` to test a file against the
  schema (it says so when neither is there), and network access to
  `ec.europa.eu` for the VAT number lookup.

## How they were tested

- 82 automated tests of the three bundled scripts:
  `python3 tests/test_scripts.py`.
- Each skill was run end to end by fresh Claude sessions that had only the
  installed skill, the input files and a request. The three close skills
  ran on a real general ledger export of 56,000 lines, the VAT return
  skill on a made-up quarter with mistakes planted in it. It found each
  mistake and built no file until they were fixed.
- Every sentence the VAT return skill quotes from the Tax Department's
  guide was matched against the guide.

Not tested yet: an upload of a built file to TFA, the path that reads live
books from Cybooks, and a run inside the Claude apps. Tell us what you
find.

## What these skills are not

They review what the books show. They are not an audit and not tax advice,
and they cannot see a document that is not in the figures. A VAT return
stays the taxpayer's own: check it with your accountant before you file.

## Contributing

Found a mistake, or a check that should be there?
[Open an issue](https://github.com/cybooks/skills/issues). The skills are
written and reviewed in the Cybooks app repository and copied here, so a
pull request is welcome as a proposal and is carried over by hand.

## In this repository

| | |
|---|---|
| `skills/` | The four skills, one folder each |
| `.claude-plugin/` | The plugin and marketplace files for Claude Code |
| `build.sh` | Packages each skill as `dist/<name>.skill` for the Claude apps |
| `tests/` | The tests of the three bundled scripts |

## Licence

[MIT](LICENSE). Each skill carries its own copy.

`skills/cybooks-cyprus-vat-return/assets/schemas/` holds the XML schemas
the Cyprus Tax Department publishes for these files, unchanged. They are
the Ministry of Finance's and are not covered by the MIT licence.
