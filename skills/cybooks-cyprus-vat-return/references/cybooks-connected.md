# Connected to Cybooks

Use this path when tools named `cybooks_*` are available. Cybooks then
holds the return: it works the boxes out from the books, and it builds and
schema-tests the file for the portal itself. Your job is to read the
return, run the tests of this skill on its figures, and say what stands
between the return and filing. This path only reads. It calls no
capability that changes data.

To connect: add the Cybooks connector in Claude with the address
`https://app.cybooks.com.cy/mcp/cybooks` and sign in. Claude can then read
what the signed-in person can read in Cybooks, no more.

## How Cybooks tools are called

A few tools are listed directly (`cybooks_get_customer`,
`cybooks_get_vendor`). The rest are capabilities, reached in three steps:

1. `cybooks_search_capabilities` with plain words ("VAT return") finds the
   capability.
2. `cybooks_describe_capability` publishes its arguments. Do this once per
   capability before the first call.
3. `cybooks_read_capability` runs a read. A return's `id` sits beside
   `query`, not inside it: `{ "id": "...", "query": { ... } }`.

## The steps

**1. Who and what.** `cybooks_auth_status` names the company and the
person's permissions. Reading a return needs `view_vat_returns`.

**2. Find the return.** `cybooks_list_vat_returns` with

```json
{ "query": { "tax_type": "ADDED_TAX", "year": 2026 } }
```

`tax_type` is `ADDED_TAX` for VAT returns and `VIES` for VIES statements.
`year` is the year the period ends in. Each row has `id`, `period_start`,
`period_end`, `status` (`draft` or `completed`), `filed`, `period_filed`,
`period_running`, `due_date`, `overdue` and `currency`. Pick the row whose
period the person means; if two could be meant, ask.

**3. Read it.** `cybooks_get_vat_return` with the `id`. It returns:

- `vat_return`: the same summary as a row of step 2 (`filed`,
  `period_running`, `due_date` and the rest are inside it).
- `boxes[]`: thirteen rows with `slug` (`box-1` to `box-11b`), `name` and
  `amount`, a number. Box 5 positive is payable, negative is a credit.
- `figures_source`: `filed` (the figures as they were filed) or `computed`
  (worked out from the books now).
- `net_vat`: `position` (`owe`, `refund` or `zero`) and the amount.
- `adjustments[]`: manual adjustments to a box, each with its `box`,
  `amount` and `reason`. List every one in the report.
- `transactions[]`: the lines behind the boxes, paged (`page`, `per_page`
  up to 200, `last_page`, `total_rows`). `query.box` narrows them to one
  box (`box-1`, `box-8b`, ...; not `box-3` or `box-5`, which are sums).
- `recompute_error`: when set, say the figures could not be worked out
  again and why.

**4. The VIES statements of the period, for VR-10 and VR-11.**
`cybooks_list_vat_returns` with `tax_type: "VIES"` lists the monthly
statements. Read each month of the period with `cybooks_get_vat_return`:
`vies-box-1` is the number of rows, `vies-box-2` goods, `vies-box-3`
triangular, `vies-box-4` services, in whole euros. A month with no
statement in Cybooks is "not read", not nil: leave it out, and the two
tests will say Could not be checked and name it.

**5. Run the tests on the figures.** Save the `boxes` list as Cybooks
returned it to a JSON file (`{"boxes": [...]}`) and run:

```bash
python3 scripts/vat_return.py check --taxpayer 12345678X \
  --from 2026-07-01 --to 2026-09-30 --boxes boxes.json \
  --vies "2026-07:goods=0,triangular=0,services=4301,rows=2" \
  --vies "2026-08:goods=0,triangular=0,services=3160,rows=2" \
  --vies "2026-09:goods=3200,triangular=0,services=5901,rows=3"
```

`--from` and `--to` are `period_start` and `period_end`. The taxpayer
number is `vat_id` from `cybooks_get_company` (needs `view_companies`); if
that is refused, ask the person. Use `check`, not `xml`: see step 8. If
`currency` is not `EUR`, say so and stop: the return is filed in euros.

Cybooks reports triangular sales with the goods of box 8A. Where VR-10
says box 8A agrees once the triangular column is added, that is why: show
the answer as the script gives it and say so.

**6. The lines, for the tests in `boxes.md` section 4.** Page through
`transactions[]`. Each line has `date`, `box_slug`, `contact`,
`document_number`, `tax_rule`, `country_code`, `tax_rate`, `net`, `vat`
and `gross`. A line with `is_reclaim: true` is the input side of a reverse
charge, shown for reading: do not add it to a box total twice. Lines do
not carry the supplier's or customer's VAT number; read it from the
contact (`cybooks_get_customer`, `cybooks_get_vendor`; they need
`view_customers` and `view_vendors`) only for the lines a test puts in
question.

**7. What is waiting.**

- `cybooks_get_vat_return_customs` returns import VAT that is not in box 4
  yet, grouped by what it waits for (`held_total`, `held_count`). Name the
  amount and the reason; it is a figure the person may expect in the
  return.
- `cybooks_get_vat_return_deadlines` lists the returns still to file, the
  earliest first, with `due_date` and `overdue`.

**8. The file comes from Cybooks.** Do not build a second file for a
return that lives in Cybooks. Cybooks builds the VAT return file and the
VIES file from the same figures and tests each against the Tax
Department's schema. The person downloads it on the return's page in
Cybooks with **Download TFA XML**, uploads it to Tax For All, and records
the outcome there (**I uploaded it to Tax For All**, then **Accepted** or
**Rejected**). The button is there when the company files by XML upload;
with filing by hand, Cybooks shows **Copy filing sheet** in its place.
The connector cannot download the file.

Build a file with this skill only when the person says the return is kept
outside Cybooks, and then from their figures, not from these.

## What Cybooks has already worked out

Cybooks derives boxes 3 and 5 itself, so VR-04 and VR-05 pass by
construction. Its own review runs checks on VAT, VIES and the One Stop
Shop (codes `CB-VAT`, `CB-VIE`, `CB-OSS`). `cybooks_get_books_review`
reads it; the `cybooks-month-end-close` skill says how. When a review of
the period exists, show its answers beside this skill's. If the two differ
on the same question, show both and say they differ. Do not pick one.

## Rules for this path

- **Read only.** Never call `cybooks_adjust_vat_return_box`,
  `cybooks_remove_vat_return_adjustment`, either of their previews
  (`cybooks_preview_vat_return_adjustment`,
  `cybooks_preview_vat_return_adjustment_removal`), or the import VAT
  capabilities that claim or undo a claim. If a figure needs to change,
  name the document or the box and say it is changed in Cybooks, by a
  person.
- **A figure in the report is what Cybooks returned.** Do not correct,
  round or re-derive it. If a test of this skill disagrees with it, that
  is the finding.
- **A filed return is a look back.** When `vat_return.filed` is true or
  `figures_source` is `filed`, say so at the top. Nothing found is fixed
  in that return: a correction goes into the open period, and Cybooks
  routes it there.
- **A running period is not final.** When `vat_return.period_running` is
  true, say the figures will still move.
- **A refusal is an answer.** A `403` names a missing permission. The code
  `vat_return_filing_rate_missing` means some entries have no euro rate
  yet, so Cybooks will not show the draft: say so, and that it is resolved
  in Cybooks. Do not look for another route to the same data.
- **Rate limits.** A `429` carries the seconds to wait. Wait, then go on.
- **Filing is the person's act.** No capability files a return or marks
  one as filed.
