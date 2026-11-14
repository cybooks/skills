#!/usr/bin/env python3
"""Journal entry screen: runs a fixed battery of tests over a journal export.

Input: a CSV with one row per journal line. Output: JSON on stdout.
Standard library only. Every figure in the report comes from this script;
nothing is estimated.

    python3 je_screen.py lines.csv --period-start 2026-06-01 --period-end 2026-06-30

Columns are found by name (see ALIASES) or mapped by hand:

    --map entry_id="Journal No" --map date="Posting date" --map debit=Dr

Run with --help for every option.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

ALIASES = {
    "entry_id": ["entry_id", "journal_entry_id", "entry", "entry no", "entry number", "journal", "journal no",
                 "journal number", "je", "je number", "transaction id", "voucher", "doc no", "document number"],
    "date": ["date", "entry date", "posting date", "journal date", "effective date", "transaction date"],
    "account": ["account", "account code", "account_code", "account number", "account no", "gl account", "code"],
    "account_name": ["account name", "account_name", "account description", "gl account name", "name", "account title"],
    "debit": ["debit", "dr", "debit amount", "base debit"],
    "credit": ["credit", "cr", "credit amount", "base credit"],
    "amount": ["amount", "net amount", "value", "signed amount"],
    "description": ["description", "memo", "narration", "note", "notes", "reference", "details"],
    "source": ["source", "type", "transaction type", "transaction_type", "entry type", "journal type", "origin"],
    "recorded_at": ["recorded_at", "created_at", "created", "posted at", "posted date", "entered", "entered at",
                    "entry timestamp", "created date"],
    "user": ["user", "posted by", "created by", "entered by", "preparer", "username"],
    "approver": ["approver", "approved by", "authorised by", "authorized by", "reviewer"],
    "counterparty": ["counterparty", "contact", "customer", "supplier", "vendor", "relation", "relation name",
                     "customer name", "supplier name", "payee", "payer"],
}

GENERIC_DESCRIPTIONS = {
    "adjustment", "adj", "adjust", "reclass", "reclassification", "correction", "correct", "fix", "misc",
    "miscellaneous", "journal", "manual journal", "entry", "test", "n/a", "na", "various", "tbc", "other",
    "accrual", "true up", "true-up", "plug", "balancing", "to balance", "see attached",
}

DEFAULT_CONTROL = r"receivable|payable|\bvat\b|output tax|input tax|retained earnings|suspense|clearing|holding|undeposited"
DEFAULT_INCOME = r"revenue|sales|income|turnover|fees earned"
DEFAULT_NOT_INCOME = r"cost of|\btax|deferred|unearned|payable|receivable|accrued"
BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
CHI2_CRITICAL_8DF_05 = 15.507
BENFORD_MIN_POPULATION = 500
CHAIN_WINDOW_DAYS = 21
BATCH_LINES = 12  # an entry with more lines than this is a batch: a bank statement, a pay run


# ---------- parsing ----------

def norm(text: str) -> str:
    return re.sub(r"[\s_\-]+", " ", (text or "").strip().lower())


def resolve_columns(header: list[str], manual: dict[str, str]) -> dict[str, str]:
    by_norm = {norm(h): h for h in header}
    found: dict[str, str] = {}
    for field, column in manual.items():
        if norm(column) not in by_norm:
            sys.exit(f"--map {field}={column}: no such column. Columns: {', '.join(header)}")
        found[field] = by_norm[norm(column)]
    for field, names in ALIASES.items():
        if field in found:
            continue
        for name in names:
            if norm(name) in by_norm and by_norm[norm(name)] not in found.values():
                found[field] = by_norm[norm(name)]
                break
    return found


def detect_decimal(samples: list[str]) -> str:
    comma = sum(1 for s in samples if re.search(r",\d{1,2}\)?\s*$", s))
    point = sum(1 for s in samples if re.search(r"\.\d{1,2}\)?\s*$", s))
    if comma == 0 and point == 0:
        # No decimals anywhere: 135.000 is a hundred and thirty-five thousand, not 135.
        grouped = sum(1 for s in samples if re.fullmatch(r"\s*[-(]?\d{1,3}(\.\d{3})+\)?-?\s*", s))
        other = sum(1 for s in samples if "." in s) - grouped
        return "comma" if grouped and other == 0 else "point"
    return "comma" if comma > point else "point"


def parse_number(raw: str, decimal: str) -> float:
    text = (raw or "").strip()
    if not text or text in {"-", "–"}:
        return 0.0
    negative = text.startswith("(") and text.endswith(")") or text.startswith("-") or text.endswith("-")
    text = re.sub(r"[^\d.,]", "", text)
    if not text:
        return 0.0
    if decimal == "comma":
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        value = float(text)
    except ValueError:
        return 0.0
    return -value if negative else value


def parse_datetime(raw: str, dayfirst: bool) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        pass
    time_part = r"(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?"
    match = re.match(r"^(\d{4})[./](\d{1,2})[./](\d{1,2})" + time_part, text)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    else:
        match = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})" + time_part, text)
        if not match:
            return None
        first, second, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        year += 2000 if year < 100 else 0
        day, month = (first, second) if dayfirst else (second, first)
    try:
        return datetime(year, month, day, int(match.group(4) or 0), int(match.group(5) or 0), int(match.group(6) or 0))
    except ValueError:
        return None


def has_time(raw: str) -> bool:
    return bool(re.search(r"\d{1,2}:\d{2}", raw or ""))


def date_order(values: list[str]) -> tuple[bool, bool]:
    """(some value can only be day first, some value can only be month first)"""
    day_first = month_first = False
    for value in values:
        match = re.match(r"^\s*(\d{1,2})[./-](\d{1,2})[./-]\d{2,4}", value or "")
        if match:
            day_first = day_first or int(match.group(1)) > 12
            month_first = month_first or int(match.group(2)) > 12
    return day_first, month_first


# ---------- helpers ----------

def business_days(start: date, end: date) -> list[date]:
    days, cursor = [], start
    while cursor <= end:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def month_end(day: date) -> date:
    first_next = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first_next - timedelta(days=1)


def percentile(values: list[float], share: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def is_round(amount: float) -> bool:
    return amount >= 1000 and abs(amount / 1000 - round(amount / 1000)) < 1e-9


def money(value: float) -> float:
    return round(value, 2)


# ---------- the screen ----------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", help="CSV, one row per journal line")
    parser.add_argument("--map", action="append", default=[], metavar="FIELD=COLUMN",
                        help="map a field to a column; fields: " + ", ".join(ALIASES))
    parser.add_argument("--period-start", help="first day of the period under review, YYYY-MM-DD")
    parser.add_argument("--period-end", help="last day of the period under review, YYYY-MM-DD")
    parser.add_argument("--closed-on", help="the day the period was closed, YYYY-MM-DD (enables the after-close test)")
    parser.add_argument("--monthfirst", action="store_true", help="read 03/04/2026 as March 4 (default: 3 April)")
    parser.add_argument("--decimal", choices=["auto", "point", "comma"], default="auto")
    parser.add_argument("--materiality", type=float, help="amount floor for the tests that use one "
                                                          "(default: the 75th percentile of entry totals)")
    parser.add_argument("--thresholds", default="", help="approval limits to test just below, e.g. 1000,5000,10000")
    parser.add_argument("--manual-values", default="manual journal,manual,journal,general journal,adjustment",
                        help="values of the source column that mean a person keyed the entry")
    parser.add_argument("--control", default=DEFAULT_CONTROL,
                        help="regex over account code and name: accounts a document should post to, not a manual entry")
    parser.add_argument("--income", default=DEFAULT_INCOME, help="regex over account code and name: income accounts")
    parser.add_argument("--not-income", default=DEFAULT_NOT_INCOME,
                        help="regex: accounts the income pattern matches by accident (cost of sales, income tax)")
    parser.add_argument("--backdate-days", type=int, default=30)
    parser.add_argument("--system-descriptions", default="",
                        help="regex over the description: entries in a manual journal that the system wrote "
                             "(a VAT return posting, a year-end transfer) and that should not count as manual")
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    manual_map = {}
    for pair in args.map:
        if "=" not in pair:
            sys.exit(f"--map {pair}: expected FIELD=COLUMN")
        field, column = pair.split("=", 1)
        if field not in ALIASES:
            sys.exit(f"--map {field}: unknown field. Fields: {', '.join(ALIASES)}")
        manual_map[field] = column

    with open(args.file, newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        header = reader.fieldnames or []
        # A row shorter than the header gives None for its missing cells; a longer one a None key.
        rows = [{key: (value or "") for key, value in row.items() if key is not None} for row in reader]

    cols = resolve_columns(header, manual_map)
    if "date" not in cols or "account" not in cols or not ({"debit", "credit", "amount"} & set(cols)):
        sys.exit("Need at least a date, an account and an amount (debit and credit, or one signed amount). "
                 f"Found: {cols}. Columns: {', '.join(header)}. Use --map.")

    amount_fields = [f for f in ("debit", "credit", "amount") if f in cols]
    samples = [row[cols[f]] for row in rows[:2000] for f in amount_fields if row.get(cols[f])]
    decimal = detect_decimal(samples) if args.decimal == "auto" else args.decimal
    dayfirst, date_order_basis = not args.monthfirst, "given" if args.monthfirst else "default: day first"
    only_day_first, only_month_first = date_order([row.get(cols["date"], "") for row in rows])
    if only_day_first and only_month_first:
        sys.exit("The date column mixes day-first and month-first dates (a value over 12 in both places). "
                 "Clean the dates to YYYY-MM-DD and run again.")
    if only_month_first and not args.monthfirst:
        dayfirst, date_order_basis = False, "detected: a value over 12 in the second place"
    if only_day_first and args.monthfirst:
        sys.exit("--monthfirst was given, but the file has dates that can only be day first.")
    manual_values = {norm(v) for v in args.manual_values.split(",") if v.strip()}
    control_re, income_re = re.compile(args.control, re.I), re.compile(args.income, re.I)
    not_income_re = re.compile(args.not_income, re.I) if args.not_income else None

    def day_arg(value: str | None) -> date | None:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None

    period_start, period_end, closed_on = day_arg(args.period_start), day_arg(args.period_end), day_arg(args.closed_on)

    # ----- lines -> entries -----
    entries: dict[str, dict] = {}
    unreadable_dates, unreadable_examples, carried_down = 0, [], 0
    last_key, last_when = None, None
    for index, row in enumerate(rows):
        raw_date = row.get(cols["date"], "").strip()
        raw_entry = row.get(cols["entry_id"], "").strip() if "entry_id" in cols else ""
        when = parse_datetime(raw_date, dayfirst)
        if when is None and not raw_date and "entry_id" in cols:
            # Exports that print the date and number on an entry's first line only.
            if raw_entry and raw_entry in entries:
                when = datetime.combine(entries[raw_entry]["date"], datetime.min.time())
            elif not raw_entry and last_key is not None:
                raw_entry, when = last_key, last_when
            carried_down += 1 if when is not None else 0
        if when is None:
            unreadable_dates += 1
            if len(unreadable_examples) < 3:
                unreadable_examples.append(raw_date or "(blank)")
            continue
        if "amount" in cols and "debit" not in cols:
            signed = parse_number(row.get(cols["amount"], ""), decimal)
            debit, credit = (signed, 0.0) if signed >= 0 else (0.0, -signed)
        else:
            debit = parse_number(row.get(cols.get("debit", ""), ""), decimal) if "debit" in cols else 0.0
            credit = parse_number(row.get(cols.get("credit", ""), ""), decimal) if "credit" in cols else 0.0
            # A negative debit is a credit, and the other way round.
            debit, credit = max(debit, 0.0) + max(-credit, 0.0), max(credit, 0.0) + max(-debit, 0.0)
        key = raw_entry or f"line-{index + 1}"
        last_key, last_when = (key, when) if "entry_id" in cols else (None, None)
        entry = entries.setdefault(key, {
            "id": key, "date": when.date(), "lines": [], "description": "", "source": None,
            "recorded_at": None, "recorded_has_time": False, "user": None, "approver": None,
            "counterparty": "", "line_dates": set(),
        })
        entry["line_dates"].add(when.date())
        account = row.get(cols["account"], "").strip()
        name = row.get(cols["account_name"], "").strip() if "account_name" in cols else ""
        entry["lines"].append({"account": account, "name": name, "debit": debit, "credit": credit})
        if "description" in cols and len(row.get(cols["description"], "").strip()) > len(entry["description"]):
            entry["description"] = row[cols["description"]].strip()
        if "source" in cols and row.get(cols["source"], "").strip():
            entry["source"] = row[cols["source"]].strip()
        if "recorded_at" in cols and entry["recorded_at"] is None:
            raw = row.get(cols["recorded_at"], "")
            entry["recorded_at"] = parse_datetime(raw, dayfirst)
            entry["recorded_has_time"] = has_time(raw)
        for person in ("user", "approver", "counterparty"):
            if person in cols and row.get(cols[person], "").strip():
                entry[person] = row[cols[person]].strip()

    if unreadable_dates > max(5, len(rows) // 100):
        sys.exit(f"{unreadable_dates} of {len(rows)} lines have a date that cannot be read "
                 f"(for example: {', '.join(unreadable_examples)}). Fix the date column, or map another one "
                 "with --map date=..., and run again. Screening the rest would give wrong results.")
    population = list(entries.values())
    times_are_real = any(e["recorded_at"] and e["recorded_has_time"]
                         and (e["recorded_at"].hour, e["recorded_at"].minute, e["recorded_at"].second) != (0, 0, 0)
                         for e in population)
    if period_start or period_end:
        population = [e for e in population
                      if (not period_start or e["date"] >= period_start) and (not period_end or e["date"] <= period_end)]
    if not population:
        sys.exit("No entries in the period. Check --period-start, --period-end and the date column.")

    grouped = "entry_id" in cols
    knows_manual = "source" in cols
    system_re = re.compile(args.system_descriptions, re.I) if args.system_descriptions else None
    for entry in population:
        entry["debit"] = sum(line["debit"] for line in entry["lines"])
        entry["credit"] = sum(line["credit"] for line in entry["lines"])
        entry["total"] = max(entry["debit"], entry["credit"])
        entry["manual"] = (norm(entry["source"] or "") in manual_values) if knows_manual else None
        if entry["manual"] and system_re and system_re.search(entry["description"]):
            entry["manual"], entry["reclassed"] = False, True
        entry["batch"] = len(entry["lines"]) > BATCH_LINES
        entry["mixed_dates"] = len(entry["line_dates"]) > 1
        net = defaultdict(float)
        for line in entry["lines"]:
            net[line["account"]] += line["debit"] - line["credit"]
        entry["signature"] = tuple(sorted((acc, money(val)) for acc, val in net.items() if abs(val) >= 0.005))
        entry["flags"] = []

    totals = [e["total"] for e in population if e["total"] > 0]
    materiality = args.materiality if args.materiality is not None else money(percentile(totals, 0.75))
    materiality_basis = "given" if args.materiality is not None else "75th percentile of entry totals in the file"
    scope = [e for e in population if e["manual"]] if knows_manual else population
    scope_label = "manual entries" if knows_manual else "all entries (the file does not say which are manual)"

    tests: dict[str, dict] = {}

    def flag(entry: dict, category: str, code: str, detail: str) -> None:
        entry["flags"].append({"category": category, "test": code, "detail": detail})

    def skip(code: str, reason: str) -> None:
        tests[code] = {"status": "skipped", "reason": reason}

    # 1 integrity: balance
    if grouped:
        unbalanced = [e for e in population if abs(e["debit"] - e["credit"]) > 0.005]
        for e in unbalanced:
            flag(e, "integrity", "unbalanced", f"debits {money(e['debit'])} against credits {money(e['credit'])}")
        single = [e for e in population if len(e["lines"]) == 1]
        for e in single:
            flag(e, "integrity", "single_line", "the entry has one line")
        tests["balance"] = {"status": "ran", "grade": "worked_out", "entries": len(population),
                            "unbalanced": len(unbalanced), "single_line": len(single),
                            "difference": money(sum(abs(e["debit"] - e["credit"]) for e in unbalanced))}
    else:
        skip("balance", "no entry number column, so lines cannot be grouped into entries")

    # 2 integrity: duplicates
    if grouped:
        seen = defaultdict(list)
        for e in population:
            if e["signature"] and e["total"] >= materiality:
                seen[(e["date"], e["signature"], norm(e["counterparty"]))].append(e)
        duplicates = [group for group in seen.values() if len(group) > 1]
        for group in duplicates:
            for e in group:
                others = ", ".join(o["id"] for o in group if o is not e)
                flag(e, "integrity", "duplicate", f"same date, accounts and amounts as {others}")
        tests["duplicates"] = {"status": "ran", "grade": "worked_out", "groups": len(duplicates),
                               "entries": sum(len(g) for g in duplicates),
                               "same_counterparty_required": "counterparty" in cols}
    else:
        skip("duplicates", "no entry number column")

    # 3 timing: recorded after the period was closed
    if "recorded_at" not in cols:
        skip("after_close", "no recorded-at column (when the entry was keyed, as opposed to its date)")
    elif not (closed_on and period_end):
        skip("after_close", "needs --period-end and --closed-on (the day the period was closed)")
    else:
        late = [e for e in population if e["recorded_at"] and e["date"] <= period_end and e["recorded_at"].date() > closed_on]
        for e in late:
            flag(e, "timing", "after_close", f"dated {e['date']}, recorded {e['recorded_at'].date()}, "
                                              f"after the close on {closed_on}")
        tests["after_close"] = {"status": "ran", "grade": "worked_out", "entries": len(late),
                                "amount": money(sum(e["total"] for e in late))}

    # 4 timing: backdated
    if "recorded_at" in cols:
        back = [e for e in scope if e["recorded_at"] and (e["recorded_at"].date() - e["date"]).days > args.backdate_days]
        for e in back:
            gap = (e["recorded_at"].date() - e["date"]).days
            flag(e, "timing", "backdated", f"recorded {gap} days after its date")
        tests["backdated"] = {"status": "ran", "grade": "pattern", "population": scope_label,
                              "days": args.backdate_days, "entries": len(back)}
    else:
        skip("backdated", "no recorded-at column")

    # 5 timing: period-end clustering (population signal)
    months = defaultdict(list)
    for e in population:
        months[(e["date"].year, e["date"].month)].append(e)
    cluster_rows, tail_total, norm_total = [], 0.0, 0.0
    for (year, month), items in sorted(months.items()):
        end = month_end(date(year, month, 1))
        days = business_days(date(year, month, 1), end)
        if len(days) < 5 or len(items) < 20:
            continue
        tail = set(days[-2:])
        in_tail = [e for e in items if e["date"] in tail or e["date"] > days[-1]]
        daily_norm = len(items) / len(days)
        ratio = (len(in_tail) / 2) / daily_norm if daily_norm else 0.0
        cluster_rows.append({"month": f"{year}-{month:02d}", "entries": len(items), "last_two_days": len(in_tail),
                             "share": round(len(in_tail) / len(items), 4), "times_daily_norm": round(ratio, 2)})
        tail_total += len(in_tail) / 2
        norm_total += daily_norm
        if ratio > 3:
            for e in in_tail:
                if e["manual"] or not knows_manual:
                    flag(e, "timing", "period_end", f"in the last two working days of {year}-{month:02d}")
    if cluster_rows:
        overall = round(tail_total / norm_total, 2) if norm_total else 0.0
        tests["period_end"] = {"status": "ran", "grade": "pattern", "months": cluster_rows,
                               "times_daily_norm": overall, "signal": overall > 3}
    else:
        skip("period_end", "no month in the file has 20 or more entries")

    # 6 timing: weekend and night
    weekend, night, month_end_skipped = [], [], 0
    for e in scope:
        stamp = e["recorded_at"] or datetime.combine(e["date"], datetime.min.time())
        if not e["recorded_at"] and stamp.weekday() >= 5 and e["date"] == month_end(e["date"]):
            # An entry dated the last day of a month says nothing about when it was keyed.
            month_end_skipped += 1
            continue
        if stamp.weekday() >= 5:
            weekend.append(e)
            flag(e, "timing", "weekend", f"{'recorded' if e['recorded_at'] else 'dated'} on a {stamp.strftime('%A')}")
        if e["recorded_at"] and times_are_real and e["recorded_has_time"] and (stamp.hour < 6 or stamp.hour >= 22):
            night.append(e)
            flag(e, "timing", "night", f"recorded at {stamp.strftime('%H:%M')}")
    tests["weekend_night"] = {"status": "ran", "grade": "pattern", "population": scope_label,
                              "basis": "recorded-at" if "recorded_at" in cols else "entry date (no recorded-at column)",
                              "weekend": len(weekend),
                              "month_end_dates_left_out": month_end_skipped if "recorded_at" not in cols else None,
                              "night": len(night) if times_are_real else None,
                              "night_note": None if times_are_real else "no time of day in the file"}

    # 7 amounts: round numbers
    round_all = [e for e in population if is_round(e["total"])]
    round_scope = [e for e in scope if is_round(e["total"])]
    for e in round_scope:
        flag(e, "amounts", "round", f"exactly {money(e['total'])}")
    tests["round"] = {"status": "ran", "grade": "pattern", "population": scope_label,
                      "rate": round(len(round_scope) / len(scope), 4) if scope else None,
                      "rate_all_entries": round(len(round_all) / len(population), 4), "entries": len(round_scope)}

    # 8 amounts: just below an approval limit
    limits = [float(t) for t in args.thresholds.split(",") if t.strip()]
    if limits:
        below = {}
        for limit in limits:
            hits = [e for e in scope if limit * 0.98 <= e["total"] < limit]
            below[str(int(limit) if limit == int(limit) else limit)] = len(hits)
            if len(hits) >= 3:
                for e in hits:
                    flag(e, "amounts", "below_limit", f"{money(e['total'])}, just under {money(limit)}")
        tests["below_limit"] = {"status": "ran", "grade": "pattern", "population": scope_label, "counts": below,
                                "note": "entries are flagged only where three or more sit under one limit"}
    else:
        skip("below_limit", "no approval limits given (--thresholds)")

    # 9 amounts: first digits (population signal only)
    recurring = Counter()
    for e in population:
        for line in e["lines"]:
            recurring[(line["account"], money(max(line["debit"], line["credit"])))] += 1
    qualifying = []
    for e in population:
        if e["total"] < 10:
            continue
        biggest = max(e["lines"], key=lambda line: max(line["debit"], line["credit"]))
        if recurring[(biggest["account"], money(max(biggest["debit"], biggest["credit"])))] >= 6:
            continue
        qualifying.append(e["total"])
    if len(qualifying) < BENFORD_MIN_POPULATION:
        skip("first_digits", f"{len(qualifying)} qualifying entries; the test needs {BENFORD_MIN_POPULATION} "
                             "or more to mean anything")
    else:
        digits = Counter(int(f"{value:.6e}"[0]) for value in qualifying)
        count = len(qualifying)
        observed = {d: digits.get(d, 0) / count for d in range(1, 10)}
        mad = sum(abs(observed[d] - BENFORD[d]) for d in range(1, 10)) / 9
        chi2 = sum((digits.get(d, 0) - count * BENFORD[d]) ** 2 / (count * BENFORD[d]) for d in range(1, 10))
        excess = sorted(range(1, 10), key=lambda d: observed[d] - BENFORD[d], reverse=True)[:2]
        tests["first_digits"] = {
            "status": "ran", "grade": "pattern", "qualifying": count, "excluded": len(population) - count,
            "mad": round(mad, 5), "chi_square": round(chi2, 2), "chi_square_critical": CHI2_CRITICAL_8DF_05,
            "signal": mad > 0.015 and chi2 > CHI2_CRITICAL_8DF_05,
            "digits_above_expected": [{"digit": d, "observed": round(observed[d], 4), "expected": round(BENFORD[d], 4)}
                                      for d in excess],
            "note": "a population signal: it points at a digit range to sample, never at one entry",
        }

    # 10 people
    if "user" in cols:
        by_user_amount, by_user_count = Counter(), Counter()
        for e in scope:
            by_user_amount[e["user"] or "(blank)"] += e["total"]
            by_user_count[e["user"] or "(blank)"] += 1
        total_amount = sum(by_user_amount.values()) or 1.0
        top_user, top_amount = by_user_amount.most_common(1)[0] if by_user_amount else ("", 0.0)
        rare = [e for e in scope if by_user_count[e["user"] or "(blank)"] < 5 and e["total"] >= materiality]
        for e in rare:
            flag(e, "people", "rare_poster", f"{e['user'] or '(blank)'} keyed "
                                             f"{by_user_count[e['user'] or '(blank)']} entries in the file")
        result = {"status": "ran", "grade": "pattern", "population": scope_label, "users": len(by_user_count),
                  "top_user": top_user, "top_user_share_of_amount": round(top_amount / total_amount, 4),
                  "rare_poster_entries": len(rare),
                  "one_person": len(by_user_count) == 1}
        if "approver" in cols:
            same = [e for e in scope if e["user"] and e["approver"] and norm(e["user"]) == norm(e["approver"])]
            for e in same:
                flag(e, "people", "self_approved", f"keyed and approved by {e['user']}")
            result["self_approved"] = len(same)
        else:
            result["self_approved"] = None
        tests["people"] = result
    else:
        skip("people", "no posted-by column")

    # 11 accounts: rare pairings
    if grouped:
        def dominant_pair(entry: dict) -> tuple[str, str] | None:
            debits = [line for line in entry["lines"] if line["debit"] > 0]
            credits = [line for line in entry["lines"] if line["credit"] > 0]
            if not debits or not credits:
                return None
            debit_account = max(debits, key=lambda line: line["debit"])["account"]
            others = [line for line in credits if line["account"] != debit_account]
            if not others:
                return None
            return (debit_account, max(others, key=lambda line: line["credit"])["account"])
        pairs = Counter()
        for e in population:
            e["pair"] = dominant_pair(e)
            if e["pair"]:
                pairs[e["pair"]] += 1
        rare_pairs = [e for e in scope if e.get("pair") and not e["batch"] and pairs[e["pair"]] <= 2
                      and e["total"] >= materiality]
        for e in rare_pairs:
            flag(e, "accounts", "rare_pairing", f"{e['pair'][0]} against {e['pair'][1]} appears "
                                                f"{pairs[e['pair']]} time(s) in the file")
        tests["rare_pairing"] = {"status": "ran", "grade": "pattern", "population": scope_label,
                                 "distinct_pairs_in_the_whole_file": len(pairs), "entries": len(rare_pairs)}
    else:
        skip("rare_pairing", "no entry number column")

    # 12 accounts: manual entries on control accounts and income
    if knows_manual:
        control, income = [], []
        for e in scope:
            hit = max((line for line in e["lines"] if control_re.search(f"{line['account']} {line['name']}")),
                      key=lambda line: max(line["debit"], line["credit"]), default=None)
            if hit:
                control.append(e)
                flag(e, "accounts", "control_account", f"a manual entry on {hit['account']} {hit['name']}".strip())
            earned = max((line for line in e["lines"] if line["credit"] > 0
                          and income_re.search(f"{line['account']} {line['name']}")
                          and not (not_income_re and not_income_re.search(f"{line['account']} {line['name']}"))),
                         key=lambda line: line["credit"], default=None)
            if earned:
                income.append(e)
                flag(e, "accounts", "manual_income", f"a manual credit to {earned['account']} {earned['name']}".strip())
        tests["control_accounts"] = {"status": "ran", "grade": "pattern", "entries": len(control),
                                     "amount": money(sum(e["total"] for e in control))}
        tests["manual_income"] = {"status": "ran", "grade": "pattern", "entries": len(income),
                                  "amount": money(sum(e["total"] for e in income))}
    else:
        skip("control_accounts", "no source column, so manual entries cannot be told from system entries")
        skip("manual_income", "no source column, so manual entries cannot be told from system entries")

    # 13 descriptions
    if "description" in cols:
        weak = []
        for e in scope:
            text = norm(e["description"])
            if e["total"] >= materiality and (len(text) < 4 or text in GENERIC_DESCRIPTIONS):
                weak.append(e)
                flag(e, "descriptions", "weak_description", f"description: \"{e['description']}\"" if text else "no description")
        tests["descriptions"] = {"status": "ran", "grade": "pattern", "population": scope_label, "entries": len(weak)}
    else:
        skip("descriptions", "no description column")

    # 14 reversals
    if grouped:
        by_signature = defaultdict(list)
        for e in population:
            # The net of a batch (a whole bank statement) is not the shape of one posting.
            # ... and neither is an entry that moves money in and out of the same account.
            one_way = abs(sum(abs(val) for _, val in e["signature"]) / 2 - e["total"]) < 0.01
            if e["signature"] and not e["batch"] and one_way:
                by_signature[(e["signature"], norm(e["counterparty"]))].append(e)
        handled, pairs_found, chains, cross = set(), 0, 0, 0
        for (shape, party), originals in by_signature.items():
            signature = (shape, party)
            mirror = (tuple(sorted((acc, money(-val)) for acc, val in shape)), party)
            if mirror not in by_signature or signature in handled or mirror in handled:
                continue
            handled.update({signature, mirror})
            mirrors = by_signature[mirror]
            if max(e["total"] for e in originals + mirrors) < materiality:
                continue

            def near(entry: dict, others: list[dict]) -> bool:
                return any(abs((entry["date"] - other["date"]).days) <= CHAIN_WINDOW_DAYS for other in others)

            # Identical postings that recur (a monthly fee) are not part of a chain: keep only
            # the entries that have an opposite entry close by.
            close = sorted([e for e in originals if near(e, mirrors)] + [e for e in mirrors if near(e, originals)],
                           key=lambda e: e["date"])
            if len(close) >= 3:
                chains += 1
                ids = ", ".join(e["id"] for e in close)
                for e in close:
                    flag(e, "reversals", "reversal_chain", f"posted and reversed {len(close)} times: {ids}")
                continue
            if len(close) == 2:
                group = close
            else:
                first = min(mirrors if len(mirrors) <= len(originals) else originals, key=lambda e: e["date"])
                opposite = originals if first in mirrors else mirrors
                group = sorted([first, min(opposite, key=lambda e: abs((e["date"] - first["date"]).days))],
                               key=lambda e: e["date"])
            pairs_found += 1
            if len({(e["date"].year, e["date"].month) for e in group}) > 1:
                cross += 1
                ids = ", ".join(e["id"] for e in group)
                for e in group:
                    flag(e, "reversals", "reversal_across_months", f"reversed in another month: {ids}")
        tests["reversals"] = {"status": "ran", "grade": "pattern", "pairs": pairs_found,
                              "pairs_across_months": cross, "chains": chains,
                              "note": "a pair inside one month is counted, not flagged"}
    else:
        skip("reversals", "no entry number column")

    # ----- scoring -----
    flagged = [e for e in population if e["flags"]]
    for e in flagged:
        e["categories"] = sorted({f["category"] for f in e["flags"]})
    flagged.sort(key=lambda e: ("integrity" in e["categories"], e["total"] >= materiality, len(e["categories"]),
                                len(e["flags"]), e["total"]), reverse=True)

    def present(entry: dict) -> dict:
        debits = sorted((l for l in entry["lines"] if l["debit"] > 0), key=lambda l: -l["debit"])
        credits = sorted((l for l in entry["lines"] if l["credit"] > 0), key=lambda l: -l["credit"])
        return {
            "entry": entry["id"], "date": entry["date"].isoformat(), "amount": money(entry["total"]),
            "debit_accounts": [f"{l['account']} {l['name']}".strip() for l in debits[:3]],
            "credit_accounts": [f"{l['account']} {l['name']}".strip() for l in credits[:3]],
            "description": entry["description"], "source": entry["source"], "user": entry["user"],
            "counterparty": entry["counterparty"] or None,
            "lines": len(entry["lines"]), "batch": entry["batch"],
            "categories": entry["categories"], "flags": entry["flags"],
        }

    def by_test(entries: list[dict]) -> dict:
        summary = defaultdict(lambda: {"entries": 0, "amount": 0.0})
        for e in entries:
            for code in {f["test"] for f in e["flags"]}:
                summary[code]["entries"] += 1
                summary[code]["amount"] = money(summary[code]["amount"] + e["total"])
        return dict(sorted(summary.items(), key=lambda item: -item[1]["entries"]))

    dates = [e["date"] for e in population]
    report = {
        "profile": {
            "file": args.file, "lines_read": len(rows), "lines_with_unreadable_date": unreadable_dates,
            "entries": len(population), "grouped_into_entries": grouped,
            "date_from": min(dates).isoformat(), "date_to": max(dates).isoformat(),
            "period": {"from": args.period_start, "to": args.period_end, "closed_on": args.closed_on},
            "manual_entries": len(scope) if knows_manual else None,
            "system_entries": len(population) - len(scope) if knows_manual else None,
            "sources": dict(Counter(e["source"] or "(blank)" for e in population).most_common(12)) if knows_manual else None,
            "users": len({e["user"] for e in population if e["user"]}) if "user" in cols else None,
            "total_debits": money(sum(e["debit"] for e in population)),
            "total_credits": money(sum(e["credit"] for e in population)),
            "batch_entries": sum(1 for e in population if e["batch"]),
            "batch_note": f"entries with more than {BATCH_LINES} lines (a bank statement, a pay run); their amount is "
                          "the gross of all lines, and they are left out of the pairing and reversal tests",
            "entries_with_more_than_one_date": sum(1 for e in population if e["mixed_dates"]),
            "entries_with_more_than_one_date_ids": [e["id"] for e in population if e["mixed_dates"]][:20],
            "manual_entries_counted_as_system": sum(1 for e in population if e.get("reclassed")),
            "largest_counted_as_system": [
                {"entry": e["id"], "date": e["date"].isoformat(), "amount": money(e["total"]),
                 "description": e["description"]}
                for e in sorted((e for e in population if e.get("reclassed")), key=lambda e: -e["total"])[:10]],
            "columns_used": cols, "fields_missing": [f for f in ALIASES if f not in cols],
            "decimal_mark": decimal, "day_first_dates": dayfirst, "date_order_basis": date_order_basis,
            "lines_that_took_the_date_of_the_line_above": carried_down,
        },
        "settings": {"materiality": materiality, "materiality_basis": materiality_basis,
                     "manual_values": sorted(manual_values), "control_regex": args.control, "income_regex": args.income,
                     "not_income_regex": args.not_income or None,
                     "system_descriptions_regex": args.system_descriptions or None},
        "tests": tests,
        "tests_ran": sum(1 for t in tests.values() if t["status"] == "ran"),
        "tests_skipped": {code: t["reason"] for code, t in tests.items() if t["status"] == "skipped"},
        "flagged_total": len(flagged),
        "flagged": [present(e) for e in flagged[: args.top]],
        "by_test": by_test(flagged),
        "beyond_the_list_by_test": by_test(flagged[args.top:]),
    }
    json.dump(report, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
