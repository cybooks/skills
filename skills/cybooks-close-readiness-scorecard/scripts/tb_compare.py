#!/usr/bin/env python3
"""Trial balance comparison: the figures behind a close readiness scorecard.

Input: a trial balance CSV for the period end, and ideally one for the prior
period end. Output: JSON on stdout. Standard library only. Every figure in the
scorecard comes from this script; nothing is estimated.

    python3 tb_compare.py --current tb-june.csv --prior tb-may.csv --prior-months 5

Columns are found by name (see ALIASES) or mapped by hand:

    --map code="Account No" --map balance="Closing balance"

A balance column is read as debit positive, credit negative. Run with --help
for every option.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys

ALIASES = {
    "code": ["code", "account code", "account_code", "account number", "account no", "gl account", "account"],
    "name": ["name", "account name", "account_name", "account description", "description", "account", "title"],
    "class": ["class", "type", "account type", "account class", "category", "section"],
    "debit": ["debit", "dr", "debit balance", "closing debit"],
    "credit": ["credit", "cr", "credit balance", "closing credit"],
    "balance": ["balance", "closing balance", "net", "amount", "net balance"],
}

# Tried in this order: the first that matches wins. Equity before assets ("Stockholders equity"),
# liabilities before income ("Deferred income"), expenses before income ("Cost of sales", "Income tax").
CLASS_WORDS = [
    ("equity", r"equity|capital|retained|reserves?\b"),
    ("liability", r"liabilit|payable|creditor|loan|borrowing|accru|provision|deferred (income|revenue)|unearned"),
    ("expense", r"expense|cost|overhead|purchases|\btax"),
    ("income", r"income|revenue|sales|turnover"),
    ("asset", r"asset|bank|cash|receivable|debtor|inventory|stock|prepaid|prepayment"),
]
DEFAULT_HOLDING = r"suspense|clearing|(?<!with)holding|undeposited|unallocated|ask my accountant|uncategori[sz]ed"
DEFAULT_ACCRUAL = r"accru|prepaid|prepayment|provision|deferred"
DEFAULT_CONTRA = r"accumulated|depreciation|amorti[sz]ation|allowance|impairment|provision for|drawings|treasury"
DEFAULT_RETAINED = r"retained earnings|retained profit|accumulated profit|profit and loss reserve"
DEFAULT_BANK = r"bank|cash"
DEFAULT_STOCK = r"stock|inventory|work in progress"


def norm(text: str) -> str:
    return re.sub(r"[\s_\-]+", " ", (text or "").strip().lower())


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
    text = text.replace(".", "").replace(",", ".") if decimal == "comma" else text.replace(",", "")
    try:
        value = float(text)
    except ValueError:
        return 0.0
    return -value if negative else value


def classify(raw: str) -> str | None:
    text = norm(raw)
    for label, pattern in CLASS_WORDS:
        if re.search(pattern, text):
            return label
    return None


def load(path: str, manual: dict[str, str], decimal_arg: str) -> tuple[dict[str, dict], dict]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
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
    by_norm = {norm(h): h for h in header}
    cols: dict[str, str] = {}
    for field, column in manual.items():
        if norm(column) not in by_norm:
            sys.exit(f"--map {field}={column}: no such column in {path}. Columns: {', '.join(header)}")
        cols[field] = by_norm[norm(column)]
    for field, names in ALIASES.items():
        if field in cols:
            continue
        for name in names:
            if norm(name) in by_norm and by_norm[norm(name)] not in cols.values():
                cols[field] = by_norm[norm(name)]
                break
    if "code" not in cols and "name" not in cols:
        sys.exit(f"{path}: need an account code or name column. Columns: {', '.join(header)}. Use --map.")
    if not ({"debit", "credit", "balance"} & set(cols)):
        sys.exit(f"{path}: need debit and credit columns, or one balance column. Columns: {', '.join(header)}. Use --map.")
    amount_cols = [cols[f] for f in ("debit", "credit", "balance") if f in cols]
    samples = [row[c] for row in rows[:2000] for c in amount_cols if row.get(c)]
    decimal = detect_decimal(samples) if decimal_arg == "auto" else decimal_arg

    accounts: dict[str, dict] = {}
    for row in rows:
        code = row.get(cols.get("code", ""), "").strip() if "code" in cols else ""
        name = row.get(cols.get("name", ""), "").strip() if "name" in cols else ""
        key = code or name
        if not key or norm(key).startswith("total"):
            continue
        if "debit" in cols or "credit" in cols:
            debit = parse_number(row.get(cols.get("debit", ""), ""), decimal) if "debit" in cols else 0.0
            credit = parse_number(row.get(cols.get("credit", ""), ""), decimal) if "credit" in cols else 0.0
            balance = debit - credit
        else:
            balance = parse_number(row.get(cols["balance"], ""), decimal)
        entry = accounts.setdefault(key, {"code": code, "name": name, "class": None, "balance": 0.0})
        entry["balance"] = round(entry["balance"] + balance, 2)
        if "class" in cols and entry["class"] is None:
            entry["class"] = classify(row.get(cols["class"], ""))
    return accounts, {"file": path, "rows": len(rows), "accounts": len(accounts), "columns_used": cols,
                      "has_class": "class" in cols, "decimal_mark": decimal}


def label(account: dict) -> str:
    return f"{account['code']} {account['name']}".strip()


def is_round(amount: float) -> bool:
    amount = abs(amount)
    return amount >= 1000 and abs(amount / 1000 - round(amount / 1000)) < 1e-9


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--current", required=True, help="trial balance at the period end (CSV)")
    parser.add_argument("--prior", help="trial balance at the prior period end (CSV)")
    parser.add_argument("--map", action="append", default=[], metavar="FIELD=COLUMN",
                        help="map a field to a column; fields: " + ", ".join(ALIASES))
    parser.add_argument("--decimal", choices=["auto", "point", "comma"], default="auto")
    parser.add_argument("--percent", type=float, default=10.0, help="movement test: percent change (default 10)")
    parser.add_argument("--floor", type=float, help="movement test: amount floor "
                                                    "(default 0.5%% of income, else 0.5%% of expenses, else 0.25%% of total debits)")
    parser.add_argument("--prior-months", type=int,
                        help="months of the financial year covered by the prior trial balance; lets income and "
                             "expense movements be compared with the monthly run rate")
    parser.add_argument("--holding", default=DEFAULT_HOLDING,
                        help="regex over account code and name: holding, suspense and clearing accounts. "
                             "Replace it for a chart that is not in English.")
    parser.add_argument("--accrual", default=DEFAULT_ACCRUAL,
                        help="regex over account code and name: accruals, prepayments and provisions")
    parser.add_argument("--contra", default=DEFAULT_CONTRA,
                        help="regex: accounts that are meant to sit on the other side (accumulated depreciation)")
    parser.add_argument("--retained", default=DEFAULT_RETAINED, help="regex: the retained earnings account")
    parser.add_argument("--bank", default=DEFAULT_BANK, help="regex: bank, cash and payment provider accounts")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="regex: stock and inventory accounts")
    parser.add_argument("--income", help="regex over 'code name': income accounts, for a file with no class column "
                                         "(for example '^4' or '^8\\d{4} ')")
    parser.add_argument("--expense", help="regex over 'code name': expense accounts, for a file with no class column")
    parser.add_argument("--top", type=int, default=40)
    args = parser.parse_args()
    HOLDING, ACCRUAL = re.compile(args.holding, re.I), re.compile(args.accrual, re.I)
    CONTRA, RETAINED, BANK = re.compile(args.contra, re.I), re.compile(args.retained, re.I), re.compile(args.bank, re.I)
    STOCK = re.compile(args.stock, re.I)

    manual = {}
    for pair in args.map:
        if "=" not in pair or pair.split("=", 1)[0] not in ALIASES:
            sys.exit(f"--map {pair}: expected FIELD=COLUMN with a field of: {', '.join(ALIASES)}")
        field, column = pair.split("=", 1)
        manual[field] = column

    current, current_info = load(args.current, manual, args.decimal)
    prior, prior_info = load(args.prior, manual, args.decimal) if args.prior else ({}, None)
    has_class = current_info["has_class"]
    for key, account in current.items():
        if account["class"] is None and key in prior:
            account["class"] = prior[key]["class"]
    # Without a class column the script cannot tell a sales account from a bank account, unless told.
    by_pattern = [(kind, re.compile(pattern, re.I)) for kind, pattern in (("income", args.income), ("expense", args.expense))
                  if pattern]
    for accounts in (current, prior):
        for account in accounts.values():
            if account["class"] is None:
                account["class"] = next((kind for kind, regex in by_pattern if regex.search(label(account))), None)
    knows_income_and_expense = has_class or len(by_pattern) == 2

    total_debit = round(sum(a["balance"] for a in current.values() if a["balance"] > 0), 2)
    total_credit = round(-sum(a["balance"] for a in current.values() if a["balance"] < 0), 2)
    income = round(-sum(a["balance"] for a in current.values() if a["class"] == "income"), 2)
    expenses = round(sum(a["balance"] for a in current.values() if a["class"] == "expense"), 2)

    if args.floor is not None:
        floor, floor_basis = args.floor, "given"
    elif income > 0:
        floor, floor_basis = round(income * 0.005, 2), "0.5% of income to date"
    elif expenses > 0:
        floor, floor_basis = round(expenses * 0.005, 2), "0.5% of expenses to date (no income found)"
    else:
        floor, floor_basis = round(total_debit * 0.0025, 2), "0.25% of total debits (no account classes in the file)"

    findings: dict[str, list] = {key: [] for key in (
        "holding_accounts", "wrong_side", "round_balances", "movements", "unchanged", "went_quiet",
        "new_accounts", "emptied_accounts", "retained_earnings")}

    for account in current.values():
        balance, text = account["balance"], label(account)
        balance_sheet = account["class"] not in ("income", "expense")
        if HOLDING.search(text) and balance_sheet and abs(balance) >= 0.005:
            # An account that is not in the prior file had no balance then.
            before = prior.get(account["code"] or account["name"], {}).get("balance", 0.0) if prior else None
            findings["holding_accounts"].append({
                "account": text, "balance": balance, "prior": before,
                "grew": (abs(balance) > abs(before)) if before is not None else None,
                "changed_side": (balance * before < 0) if before is not None else None})
        if has_class and abs(balance) >= 1:
            wrong = ((account["class"] == "asset" and balance < 0) or (account["class"] == "liability" and balance > 0)
                     or (account["class"] == "income" and balance > 0) or (account["class"] == "expense" and balance < 0))
            if wrong:
                findings["wrong_side"].append({
                    "account": text, "class": account["class"], "balance": balance,
                    "looks_like_contra_account": bool(CONTRA.search(text)), "material": abs(balance) >= floor})
        if ACCRUAL.search(text) and balance_sheet and is_round(balance):
            findings["round_balances"].append({"account": text, "balance": balance})

    months_note = None
    if prior:
        keys = set(current) | set(prior)
        income_down = 0
        income_accounts = 0
        for key in keys:
            now = current.get(key, {"code": "", "name": key, "class": None, "balance": 0.0})
            before = prior.get(key, {"code": "", "name": key, "class": None, "balance": 0.0})
            account = now if key in current else before
            kind = now.get("class") or before.get("class")
            text = label(account)
            change = round(now["balance"] - before["balance"], 2)
            if kind == "income":
                income_accounts += 1
                if abs(now["balance"]) < abs(before["balance"]) - 0.005:
                    income_down += 1
            if abs(before["balance"]) < 0.005 and abs(now["balance"]) >= floor:
                findings["new_accounts"].append({"account": text, "class": kind, "balance": now["balance"]})
                continue
            if abs(now["balance"]) < 0.005 and abs(before["balance"]) >= floor:
                findings["emptied_accounts"].append({"account": text, "class": kind, "prior": before["balance"]})
                continue
            if RETAINED.search(text) and abs(change) >= 0.005:
                findings["retained_earnings"].append({"account": text, "prior": before["balance"],
                                                      "balance": now["balance"], "change": change})
            if abs(change) < 0.005 and kind in ("income", "expense") and args.prior_months:
                run_rate = round(before["balance"] / args.prior_months, 2)
                if abs(run_rate) >= floor / 5:
                    findings["went_quiet"].append({"account": text, "class": kind, "monthly_run_rate": run_rate,
                                                   "note": "nothing in the period on an account that ran every month"})
                continue
            if abs(change) < 0.005:
                if kind in (None, "asset", "liability") and ACCRUAL.search(text) and abs(now["balance"]) >= floor / 10:
                    findings["unchanged"].append({"account": text, "class": kind, "balance": now["balance"]})
                elif kind in (None, "asset", "liability") and BANK.search(text) and abs(now["balance"]) >= 0.005:
                    findings["unchanged"].append({"account": text, "class": kind, "balance": now["balance"],
                                                  "note": "a bank or cash balance identical to the prior period"})
                elif kind in (None, "asset") and STOCK.search(text) and abs(now["balance"]) >= floor / 10:
                    findings["unchanged"].append({"account": text, "class": kind, "balance": now["balance"],
                                                  "note": "stock that did not move"})
                elif kind in (None, "asset") and CONTRA.search(text) and abs(now["balance"]) >= floor / 10:
                    findings["unchanged"].append({"account": text, "class": kind, "balance": now["balance"],
                                                  "note": "accumulated depreciation or an allowance that did not move"})
                continue
            if abs(change) < floor:
                continue
            row = {"account": text, "class": kind, "prior": before["balance"], "balance": now["balance"],
                   "change": change}
            if kind in ("income", "expense"):
                row["basis"] = "activity in the period (the two balances are cumulative)"
                if args.prior_months:
                    run_rate = round(before["balance"] / args.prior_months, 2)
                    row["monthly_run_rate"] = run_rate
                    if abs(run_rate) >= 0.005:
                        # Positive means more activity than usual, whichever side the account sits on.
                        side = 1 if run_rate > 0 else -1
                        row["percent_vs_run_rate"] = round((change - run_rate) / abs(run_rate) * 100 * side, 1)
                        row["reads_as"] = "more than the run rate" if row["percent_vs_run_rate"] > 0 else "less than the run rate"
                        if abs(row["percent_vs_run_rate"]) < args.percent or abs(change - run_rate) < floor:
                            continue
                else:
                    row["note"] = "no run rate: pass --prior-months to compare with the months before"
            else:
                # Positive means the balance grew in size, whichever side it sits on.
                side = 1 if before["balance"] > 0 else -1
                percent = round(change / abs(before["balance"]) * 100 * side, 1) if abs(before["balance"]) >= 0.005 else None
                row["percent"] = percent
                row["reads_as"] = None if percent is None else ("the balance grew" if percent > 0 else "the balance shrank")
                if percent is not None and abs(percent) < args.percent:
                    continue
            findings["movements"].append(row)
        if income_accounts >= 3 and income_down / income_accounts > 0.6:
            months_note = ("Most income accounts are smaller than in the prior trial balance. The two files may sit "
                           "either side of a year end, where income and expenses restart at zero. Movements on "
                           "income and expense accounts are then not comparable.")
        findings["movements"].sort(key=lambda row: -abs(row["change"]))
    findings["wrong_side"].sort(key=lambda row: -abs(row["balance"]))

    report = {
        "current": current_info, "prior": prior_info,
        "mode": "full" if prior else "limited (one trial balance: no movements, no unchanged balances)",
        "totals": {"debit": total_debit, "credit": total_credit, "difference": round(total_debit - total_credit, 2),
                   "balances": abs(total_debit - total_credit) < 0.01,
                   "income_to_date": income if has_class else None,
                   "expenses_to_date": expenses if has_class else None},
        "settings": {"percent": args.percent, "floor": floor, "floor_basis": floor_basis,
                     "prior_months": args.prior_months, "holding_regex": args.holding, "accrual_regex": args.accrual,
                     "contra_regex": args.contra, "retained_regex": args.retained, "bank_regex": args.bank,
                     "stock_regex": args.stock},
        "warning": months_note,
        "counts": {key: len(value) for key, value in findings.items()},
        "findings": {key: value[: args.top] for key, value in findings.items()},
        "not_assessable": [
            reason for reason, missing in (
                ("Movements, unchanged balances, new and emptied accounts: no prior trial balance.", not prior),
                ("Balances on the wrong side: the file has no account class or type column.", not has_class),
                ("Income and expense run rate: --prior-months was not given.", bool(prior) and not args.prior_months),
                ("Income and expense accounts cannot be told from balance sheet accounts: the file has no class "
                 "column and --income and --expense were not both given. Their movements are compared on balances "
                 "to date, so ordinary monthly activity shows as growth; the run rate, quiet accounts and the "
                 "year-end warning are not available.", bool(prior) and not knows_income_and_expense),
            ) if missing],
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
