# Connected to Cybooks

Use this path when tools named `cybooks_*` are available. The journal is
read from the live books, written to a CSV, and screened by the same script
as an export. This path only reads. It calls no capability that changes
data.

To connect: add the Cybooks connector in Claude with the address
`https://app.cybooks.com.cy/mcp/cybooks` and sign in. Claude can then read
what the signed-in person can read in Cybooks, no more.

## How Cybooks tools are called

The journal tools are capabilities, reached in three steps:

1. `cybooks_search_capabilities` with plain words ("journal lines") finds
   the capability.
2. `cybooks_describe_capability` publishes its arguments. Do this once per
   capability before the first call.
3. `cybooks_read_capability` runs it, with arguments shaped as described,
   usually `{ "query": { ... } }`.

## The steps

**1. Who and what.** `cybooks_auth_status` names the company and the
person's permissions. Reading the journal needs `view_reports`.

**2. Read the entries of the period.** `cybooks_list_journal_entries` with

```json
{ "query": { "filter": { "date_from": "2026-06-01", "date_to": "2026-06-30" }, "per_page": 100 } }
```

Follow `links.next` (pass its cursor) until it is empty. Keep, per entry:
`id`, `date`, `transaction_type`, `reference`, `description`, `created_at`.

**3. Read the lines of the period.** `cybooks_list_journal_lines` with the
same filter, paged the same way. Keep, per line: `journal_entry_id`,
`account.code`, `account.name`, `base_amounts.debit`,
`base_amounts.credit`, `description`. Use `base_amounts`: they are in the
company's own currency.

Page until `links.next` is empty; these reads report no row total. The
check that the file is complete comes from the script: its profile shows
total debits and total credits, and they must be equal. If they are not, a
page is missing; read again before screening. If a `429` comes back, wait
the seconds it names and go on.

**4. Mark the manual entries.** `cybooks_list_manual_journals` lists the
journals a person keyed; each has a `journal_entry_id`. An entry whose id is
in that list is manual. It needs `view_manual_journals`. If it is refused,
say so and run the screen without a source column: the script then treats
all entries alike and says which tests it could not run.

**5. Find when the period was closed.** `cybooks_get_period_lock` returns
the dates up to which the books are closed, and
`cybooks_list_period_lock_history` the moves of that date with their time.
The first move that took the closed date to the period's last day or later
is the close; pass its date as `--closed-on`. Both need
`manage_period_lock`. If refused, ask the person for the date, or leave the
after-close test as not run.

**6. Write the CSV and run the script.** One row per line, with these
headers so no mapping is needed:

```
entry_id,date,account,account_name,debit,credit,description,source,recorded_at
```

`entry_id` is the entry's `id`. Never use `reference` to group lines: a
reversal carries the reference of the entry it reverses, and a bill's
reference is the supplier's own number, so two entries can share one. Keep
`reference` in a column of its own and show it beside the entry in the
report.

`source` is `manual` for the entries from step 4. For every other entry
write `system: ` followed by its `transaction_type`. Do not pass the
`transaction_type` through as it is: Cybooks uses the types "Manual" and
"Journal" for bookings it makes itself (a categorised bank line, a VAT
adjustment), and the script would take them for entries a person keyed.

`recorded_at` is `created_at`. Use the entry's description where a line has
none.

```bash
python3 scripts/je_screen.py journal.csv --manual-values manual \
  --period-start 2026-06-01 --period-end 2026-06-30 --closed-on 2026-07-05
```

For a long period, read month by month and append to the same file.

## What this path cannot test

- **People.** Journal reads carry no "posted by" or "approved by". The
  people tests are reported as not run. Cybooks keeps who did what in its
  audit trail, which is read in the app.
- **Times of day.** `created_at` is in UTC. Cyprus is two or three hours
  ahead. Say so beside any night flag.

## What Cybooks has already worked out

Cybooks' own review runs two of the worked out tests on the live books:
`CB-LDG-03` (no unbalanced or orphaned journal entries) and `CB-LDG-05` (no
unexplained entries were backdated into a closed period). When a review of
the period exists (`cybooks_get_books_review`, see the
`cybooks-month-end-close` skill), show its answer for those two beside the
script's. If the two differ, show both and say they differ. Do not pick
one.

## Rules for this path

- A `403` names a missing permission. Report the step that could not be
  read. Do not look for another route to the same data.
- System entries (invoices, bills, bank bookings, payroll) are part of the
  file and of the profile, but most pattern tests look at manual entries
  only. That is by design.
- Where an entry is flagged, name the screen where it is opened in Cybooks:
  manual journals under Manual journals, everything else from the journal
  report or the document it came from (`source.type` and `source.id` on the
  entry).
- Nothing found here is fixed from here. A correction is made on the
  document or with a new journal, in the open period.
