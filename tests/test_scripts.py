"""Tests for the bundled scripts. Standard library only.

    python3 public-skills/tests/test_scripts.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
JE = SKILLS / "cybooks-journal-entry-screen" / "scripts" / "je_screen.py"
TB = SKILLS / "cybooks-close-readiness-scorecard" / "scripts" / "tb_compare.py"
VAT = SKILLS / "cybooks-cyprus-vat-return" / "scripts" / "vat_return.py"
SCHEMAS = SKILLS / "cybooks-cyprus-vat-return" / "assets" / "schemas"
HEADER = ["Journal No", "Date", "Account code", "Account name", "Debit", "Credit", "Memo", "Type", "Created at",
          "Posted by", "Approved by", "Supplier"]


def euro(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if value else ""


def run(script: Path, *args: str) -> dict:
    done = subprocess.run([sys.executable, "-I", str(script), *args], capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout)


class JournalScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        random.seed(7)
        cls.dir = tempfile.TemporaryDirectory()
        rows: list[list[str]] = []

        def add(entry: str, day: date, lines: list[tuple], memo: str, kind: str, recorded: datetime,
                user: str, approver: str = "", supplier: str = "") -> None:
            for account, name, debit, credit in lines:
                rows.append([entry, day.strftime("%d/%m/%Y"), account, name, euro(debit), euro(credit), memo, kind,
                             recorded.strftime("%Y-%m-%d %H:%M:%S"), user, approver, supplier])

        number = 0
        for month in (4, 5, 6):
            for index in range(260):
                number += 1
                day = date(2026, month, random.randint(1, 28))
                while day.weekday() >= 5:
                    day -= timedelta(days=1)
                amount = round(10 ** random.uniform(1, 4), 2)
                recorded = datetime(day.year, day.month, day.day, random.randint(9, 17), random.randint(0, 59))
                if index % 2:
                    add(f"JE-{number}", day, [("1100", "Accounts receivable", amount, 0), ("4000", "Sales revenue", 0, amount)],
                        f"Invoice INV-{number}", "Invoice", recorded, "system", supplier=f"Customer {number}")
                else:
                    add(f"JE-{number}", day, [("6100", "Office costs", amount, 0), ("2000", "Accounts payable", 0, amount)],
                        f"Bill {number}", "Bill", recorded, "system", supplier=f"Supplier {number % 40}")
        manual = "Manual Journal"
        add("MJ-1", date(2026, 6, 30), [("1100", "Accounts receivable", 50000, 0), ("4000", "Sales revenue", 0, 50000)],
            "adjustment", manual, datetime(2026, 7, 9, 23, 40), "maria", "maria")
        for entry, amount in (("MJ-2", 4950), ("MJ-3", 4980), ("MJ-4", 4990)):
            add(entry, date(2026, 6, 29), [("6900", "Sundry", amount, 0), ("1000", "Bank", 0, amount)],
                "Consulting fee June", manual, datetime(2026, 6, 29, 11, 0), "nikos", "eleni")
        add("MJ-5", date(2026, 5, 15), [("2200", "VAT control", 12000, 0), ("3100", "Retained earnings", 0, 12000)],
            "", manual, datetime(2026, 5, 16, 10, 0), "maria", "eleni")
        add("MJ-6", date(2026, 5, 20), [("6500", "Audit fee", 8000, 0), ("2300", "Accruals", 0, 8000)],
            "May accrual for the audit fee", manual, datetime(2026, 5, 20, 10, 0), "maria", "eleni")
        add("MJ-7", date(2026, 6, 22), [("2300", "Accruals", 8000, 0), ("6500", "Audit fee", 0, 8000)],
            "Reverse the May accrual", manual, datetime(2026, 6, 22, 10, 0), "maria", "eleni")
        add("MJ-8", date(2026, 6, 12), [("6100", "Office costs", 700, 0), ("1000", "Bank", 0, 650)],
            "Out of balance", manual, datetime(2026, 6, 12, 10, 0), "maria", "eleni")
        # A monthly fee, billed twice and reversed once in April: a chain of three, not of five.
        fee = [("6700", "Management fee", 6292, 0), ("2000", "Accounts payable", 0, 6292)]
        back = [("2000", "Accounts payable", 6292, 0), ("6700", "Management fee", 0, 6292)]
        for entry, day, lines in (("FEE-1", date(2026, 4, 30), fee), ("FEE-2", date(2026, 4, 30), back),
                                  ("FEE-3", date(2026, 4, 30), fee), ("FEE-4", date(2026, 5, 29), fee),
                                  ("FEE-5", date(2026, 6, 29), fee)):
            add(entry, day, lines, "Management fee", "Bill", datetime(day.year, day.month, day.day, 10, 0), "system",
                supplier="Holding Ltd")
        # Same day, same accounts, same amount, two different customers: not a duplicate.
        for entry, customer in (("SALE-A", "Customer A"), ("SALE-B", "Customer B")):
            add(entry, date(2026, 6, 10), [("1100", "Accounts receivable", 9100, 0), ("4000", "Sales revenue", 0, 9100)],
                "Order", "Invoice", datetime(2026, 6, 10, 10, 0), "system", supplier=customer)
        # A bank statement booked as one entry: 40 payments out, and a net of 300 that mirrors TRANSFER-1.
        add("TRANSFER-1", date(2026, 4, 14), [("1000", "Bank", 300, 0), ("1010", "Savings", 0, 300)],
            "Transfer", "Bank", datetime(2026, 4, 14, 10, 0), "system")
        add("STATEMENT-1", date(2026, 6, 15),
            [("1010", "Savings", 5300, 0), ("1000", "Bank", 0, 5300), ("1000", "Bank", 5000, 0), ("1010", "Savings", 0, 5000)],
            "Statement 15 June", "Bank", datetime(2026, 6, 15, 10, 0), "system")
        add("VAT-1", date(2026, 6, 10), [("2200", "VAT control", 9000, 0), ("2210", "VAT payable", 0, 9000)],
            "VAT return 2026-Q1", manual, datetime(2026, 6, 10, 10, 0), "maria", "eleni")
        # The same amount invoiced to one customer in March and credited to another in May: not a reversal.
        add("INV-X", date(2026, 4, 11), [("1100", "Accounts receivable", 7777, 0), ("4000", "Sales revenue", 0, 7777)],
            "Order X", "Invoice", datetime(2026, 4, 11, 10, 0), "system", supplier="Customer X")
        add("CRN-Y", date(2026, 6, 25), [("4000", "Sales revenue", 7777, 0), ("1100", "Accounts receivable", 0, 7777)],
            "Credit Y", "Invoice", datetime(2026, 6, 25, 10, 0), "system", supplier="Customer Y")
        path = Path(cls.dir.name) / "journal.csv"
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(HEADER)
            writer.writerows(rows)
        cls.report = run(JE, str(path), "--period-start", "2026-04-01", "--period-end", "2026-06-30",
                         "--closed-on", "2026-07-05", "--thresholds", "5000", "--top", "50",
                         "--system-descriptions", "^vat return")
        cls.flags = {entry["entry"]: {flag["test"] for flag in entry["flags"]} for entry in cls.report["flagged"]}
        cls.path = path

    @classmethod
    def tearDownClass(cls) -> None:
        cls.dir.cleanup()

    def test_reads_semicolons_decimal_commas_and_day_first_dates(self) -> None:
        profile = self.report["profile"]
        self.assertEqual("comma", profile["decimal_mark"])
        self.assertEqual(800, profile["entries"])
        self.assertEqual(8, profile["manual_entries"])
        self.assertEqual("2026-04-01", min(profile["date_from"], "2026-04-01"))

    def test_worked_out_tests(self) -> None:
        self.assertEqual(1, self.report["tests"]["balance"]["unbalanced"])
        self.assertIn("unbalanced", self.flags["MJ-8"])
        self.assertIn("after_close", self.flags["MJ-1"])
        self.assertEqual(1, self.report["tests"]["after_close"]["entries"])

    def test_duplicates_need_the_same_counterparty(self) -> None:
        self.assertIn("duplicate", self.flags["FEE-1"])
        self.assertIn("duplicate", self.flags["FEE-3"])
        self.assertNotIn("duplicate", self.flags.get("SALE-A", set()))

    def test_pattern_tests(self) -> None:
        self.assertTrue({"night", "round", "self_approved", "control_account", "manual_income", "weak_description"}
                        <= self.flags["MJ-1"])
        for entry in ("MJ-2", "MJ-3", "MJ-4"):
            self.assertIn("below_limit", self.flags[entry])
        self.assertTrue({"weekend", "control_account", "weak_description"} <= self.flags["MJ-5"])

    def test_a_recurring_fee_is_not_part_of_a_reversal_chain(self) -> None:
        for entry in ("FEE-1", "FEE-2", "FEE-3"):
            self.assertIn("reversal_chain", self.flags[entry])
        for entry in ("FEE-4", "FEE-5"):
            self.assertNotIn("reversal_chain", self.flags.get(entry, set()))
        self.assertIn("reversal_across_months", self.flags["MJ-6"])
        self.assertIn("reversal_across_months", self.flags["MJ-7"])

    def test_an_entry_that_moves_money_both_ways_is_not_a_reversal(self) -> None:
        self.assertNotIn("reversal_across_months", self.flags.get("STATEMENT-1", set()))
        self.assertNotIn("reversal_across_months", self.flags.get("TRANSFER-1", set()))

    def test_a_reversal_needs_the_same_counterparty(self) -> None:
        self.assertNotIn("INV-X", self.flags)
        self.assertNotIn("CRN-Y", self.flags)

    def test_a_system_posting_in_a_manual_journal_is_not_manual(self) -> None:
        self.assertNotIn("VAT-1", self.flags)
        self.assertEqual(1, self.report["profile"]["manual_entries_counted_as_system"])
        self.assertEqual("VAT-1", self.report["profile"]["largest_counted_as_system"][0]["entry"])

    def test_small_entries_rank_below_entries_above_the_floor(self) -> None:
        floor = self.report["settings"]["materiality"]
        amounts = [entry["amount"] for entry in self.report["flagged"] if "integrity" not in entry["categories"]]
        below = [index for index, amount in enumerate(amounts) if amount < floor]
        above = [index for index, amount in enumerate(amounts) if amount >= floor]
        if below and above:
            self.assertGreater(min(below), max(above))

    def test_first_digits_run_on_a_large_population_and_never_flag_an_entry(self) -> None:
        digits = self.report["tests"]["first_digits"]
        self.assertEqual("ran", digits["status"])
        self.assertFalse(digits["signal"])
        self.assertFalse(any("first_digits" in flags for flags in self.flags.values()))

    def test_a_month_end_date_is_not_a_weekend_posting_without_a_recorded_date(self) -> None:
        path = Path(self.dir.name) / "no-recorded.csv"
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["entry_id", "date", "account", "debit", "credit", "source"])
            for entry, day in (("A", "2026-05-31"), ("B", "2026-05-30")):  # Sunday month end, Saturday
                writer.writerow([entry, day, "6100", "500.00", "", "manual"])
                writer.writerow([entry, day, "1000", "", "500.00", "manual"])
        report = run(JE, str(path))
        weekend = report["tests"]["weekend_night"]
        self.assertEqual(1, weekend["weekend"])
        self.assertEqual(1, weekend["month_end_dates_left_out"])
        self.assertIn("recorded_at", report["profile"]["fields_missing"])
        self.assertIn("after_close", report["tests_skipped"])

    def test_a_trial_balance_is_refused(self) -> None:
        path = Path(self.dir.name) / "tb.csv"
        path.write_text("Code,Account,Debit,Credit\n1000,Bank,10,0\n")
        done = subprocess.run([sys.executable, "-I", str(JE), str(path)], capture_output=True, text=True)
        self.assertNotEqual(0, done.returncode)
        self.assertIn("Need at least a date", done.stderr)


class JournalInputTest(unittest.TestCase):
    """Shapes of file that used to be read wrongly."""

    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, text: str) -> str:
        path = Path(self.dir.name) / "journal.csv"
        path.write_text(text)
        return str(path)

    def fails(self, text: str, *args: str) -> str:
        done = subprocess.run([sys.executable, "-I", str(JE), self.write(text), *args], capture_output=True, text=True)
        self.assertNotEqual(0, done.returncode)
        return done.stderr

    def test_a_row_shorter_than_the_header_does_not_crash(self) -> None:
        report = run(JE, self.write("entry_id,date,account,debit,credit,description\n"
                                    "A,2026-06-01,6100,100.00\nA,2026-06-01,1000,,100.00,Paid\n"))
        self.assertEqual(0, report["tests"]["balance"]["unbalanced"])

    def test_a_negative_debit_is_a_credit(self) -> None:
        report = run(JE, self.write(
            "entry_id,date,account,debit,credit,source\n"
            "ACC,2026-05-04,6500,5000.00,,manual\nACC,2026-05-04,2300,,5000.00,manual\n"
            "REV,2026-06-05,6500,-5000.00,,manual\nREV,2026-06-05,2300,,-5000.00,manual\n"), "--materiality", "100")
        self.assertEqual(10000.0, report["profile"]["total_debits"])
        self.assertEqual(1, report["tests"]["reversals"]["pairs_across_months"])

    def test_month_first_dates_are_detected_and_mixed_dates_are_refused(self) -> None:
        body = "entry_id,date,account,debit,credit\nA,06/25/2026,6100,10,\nA,06/25/2026,1000,,10\n"
        report = run(JE, self.write(body + "B,06/04/2026,6100,5,\nB,06/04/2026,1000,,5\n"))
        self.assertFalse(report["profile"]["day_first_dates"])
        self.assertEqual("2026-06-04", report["profile"]["date_from"])
        self.assertIn("mixes day-first and month-first", self.fails(body + "B,25/06/2026,6100,5,\nB,25/06/2026,1000,,5\n"))

    def test_lines_without_a_date_take_the_date_of_the_line_above(self) -> None:
        report = run(JE, self.write("entry_id,date,account,debit,credit\nA,2026-06-01,6100,100,\n,,1000,,100\n"
                                    "B,2026-06-02,6100,40,\n,,1000,,40\n"))
        self.assertEqual(2, report["profile"]["entries"])
        self.assertEqual(0, report["tests"]["balance"]["unbalanced"])
        self.assertEqual(0, report["tests"]["balance"]["single_line"])
        self.assertEqual(2, report["profile"]["lines_that_took_the_date_of_the_line_above"])

    def test_a_file_full_of_unreadable_dates_is_refused(self) -> None:
        rows = "".join(f"line {i},6100,10\n" for i in range(20))
        self.assertIn("cannot be read", self.fails("date,account,amount\n" + rows))

    def test_cost_of_sales_and_income_tax_are_not_income(self) -> None:
        report = run(JE, self.write(
            "entry_id,date,account,account_name,debit,credit,source\n"
            "T,2026-06-30,8500,Income tax expense,900,,manual\nT,2026-06-30,2400,Income tax payable,,900,manual\n"
            "S,2026-06-30,1300,Stock,700,,manual\nS,2026-06-30,5000,Cost of sales,,700,manual\n"
            "R,2026-06-30,1100,Accounts receivable,500,,manual\nR,2026-06-30,4000,Sales,,500,manual\n"))
        self.assertEqual(1, report["tests"]["manual_income"]["entries"])

    def test_a_date_written_with_midnight_is_not_a_night_posting(self) -> None:
        report = run(JE, self.write(
            "entry_id,date,account,debit,credit,source,recorded_at\n"
            "A,2026-05-04,6100,100,,manual,2026-05-04 00:00:00\nA,2026-05-04,1000,,100,manual,2026-05-04 00:00:00\n"))
        self.assertIsNone(report["tests"]["weekend_night"]["night"])
        self.assertNotIn("night", [flag["test"] for entry in report["flagged"] for flag in entry["flags"]])

    def test_whole_numbers_with_dots_as_thousands(self) -> None:
        report = run(JE, self.write("entry_id,date,account,debit,credit\nA,2026-06-01,1300,135.000,\nA,2026-06-01,2000,,135.000\n"))
        self.assertEqual(135000.0, report["profile"]["total_debits"])


class TrialBalanceTest(unittest.TestCase):
    PRIOR = """Code,Account,Class,Debit,Credit
1000,Bank of Cyprus,Assets,21340.10,0
1050,Petty cash,Assets,300.00,0
1100,Accounts receivable,Assets,9870.00,0
1200,Prepaid insurance,Assets,6000.00,0
1500,Equipment,Assets,40000.00,0
1510,Accumulated depreciation,Assets,0,8000.00
1900,Suspense account,Assets,150.00,0
2000,Accounts payable,Liabilities,0,12400.00
2200,VAT control,Liabilities,0,3100.00
2300,Accrued expenses,Liabilities,0,5000.00
3000,Share capital,Equity,0,1000.00
3100,Retained earnings,Equity,0,20000.00
4000,Sales revenue,Income,0,100000.00
5000,Cost of sales,Expenses,40000.00,0
6100,Office costs,Expenses,10000.00,0
6200,Salaries,Expenses,21839.90,0
"""
    CURRENT = """Code,Account,Class,Debit,Credit
1000,Bank of Cyprus,Assets,0,2100.00
1050,Petty cash,Assets,300.00,0
1100,Accounts receivable,Assets,31870.00,0
1200,Prepaid insurance,Assets,6000.00,0
1500,Equipment,Assets,40000.00,0
1510,Accumulated depreciation,Assets,0,8000.00
1900,Suspense account,Assets,2650.00,0
1950,Director loan,Assets,15000.00,0
2000,Accounts payable,Liabilities,0,13000.00
2200,VAT control,Liabilities,0,3900.00
2300,Accrued expenses,Liabilities,0,5000.00
3000,Share capital,Equity,0,1000.00
3100,Retained earnings,Equity,0,17500.00
4000,Sales revenue,Income,0,121000.00
5000,Cost of sales,Expenses,48000.00,0
6100,Office costs,Expenses,18000.00,0
6200,Salaries,Expenses,26180.00,0
Total,,,188000.00,171500.00
"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.dir = tempfile.TemporaryDirectory()
        cls.prior = Path(cls.dir.name) / "prior.csv"
        cls.current = Path(cls.dir.name) / "current.csv"
        cls.prior.write_text(cls.PRIOR)
        cls.current.write_text(cls.CURRENT)
        cls.report = run(TB, "--current", str(cls.current), "--prior", str(cls.prior), "--prior-months", "5")
        cls.found = {key: {row["account"] for row in rows} for key, rows in cls.report["findings"].items()}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.dir.cleanup()

    def test_totals_and_floor(self) -> None:
        self.assertFalse(self.report["totals"]["balances"])
        self.assertEqual(16500.0, self.report["totals"]["difference"])
        self.assertEqual(605.0, self.report["settings"]["floor"])

    def test_findings(self) -> None:
        self.assertEqual({"1900 Suspense account"}, self.found["holding_accounts"])
        self.assertTrue(self.report["findings"]["holding_accounts"][0]["grew"])
        self.assertEqual({"1000 Bank of Cyprus", "1510 Accumulated depreciation"}, self.found["wrong_side"])
        contra = {row["account"]: row["looks_like_contra_account"] for row in self.report["findings"]["wrong_side"]}
        self.assertTrue(contra["1510 Accumulated depreciation"])
        self.assertFalse(contra["1000 Bank of Cyprus"])
        self.assertEqual({"1050 Petty cash", "2300 Accrued expenses", "1200 Prepaid insurance",
                          "1510 Accumulated depreciation"}, self.found["unchanged"])
        self.assertEqual({"1950 Director loan"}, self.found["new_accounts"])
        self.assertEqual({"3100 Retained earnings"}, self.found["retained_earnings"])

    def test_income_and_expense_movements_use_the_run_rate(self) -> None:
        movements = {row["account"]: row for row in self.report["findings"]["movements"]}
        self.assertEqual(300.0, movements["6100 Office costs"]["percent_vs_run_rate"])
        self.assertEqual("more than the run rate", movements["6100 Office costs"]["reads_as"])
        self.assertNotIn("4000 Sales revenue", movements)  # 21.000 against a run rate of 20.000: under 10 percent
        self.assertNotIn("5000 Cost of sales", movements)

    def test_percentages_read_the_same_on_debit_and_credit_accounts(self) -> None:
        movements = {row["account"]: row for row in self.report["findings"]["movements"]}
        self.assertGreater(movements["2200 VAT control"]["percent"], 0)  # owed 3,100, now 3,900: it grew
        self.assertEqual("the balance grew", movements["2200 VAT control"]["reads_as"])
        self.assertLess(movements["3100 Retained earnings"]["percent"], 0)
        prior = Path(self.dir.name) / "p2.csv"
        current = Path(self.dir.name) / "c2.csv"
        prior.write_text("Code,Account,Class,Debit,Credit\n4000,Sales,Income,0,100000\n1000,Bank,Assets,100000,0\n")
        current.write_text("Code,Account,Class,Debit,Credit\n4000,Sales,Income,0,140000\n1000,Bank,Assets,140000,0\n")
        sales = run(TB, "--current", str(current), "--prior", str(prior), "--prior-months", "5")["findings"]["movements"]
        row = next(item for item in sales if item["account"] == "4000 Sales")
        self.assertEqual(100.0, row["percent_vs_run_rate"])  # 40,000 in the month against 20,000 a month

    def test_patterns_can_be_replaced_for_another_language(self) -> None:
        prior = Path(self.dir.name) / "p3.csv"
        current = Path(self.dir.name) / "c3.csv"
        body = ("Code,Account,Class,Debit,Credit\n02080,Afschrijving inventaris,Assets,0,9000\n"
                "11008,Rabo spaarrekening,Assets,42060,0\n32005,Voorraad,Assets,135000,0\n"
                "06000,Kapitaal,Equity,0,168060\n80000,Verkopen,Income,0,{sales}\n40000,Kosten,Expenses,{sales},0\n")
        prior.write_text(body.format(sales="500000"))
        current.write_text(body.format(sales="600000"))
        report = run(TB, "--current", str(current), "--prior", str(prior), "--contra", "afschrijving", "--bank", "rabo",
                     "--stock", "voorraad")
        contra = {row["account"]: row["looks_like_contra_account"] for row in report["findings"]["wrong_side"]}
        self.assertTrue(contra["02080 Afschrijving inventaris"])
        notes = {row["account"]: row.get("note") for row in report["findings"]["unchanged"]}
        self.assertEqual("a bank or cash balance identical to the prior period", notes["11008 Rabo spaarrekening"])
        self.assertEqual("stock that did not move", notes["32005 Voorraad"])

    def test_an_account_that_ran_every_month_and_stopped(self) -> None:
        prior = Path(self.dir.name) / "p4.csv"
        current = Path(self.dir.name) / "c4.csv"
        body = ("Code,Account,Class,Debit,Credit\n4000,Sales,Income,0,{sales}\n6300,Rent,Expenses,25000,0\n"
                "6999,Suspense costs,Expenses,400,0\n1000,Bank,Assets,{bank},0\n")
        prior.write_text(body.format(sales="500000", bank="474600"))
        current.write_text(body.format(sales="600000", bank="574600"))
        report = run(TB, "--current", str(current), "--prior", str(prior), "--prior-months", "5")
        self.assertEqual(["6300 Rent"], [row["account"] for row in report["findings"]["went_quiet"]])
        self.assertEqual([], report["findings"]["holding_accounts"])  # an expense account is not a holding account

    def test_a_holding_account_that_changed_side(self) -> None:
        prior = Path(self.dir.name) / "p5.csv"
        current = Path(self.dir.name) / "c5.csv"
        prior.write_text("Code,Account,Debit,Credit\n1900,Clearing,0,3978.40\n1000,Bank,3978.40,0\n")
        current.write_text("Code,Account,Debit,Credit\n1900,Clearing,667.17,0\n1000,Bank,0,667.17\n")
        row = run(TB, "--current", str(current), "--prior", str(prior))["findings"]["holding_accounts"][0]
        self.assertFalse(row["grew"])
        self.assertTrue(row["changed_side"])

    def test_class_names_are_read_by_meaning(self) -> None:
        current = Path(self.dir.name) / "c6.csv"
        current.write_text("Code,Account,Class,Debit,Credit\n4000,Sales,Sales,0,100000\n5000,Purchases,Cost of sales,40000,0\n"
                           "8500,Corporation tax,Income tax,5000,0\n2500,Customer deposits,Deferred income,0,3000\n"
                           "3000,Ordinary shares,Stockholders equity,0,1000\n1000,Bank,Current assets,59000,0\n"
                           "Generated on 2026-07-01\n")
        report = run(TB, "--current", str(current))
        self.assertEqual(100000.0, report["totals"]["income_to_date"])
        self.assertEqual(45000.0, report["totals"]["expenses_to_date"])
        self.assertEqual(500.0, report["settings"]["floor"])
        self.assertEqual([], report["findings"]["wrong_side"])

    def test_without_classes_the_report_says_what_it_cannot_tell(self) -> None:
        prior = Path(self.dir.name) / "p7.csv"
        current = Path(self.dir.name) / "c7.csv"
        body = "Code,Account,Debit,Credit\n4000,Sales,0,{sales}\n6300,Rent,{rent},0\n1000,Bank,{bank},0\n"
        prior.write_text(body.format(sales="500000", rent="25000", bank="475000"))
        current.write_text(body.format(sales="600000", rent="30000", bank="570000"))
        plain = run(TB, "--current", str(current), "--prior", str(prior), "--prior-months", "5")
        self.assertTrue(any("cannot be told from balance sheet accounts" in note for note in plain["not_assessable"]))
        told = run(TB, "--current", str(current), "--prior", str(prior), "--prior-months", "5",
                   "--income", "^4", "--expense", "^6")
        self.assertFalse(any("cannot be told" in note for note in told["not_assessable"]))
        self.assertEqual(["1000 Bank"], [row["account"] for row in told["findings"]["movements"]])
        self.assertEqual(3000.0, told["settings"]["floor"])

    def test_a_holding_account_that_is_new_has_grown(self) -> None:
        prior = Path(self.dir.name) / "p8.csv"
        current = Path(self.dir.name) / "c8.csv"
        prior.write_text("Code,Account,Debit,Credit\n1000,Bank,500,0\n3000,Capital,0,500\n")
        current.write_text("Code,Account,Debit,Credit\n1000,Bank,100,0\n1900,Suspense,400,0\n3000,Capital,0,500\n")
        row = run(TB, "--current", str(current), "--prior", str(prior))["findings"]["holding_accounts"][0]
        self.assertTrue(row["grew"])
        self.assertEqual(0.0, row["prior"])

    def test_one_trial_balance_is_a_limited_read(self) -> None:
        report = run(TB, "--current", str(self.current))
        self.assertTrue(report["mode"].startswith("limited"))
        self.assertEqual(0, report["counts"]["movements"])
        self.assertEqual(1, len(report["not_assessable"]))


def run_any(script: Path, *args: str) -> tuple[int, dict]:
    """For a command whose exit code is part of the answer (2 = no file written)."""
    done = subprocess.run([sys.executable, "-I", str(script), *args], capture_output=True, text=True)
    if done.returncode not in (0, 2):
        raise AssertionError(done.stderr)
    return done.returncode, json.loads(done.stdout)


def validates(xml: Path, schema: str) -> bool | None:
    """Against the Tax Department's schema, with xmllint. None when there is no validator here."""
    xmllint = shutil.which("xmllint")
    if not xmllint:
        return None
    return subprocess.run([xmllint, "--noout", "--nonet", "--schema", str(SCHEMAS / schema), str(xml)],
                          capture_output=True).returncode == 0


SET = {"1": "500.00", "2": "190.00", "4": "490.00", "6": "5000", "7": "4000", "8A": "0", "8B": "3000", "9": "0",
       "10": "0", "11A": "1000", "11B": "1500"}
VIES = ["--vies", "2026-07:goods=0,triangular=0,services=1000,rows=1", "--vies", "2026-08:goods=0,triangular=0,services=1000,rows=1",
        "--vies", "2026-09:goods=0,triangular=0,services=1000,rows=1"]
BASE = ["--taxpayer", "CY12345678X", "--from", "2026-07-01", "--to", "2026-09-30", "--today", "2026-10-20"]


def refused(*args: str) -> str:
    """Runs a command that must stop before any JSON (exit 1) and returns what it said."""
    done = subprocess.run([sys.executable, "-I", str(VAT), *args], capture_output=True, text=True)
    if done.returncode != 1 or done.stdout:
        raise AssertionError(f"expected exit 1 and no output, got {done.returncode}: {done.stdout[:200]}")
    return done.stderr


class VatReturnTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.out = Path(self.dir.name)

    def tearDown(self) -> None:
        self.dir.cleanup()

    def go(self, command: str, boxes: dict[str, str], *extra: str, vies: bool = True) -> tuple[int, dict]:
        """`xml` gets the three monthly VIES statements unless the test gives its own or asks for none."""
        args = [command, *BASE]
        for box, amount in boxes.items():
            args += [f"--box={box}={amount}"]
        if command == "xml":
            args += ["--out", str(self.out)]
            if vies and not any(item.startswith("--vies") for item in extra):
                args += VIES
        return run_any(VAT, *args, *extra)

    @staticmethod
    def answer(report: dict, code: str) -> str:
        return next(item["answer"] for item in report["checks"] if item["code"] == code)

    @staticmethod
    def boxes(report: dict) -> dict[str, dict]:
        return {row["box"]: row for row in report["boxes"]}

    def test_a_consistent_return_is_written_and_passes_the_published_schema(self) -> None:
        code, report = self.go("xml", SET, *VIES)
        self.assertEqual(0, code)
        self.assertEqual([], report["blocks_file"])
        self.assertEqual("12345678X", report["taxpayer"])
        self.assertEqual("2026-11-10", report["due"]["date"])
        self.assertEqual(21, report["due"]["days_left"])
        self.assertFalse(report["due"]["passed"])
        self.assertEqual("payable", report["result"])
        self.assertEqual("690.00", self.boxes(report)["3"]["amount"])
        self.assertEqual("200.00", self.boxes(report)["5"]["amount"])
        self.assertEqual("worked out from the other boxes", self.boxes(report)["5"]["source"])
        self.assertEqual([f"VR-{n:02d}" for n in range(1, 18)], [item["code"] for item in report["checks"]])
        self.assertEqual("Looks right", self.answer(report, "VR-11"))
        self.assertEqual("Not relevant", self.answer(report, "VR-10"))
        path = Path(report["file"]["path"])
        self.assertTrue(path.is_absolute())
        text = path.read_text(encoding="utf-8")
        self.assertIn('<mof:f4-declarations xmlns:mof="http://www.mof.gov.cy">', text)  # as the Cybooks app writes it
        self.assertIn('taxpayer="12345678X" version="2010-1.0"', text)
        self.assertIn("<mof:total-vat>200,00</mof:total-vat>", text)
        self.assertIn("<mof:total-outflows>5000,00</mof:total-outflows>", text)
        self.assertEqual(13, text.count("</mof:") - 3)
        if validates(path, "cy-f4-2010-declaration.xsd") is not None:
            self.assertTrue(validates(path, "cy-f4-2010-declaration.xsd"))
            self.assertTrue(report["file"]["schema"]["valid"])

    def test_a_scored_check_is_never_passed(self) -> None:
        _, report = self.go("check", SET, *VIES)
        for item in report["checks"]:
            if item["grade"] == "scored":
                self.assertNotIn(item["answer"], ("Passed", "Needs a look"), item["code"])
            else:
                self.assertNotIn(item["answer"], ("Looks right", "Worth a look"), item["code"])
        self.assertEqual(len(report["checks"]), sum(report["counts"].values()))

    def test_check_writes_nothing_and_says_when_the_due_date_has_passed(self) -> None:
        code, report = self.go("check", SET, "--today", "2026-11-11")
        self.assertEqual(0, code)
        self.assertNotIn("file", report)
        self.assertEqual("Could not be checked", self.answer(report, "VR-11"))
        self.assertEqual([f"VR-{n:02d}" for n in range(1, 17)], [item["code"] for item in report["checks"]])
        self.assertTrue(report["due"]["passed"])
        self.assertEqual(-1, report["due"]["days_left"])
        self.assertEqual([], list(self.out.iterdir()))

    def test_a_box_that_does_not_add_up_blocks_the_file(self) -> None:
        code, report = self.go("xml", {**SET, "3": "700.00"})
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VR-04"))
        self.assertIn("VR-04", report["blocks_file"])
        self.assertEqual("Could not be checked", self.answer(report, "VR-17"))
        self.assertFalse(report["file"]["written"])
        self.assertEqual([], list(self.out.iterdir()))

    def test_one_cent_off_is_off(self) -> None:
        code, report = self.go("xml", {**SET, "3": "690.01", "5": "200.01"})
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VR-04"))

    def test_a_vat_figure_finer_than_a_cent_is_not_rounded_for_the_person(self) -> None:
        code, report = self.go("xml", {**SET, "1": "500.0049"})
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VR-02"))
        self.assertIn("VR-02", report["blocks_file"])

    def test_box_6_and_box_7_must_cover_the_boxes_inside_them(self) -> None:
        code, report = self.go("xml", {**SET, "6": "4000", "7": "2000"})
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VR-06"))
        self.assertEqual("Needs a look", self.answer(report, "VR-07"))

    def test_boxes_rounded_one_by_one_may_exceed_the_box_they_sit_in_by_the_rounding(self) -> None:
        # 6 = 8B + 11B to the cent; rounded each on its own, 3001 + 1501 is one euro more than 4501.
        boxes = {**SET, "6": "4501.00", "8B": "3000.50", "11B": "1500.50", "7": "4000"}
        code, report = self.go("check", boxes, "--round-values")
        self.assertEqual("Passed", self.answer(report, "VR-06"))
        self.assertIn("allowed 1.50", next(c["detail"] for c in report["checks"] if c["code"] == "VR-06"))
        code, report = self.go("check", {**boxes, "6": "4500"}, "--round-values")
        self.assertEqual("Needs a look", self.answer(report, "VR-06"))

    def test_a_wrong_command_line_is_exit_1_not_the_no_file_code(self) -> None:
        self.assertIn("--from", refused("xml", "--taxpayer", "12345678X"))
        self.assertIn("invalid choice", refused("check", *BASE, "--decimal", "dot"))

    def test_a_missing_box_is_not_taken_for_zero_but_nil_is_a_figure(self) -> None:
        boxes = {box: amount for box, amount in SET.items() if box not in ("9", "10")}
        code, report = self.go("xml", boxes)
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VR-01"))
        self.assertEqual("Could not be checked", self.answer(report, "VR-06"))
        self.assertIsNone(self.boxes(report)["9"]["amount"])
        code, report = self.go("xml", boxes, "--missing-zero")
        self.assertEqual(0, code)
        self.assertEqual("zero, as told", self.boxes(report)["10"]["source"])
        code, report = self.go("check", {**boxes, "9": "nil", "10": "-"})
        self.assertEqual("Passed", self.answer(report, "VR-01"))
        self.assertEqual("given as nil", self.boxes(report)["10"]["source"])
        self.assertEqual("0.00", self.boxes(report)["9"]["amount"])

    def test_values_are_whole_euros_and_rounding_is_half_up(self) -> None:
        code, report = self.go("xml", {**SET, "6": "5000.50", "8B": "3000.50"})
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VR-03"))
        code, report = self.go("xml", {**SET, "6": "5000.50", "8B": "3000.50"}, "--round-values")
        self.assertEqual(0, code)
        self.assertEqual("5001.00", self.boxes(report)["6"]["amount"])  # round() would give 5000
        self.assertEqual("3001.00", self.boxes(report)["8B"]["amount"])
        self.assertEqual("rounded to the euro, from 3000.50", self.boxes(report)["8B"]["source"])

    def test_a_gap_between_box_2_and_box_11a_needs_a_written_reason(self) -> None:
        gap = {**SET, "2": "261.49", "4": "561.49"}
        code, report = self.go("xml", gap)
        self.assertEqual(2, code)
        self.assertEqual("Worth a look", self.answer(report, "VR-09"))
        self.assertEqual(["VR-09"], report["blocks_file"])
        code, report = self.go("xml", gap, "--note", "box2=Goods at 5%: invoices 14 and 17")
        self.assertEqual(0, code)
        self.assertEqual("Worth a look", self.answer(report, "VR-09"))  # explained, still not "passed"
        self.assertEqual("Goods at 5%: invoices 14 and 17", report["notes_given"]["box2"])

    def test_box_2_without_box_11a_blocks_and_no_reason_lifts_it(self) -> None:
        code, report = self.go("xml", {**SET, "2": "190.00", "11A": "0", "7": "4000"}, "--note", "box2=because")
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VR-08"))

    def test_boxes_8a_and_8b_are_tied_to_vies_kind_by_kind(self) -> None:
        # All of it was goods on VIES, the return shows it as services: a combined total would not see it.
        swapped = [item.replace("goods=0", "goods=1000").replace("services=1000", "services=0") for item in VIES]
        code, report = self.go("xml", SET, *swapped)
        self.assertEqual(2, code)
        self.assertEqual("Worth a look", self.answer(report, "VR-10"))
        self.assertEqual("Worth a look", self.answer(report, "VR-11"))
        self.assertEqual(["VR-10", "VR-11"], report["blocks_file"])
        code, report = self.go("xml", SET, *swapped, "--note", "box8a=reason a", "--note", "box8b=reason b")
        self.assertEqual(0, code)
        # A month without a statement is not nil: the test cannot be made, and says which month.
        code, report = self.go("check", SET, *VIES[:4])
        self.assertEqual("Could not be checked", self.answer(report, "VR-11"))
        self.assertIn("2026-09", next(c["detail"] for c in report["checks"] if c["code"] == "VR-11"))
        self.assertEqual("not given", report["vies_statements"][2]["source"])
        # Rounding of rows is allowed for, and no more than that.
        code, report = self.go("check", {**SET, "8B": "3002"}, *VIES)
        self.assertEqual("Looks right", self.answer(report, "VR-11"))
        code, report = self.go("check", {**SET, "8B": "3003"}, *VIES)
        self.assertEqual("Worth a look", self.answer(report, "VR-11"))
        # A month given as nil has no row to round: it adds nothing to what is allowed.
        nil = [VIES[0], VIES[1].replace("services=1000", "services=3000"), "--vies", "2026-08:goods=0,triangular=0,services=0",
               "--vies", "2026-09:goods=0,triangular=0,services=0"]
        code, report = self.go("check", {**SET, "8B": "3002"}, *nil)
        self.assertEqual("Worth a look", self.answer(report, "VR-11"))
        self.assertIn("Allowed difference: 1.00", next(c["detail"] for c in report["checks"] if c["code"] == "VR-11"))

    def test_triangular_sales_in_box_8a_are_asked_about_not_refused(self) -> None:
        boxes = {**SET, "8A": "500", "8B": "3000"}
        vies = [VIES[0], VIES[1].replace("triangular=0", "triangular=500"), VIES[2], VIES[3], VIES[4], VIES[5]]
        code, report = self.go("xml", boxes, *vies)
        self.assertEqual(0, code)
        self.assertEqual("Worth a look", self.answer(report, "VR-10"))
        self.assertIn("boxes 6 and 10", next(c["detail"] for c in report["checks"] if c["code"] == "VR-10"))

    def test_the_statements_the_skill_built_feed_the_return(self) -> None:
        results = []
        for month, lines in (("2026-07", ["A;DE123456789;1000;services"]), ("2026-08", ["B;DE123456789;1000;services"]),
                             ("2026-09", ["C;DE123456789;1000;services", "D;;50;services"])):
            source = self.out / f"sales-{month}.csv"
            source.write_text("Invoice;Customer VAT;Net;Kind\n" + "\n".join(lines) + "\n")
            done = subprocess.run([sys.executable, "-I", str(VAT), "vies", "--taxpayer", "12345678X", "--month", month,
                                   "--lines", str(source), "--out", str(self.out)], capture_output=True, text=True)
            result = self.out / f"vies-{month}.json"
            result.write_text(done.stdout)
            results += ["--vies-result", str(result)]
        code, report = self.go("xml", SET, *results)
        self.assertEqual(2, code)
        self.assertEqual("Could not be checked", self.answer(report, "VR-11"))  # September was not built
        self.assertEqual(["VR-11"], report["blocks_file"])  # and the return waits for it
        detail = next(c["detail"] for c in report["checks"] if c["code"] == "VR-11")
        self.assertIn("2026-09 (VS-02)", detail)
        self.assertIn("as they would be, the services add up to 3000.00", detail)
        self.assertEqual("not built (VS-02); the rows as they would be", report["vies_statements"][2]["source"])
        self.assertEqual("1000.00", report["vies_statements"][0]["services"])

    def vies_result(self, month: str, lines: list[str]) -> tuple[int, str]:
        source = self.out / f"sales-{month}.csv"
        source.write_text("Invoice;Customer VAT;Net;Kind\n" + "\n".join(lines) + "\n")
        done = subprocess.run([sys.executable, "-I", str(VAT), "vies", "--taxpayer", "12345678X", "--month", month,
                               "--lines", str(source), "--out", str(self.out)], capture_output=True, text=True)
        result = self.out / f"vies-{month}-{done.returncode}.json"
        result.write_text(done.stdout)
        return done.returncode, str(result)

    def test_a_statement_is_unbuilt_only_when_its_own_tests_stopped_it(self) -> None:
        july = self.vies_result("2026-07", ["A;DE123456789;1500;services"])[1]
        august = self.vies_result("2026-08", ["B;DE123456789;1500;services"])[1]
        # September's only line cannot go on the statement: no rows, but that is not a nil month.
        code, blocked = self.vies_result("2026-09", ["C;;700;services"])
        self.assertEqual(2, code)
        code, report = self.go("check", SET, "--vies-result", july, "--vies-result", august, "--vies-result", blocked)
        self.assertEqual("Could not be checked", self.answer(report, "VR-11"))
        self.assertIn("VR-11", report["blocks_file"])
        # A statement built before, and run again: the file exists, nothing stopped it, and it still ties.
        code, again = self.vies_result("2026-07", ["A;DE123456789;1500;services"])
        self.assertEqual(2, code)
        code, report = self.go("check", SET, "--vies-result", again, "--vies-result", august,
                               "--vies", "2026-09:goods=0,triangular=0,services=0")
        self.assertEqual("Looks right", self.answer(report, "VR-11"))

    def test_a_return_with_eu_sales_waits_for_the_vies_tie_or_a_written_reason(self) -> None:
        code, report = self.go("xml", SET, vies=False)
        self.assertEqual(2, code)
        self.assertEqual("Could not be checked", self.answer(report, "VR-11"))
        self.assertEqual(["VR-11"], report["blocks_file"])  # box 8A is nil, so VR-10 holds nothing back
        code, report = self.go("xml", SET, "--note", "box8b=September statement is prepared by the accountant", vies=False)
        self.assertEqual(0, code)
        self.assertEqual("Could not be checked", self.answer(report, "VR-11"))
        code, report = self.go("xml", {**SET, "8B": "0"}, "--replace", vies=False)
        self.assertEqual(0, code)  # nothing sold to the EU: nothing to tie

    def test_reverse_charge_question_does_not_block(self) -> None:
        code, report = self.go("xml", {**SET, "1": "100.00"}, *VIES)
        self.assertEqual(0, code)
        self.assertEqual("Worth a look", self.answer(report, "VR-12"))
        self.assertEqual([], report["blocks_file"])

    def test_figures_in_european_format_and_a_credit(self) -> None:
        european = {box: amount.replace(".", ",") for box, amount in SET.items()}
        code, report = self.go("xml", {**european, "1": "€ 1.234,56", "4": "2 000,00", "6": "12.500"})
        self.assertEqual(0, code)
        self.assertEqual("comma", report["decimal_mark_read"])
        self.assertEqual("1234.56", self.boxes(report)["1"]["amount"])
        self.assertEqual("12500.00", self.boxes(report)["6"]["amount"])
        self.assertEqual("-575.44", self.boxes(report)["5"]["amount"])
        self.assertEqual("refundable or carried forward", report["result"])
        self.assertIn("<mof:total-vat>-575,44</mof:total-vat>", Path(report["file"]["path"]).read_text())

    def test_a_figure_that_cannot_be_read_for_certain_stops_the_run(self) -> None:
        base = ["check", *BASE]
        self.assertIn("not a number", refused(*base, "--box", "1=n/a"))
        self.assertIn("not a number", refused(*base, "--box", "1=31-08-2026"))
        self.assertIn("not a number", refused(*base, "--box", "1=1 2 3"))
        # 1.234,56 beside 190.00: read as one format, the other figure would be a hundred times too large.
        self.assertIn("mix two number formats", refused(*base, "--box", "1=1.234,56", "--box", "2=190.00"))
        self.assertIn("mix two number formats", refused(*base, "--box", "1=1,234", "--box", "6=5.000"))
        self.assertIn("does not read as a number with a decimal comma",
                      refused(*base, "--decimal", "comma", "--box", "1=1.234,56", "--box", "2=190.00"))
        self.assertIn("can be read two ways", refused(*base, "--box", "1=1,234", "--box", "2=3.737,40"))
        self.assertIn("given twice", refused(*base, "--box", "1=5", "--box", "Box 1=6"))
        self.assertIn("without a comma", refused(*base, "--vies", "2026-07:goods=0,triangular=0,services=4,301"))

    def test_minus_zero_is_written_as_zero(self) -> None:
        code, report = self.go("xml", {box: "0" for box in SET} | {"1": "-0.00"}, vies=False)
        self.assertEqual(0, code)
        text = Path(report["file"]["path"]).read_text()
        self.assertNotIn("-0,00", text)
        self.assertEqual(13, text.count(">0,00<"))

    def test_a_taxpayer_number_that_is_not_cypriot_blocks(self) -> None:
        code, report = run_any(VAT, "xml", "--taxpayer", "DE123456789", "--from", "2026-07-01", "--to", "2026-09-30",
                               "--out", str(self.out), *VIES, *[f"--box={box}={amount}" for box, amount in SET.items()])
        self.assertEqual(2, code)
        self.assertEqual(["VR-14"], report["blocks_file"])

    def test_boxes_from_a_file_and_an_existing_file_is_kept(self) -> None:
        boxes = self.out / "boxes.csv"
        boxes.write_text("Box;Amount\n" + "\n".join(f"Box {box};{amount}" for box, amount in SET.items()) + "\n")
        args = ["xml", *BASE, "--boxes", str(boxes), "--out", str(self.out), *VIES]
        code, report = run_any(VAT, *args)
        self.assertEqual(0, code)
        code, again = run_any(VAT, *args)
        self.assertEqual(2, code)
        self.assertIn("exists", again["file"]["why"][0])
        code, again = run_any(VAT, *args, "--replace")
        self.assertEqual(0, code)
        self.assertEqual(report["file"]["sha256"], again["file"]["sha256"])

    def test_an_amount_cut_in_two_by_the_delimiter_stops_the_run(self) -> None:
        boxes = self.out / "boxes.csv"
        boxes.write_text("box,amount\n1,1,234.56\n2,190.00\n")  # unquoted 1,234.56: would read as box 1 = 1
        self.assertIn("more cells than the header", refused("check", *BASE, "--boxes", str(boxes)))

    def test_boxes_as_json_and_as_cybooks_returns_them(self) -> None:
        plain = self.out / "boxes.json"
        plain.write_text(json.dumps({box: float(amount) for box, amount in SET.items()}))
        code, report = run_any(VAT, "check", *BASE, "--boxes", str(plain))
        self.assertEqual("690.00", self.boxes(report)["3"]["amount"])
        cybooks = self.out / "cybooks.json"
        cybooks.write_text(json.dumps({"boxes": [{"slug": f"box-{box.lower()}", "name": f"Box {box}", "amount": float(amount)}
                                                 for box, amount in {**SET, "3": "690", "5": "200"}.items()]}))
        code, report = run_any(VAT, "check", *BASE, "--boxes", str(cybooks))
        self.assertEqual("Passed", self.answer(report, "VR-04"))
        self.assertEqual("given", self.boxes(report)["5"]["source"])
        twice = self.out / "twice.json"
        twice.write_text('{"1": 100, "1": 900}')
        self.assertIn("given twice", refused("check", *BASE, "--boxes", str(twice)))

    def test_the_bundled_schemas_are_the_ones_the_app_uses(self) -> None:
        source = ROOT.parent / "resources" / "schemas" / "tfa"
        if not source.exists():
            self.skipTest("not inside the Cybooks repository")
        for schema in ("cy-f4-2010-declaration.xsd", "cy-vies1-2010-declaration.xsd", "cy-core.xsd", "olive-core.xsd"):
            self.assertEqual((source / schema).read_bytes(), (SCHEMAS / schema).read_bytes(), schema)


class ViesStatementTest(unittest.TestCase):
    HEADER = "Invoice;Date;Customer;Customer VAT;Net;VAT amount;Kind"
    GOOD = ["INV-1;2026-08-03;Alpha GmbH;DE 123456789;1.000,50;0,00;services",
            "INV-2;10/08/2026;Alpha GmbH;de123456789;499,00;0,00;Services",
            "CN-1;2026-08-12;Alpha GmbH;DE123456789;-200,00;0,00;services",
            "INV-3;2026-08-15;Beta SA;GR123456789;2.500,50;0,00;goods",
            "INV-7;2026-08-16;Zeta OU;EE100000001;40,00;0,00;triangular",
            "INV-8;2026-08-17;Eta SRL;IT00000000001;75,00;0,00;services",
            "CN-8;2026-08-18;Eta SRL;IT00000000001;-75,00;0,00;services",
            "INV-5;2026-09-01;Delta BV;NL123456789B01;100,00;0,00;services",
            "INV-0;2026-07-30;Delta BV;NL123456789B01;100,00;0,00;services"]
    BAD = ["INV-4;2026-08-20;Gamma Ltd;12345678X;300,00;57,00;services",
           "INV-6;2026-08-21;Epsilon Inc;;900,00;0,00;services",
           "INV-9;2026-08-22;Theta Ltd;GB123456789;50,00;0,00;services",
           "INV-10;2026-08-23;Iota Ltd;XI123456789;60,00;0,00;services",
           "INV-11;2026-08-24;Kappa GmbH;DE999999999;100,00;19,00;services",
           "INV-12;24th Aug;Lambda SA;FR12345678901;10,00;0,00;services"]

    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.out = Path(self.dir.name)

    def tearDown(self) -> None:
        self.dir.cleanup()

    def go(self, lines: list[str], *extra: str, header: str | None = None) -> tuple[int, dict]:
        source = self.out / "sales.csv"
        source.write_text("\n".join([header or self.HEADER, *lines]) + "\n", encoding="utf-8")
        return run_any(VAT, "vies", "--taxpayer", "CY12345678X", "--month", "2026-08", "--lines", str(source),
                       "--out", str(self.out), "--today", "2026-09-20", *extra)

    @staticmethod
    def answer(report: dict, code: str) -> str:
        return next(item["answer"] for item in report["checks"] if item["code"] == code)

    def test_one_row_per_customer_in_whole_euros_half_up(self) -> None:
        code, report = self.go(self.GOOD)
        self.assertEqual(0, code)
        self.assertEqual("2026-09-15", report["due"]["date"])
        self.assertTrue(report["due"]["passed"])
        self.assertEqual([f"VS-{n:02d}" for n in range(1, 9)], [item["code"] for item in report["checks"]])
        rows = {f"{row['country']}{row['vat_number']}": row for row in report["rows"]}
        self.assertEqual(["DE123456789", "EE100000001", "EL123456789"], list(rows))  # GR is written EL
        self.assertEqual(1300, rows["DE123456789"]["services"])  # 1299.50, credit note taken off
        self.assertEqual("1299.50", rows["DE123456789"]["exact"]["services"])
        self.assertEqual(2501, rows["EL123456789"]["goods"])  # 2500.50: round() would give 2500
        self.assertEqual(40, rows["EE100000001"]["triangular"])
        self.assertEqual({"goods": 2501, "triangular": 40, "services": 1300, "rows": 3}, report["totals"])
        self.assertEqual(["IT00000000001"], [f"{r['country']}{r['vat_number']}" for r in report["rows_left_out"]])
        self.assertIn("Given as GR123456789", rows["EL123456789"]["note"])
        self.assertNotIn("note", rows["DE123456789"])
        # A quarter's list is fine: lines of other months wait for their own statement.
        self.assertEqual({"2026-07": 1, "2026-09": 1}, report["lines_of_other_months"])
        self.assertEqual([], report["unusable_lines"])
        self.assertEqual("Could not be checked", self.answer(report, "VS-06"))  # numbers were not looked up
        path = Path(report["file"]["path"])
        text = path.read_text(encoding="utf-8")
        self.assertIn("<mof:month>8</mof:month>", text)
        self.assertIn("<mof:total-rows>3</mof:total-rows>", text)
        self.assertIn('<mof:vat-number country="EL">123456789</mof:vat-number>', text)
        self.assertIn("<mof:sum-services-amount>1300</mof:sum-services-amount>", text)
        self.assertIn("<mof:triangle-transactions-amount>0</mof:triangle-transactions-amount>", text)  # 0, not empty
        self.assertNotIn("IT", text)
        self.assertNotIn("NL", text)
        if validates(path, "cy-vies1-2010-declaration.xsd") is not None:
            self.assertTrue(validates(path, "cy-vies1-2010-declaration.xsd"))
        with open(report["file"]["lines_file"], encoding="utf-8") as handle:
            trail = list(csv.DictReader(handle))
        self.assertEqual(3, len(trail))
        self.assertIn("CN-1 (services, -200.00)", trail[0]["documents"])

    def test_lines_that_do_not_belong_block_the_file_until_the_person_says_so(self) -> None:
        code, report = self.go(self.GOOD + self.BAD)
        self.assertEqual(2, code)
        self.assertFalse(report["file"]["written"])
        self.assertEqual(["VS-02"], report["blocks_file"])
        why = {line["document"]: line["why"] for line in report["unusable_lines"]}
        self.assertEqual({"INV-4", "INV-6", "INV-9", "INV-10", "INV-11", "INV-12"}, set(why))
        self.assertIn("Cyprus", why["INV-4"])
        self.assertIn("no VAT number", why["INV-6"])
        self.assertIn("not a VAT number of another Member State", why["INV-9"])
        self.assertIn("goods only", why["INV-10"])
        self.assertIn("carries VAT of 19.00", why["INV-11"])  # a line with VAT does not reach the file
        self.assertIn("was not read", why["INV-12"])
        vat = next(c for c in report["checks"] if c["code"] == "VS-04")
        self.assertEqual("Needs a look", vat["answer"])
        self.assertIn("INV-4 (57.00)", vat["detail"])  # also when the line is refused for another reason
        self.assertEqual("Needs a look", self.answer(report, "VS-03"))
        self.assertEqual([], list(self.out.glob("VIES*")))
        code, report = self.go(self.GOOD + self.BAD, "--skip-unusable")
        self.assertEqual(0, code)
        self.assertEqual(3, report["totals"]["rows"])
        self.assertEqual("Needs a look", self.answer(report, "VS-02"))
        self.assertNotIn("999999999", Path(report["file"]["path"]).read_text())

    def test_a_line_without_a_date_is_not_put_on_every_month(self) -> None:
        code, report = self.go(["INV-1;2026-08-03;Alpha GmbH;DE123456789;1000,00;0,00;services",
                                "INV-2;;Alpha GmbH;DE123456789;500,00;0,00;services"])
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "VS-03"))
        self.assertIn("no date", report["unusable_lines"][0]["why"])
        self.assertEqual(3, report["unusable_lines"][0]["line"])

    def test_line_numbers_are_those_of_the_file(self) -> None:
        code, report = self.go(["", "INV-1;2026-08-03;Alpha GmbH;DE123456789;1000,00;0,00;services", "",
                                "INV-2;2026-08-04;Beta;;5,00;0,00;services"])
        self.assertEqual([5], [line["line"] for line in report["unusable_lines"]])  # blank lines are counted

    def test_a_plain_vat_column_is_read_as_the_vat_amount(self) -> None:
        code, report = self.go(["A;DE123456789;1190;190;services"], header="Invoice;Customer VAT;Amount;VAT;Kind")
        self.assertEqual(2, code)
        self.assertEqual("VAT", report["columns_used"]["vat_amount"])
        self.assertIn("carries VAT of 190.00", report["unusable_lines"][0]["why"])

    def test_a_country_column_and_the_numbers_own_prefix(self) -> None:
        header = "Invoice;Country;Customer VAT;Net;Kind"
        code, report = self.go(["A;FR;AB123456789;100;services", "B;GR;EL123456789;100;services",
                                "C;DE;DE123456789;100;services", "D;IT;00000000001;100;services"], header=header)
        self.assertEqual(0, code)
        self.assertEqual(["DE123456789", "EL123456789", "FRAB123456789", "IT00000000001"],
                         [f"{row['country']}{row['vat_number']}" for row in report["rows"]])
        code, report = self.go(["A;FR;DE123456789;100;services"], header=header)
        self.assertEqual(2, code)
        self.assertIn("the country column says FR and the number starts with DE", report["unusable_lines"][0]["why"])

    def test_only_a_plain_answer_from_vies_is_an_answer_about_the_number(self) -> None:
        spec = importlib.util.spec_from_file_location("vat_return", VAT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.time.sleep = lambda seconds: None
        calls: list[str] = []

        class Reply:
            def __init__(self, body: dict) -> None:
                self.body = json.dumps(body).encode()

            def __enter__(self) -> "Reply":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, *args: object) -> bytes:
                return self.body

        def answer_with(body: dict | Exception) -> None:
            def fake(request: object, timeout: float = 0) -> Reply:
                calls.append(request.full_url)
                if isinstance(body, Exception):
                    raise body
                return Reply(body)
            module.urllib.request.urlopen = fake

        answer_with({"isValid": True, "userError": "VALID", "name": "ALPHA GMBH", "address": "---"})
        found = module.look_up("DE123456789", 1)
        self.assertEqual(("Registered", "ALPHA GMBH", None), (found["answer"], found["name"], found["address"]))
        answer_with({"isValid": False, "userError": "INVALID"})
        self.assertEqual("Not registered", module.look_up("DE123456789", 1)["answer"])
        for code in ("IP_BLOCKED", "VAT_BLOCKED", "INVALID_REQUESTER_INFO", "MS_MAX_CONCURRENT_REQ_TIME", "MS_UNAVAILABLE"):
            answer_with({"isValid": False, "userError": code})
            self.assertEqual("Could not be checked", module.look_up("DE123456789", 1)["answer"], code)
        # No network: the first number tells, and the rest are not waited for.
        answer_with(OSError("no route to host"))
        del calls[:]
        args = type("Args", (), {"vat_numbers": ["DE123456789", "FR12345678901", "IT00000000001"], "timeout": 1})()
        import contextlib
        import io
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            module.command_numbers(args)
        result = json.loads(printed.getvalue())
        self.assertEqual(3, result["could_not_be_checked"])
        self.assertEqual(2, len(calls))  # two tries for the first number, none for the others
        self.assertNotIn("unreachable", result["results"][0])

    def test_a_number_vies_does_not_know_stops_the_file(self) -> None:
        numbers = self.out / "numbers.json"
        numbers.write_text(json.dumps({"results": [{"vat_number": "DE123456789", "answer": "Registered"},
                                                   {"vat_number": "EL123456789", "answer": "Not registered"},
                                                   {"vat_number": "EE100000001", "answer": "Could not be checked"}]}))
        code, report = self.go(self.GOOD, "--numbers", str(numbers))
        self.assertEqual(2, code)
        self.assertEqual(["VS-06"], report["blocks_file"])
        self.assertIn("EL123456789", next(c["detail"] for c in report["checks"] if c["code"] == "VS-06"))
        numbers.write_text(json.dumps({"results": [{"vat_number": n, "answer": "Registered"}
                                                   for n in ("DE123456789", "EL123456789", "EE100000001")]}))
        code, report = self.go(self.GOOD, "--numbers", str(numbers))
        self.assertEqual(0, code)
        self.assertEqual("Passed", self.answer(report, "VS-06"))
        self.assertEqual("Registered", report["rows"][0]["in_vies"])

    def test_a_month_with_nothing_to_report_has_no_file(self) -> None:
        code, report = self.go([self.GOOD[-1]])  # only a July line
        self.assertEqual(2, code)
        self.assertFalse(report["file"]["written"])
        self.assertIn("nothing to report", report["file"]["why"][0])
        self.assertEqual([], report["blocks_file"])
        self.assertEqual("Not relevant", self.answer(report, "VS-02"))
        self.assertEqual([], list(self.out.glob("VIES*")))

    def test_the_kind_of_supply_is_never_assumed(self) -> None:
        source = self.out / "sales.csv"
        source.write_text("Invoice;Customer VAT;Net\nINV-1;DE123456789;1000,00\n")
        said = refused("vies", "--taxpayer", "12345678X", "--month", "2026-08", "--lines", str(source), "--out", str(self.out))
        self.assertIn("no column found for the kind of supply", said)
        self.assertIn("Invoice, Customer VAT, Net", said)
        code, report = self.go(["INV-1;DE123456789;1000,00"], "--default-kind", "services", header="Invoice;Customer VAT;Net")
        self.assertEqual(0, code)
        self.assertEqual(1000, report["rows"][0]["services"])
        self.assertEqual("Could not be checked", self.answer(report, "VS-03"))

    def test_common_column_names_are_found(self) -> None:
        header = "Invoice date,Invoice no,Customer,VAT Reg No,Net EUR,VAT EUR,Goods/Services"
        code, report = self.go(['2026-08-03,INV-1,Alpha GmbH,DE123456789,"1,000.50",0.00,Services'], header=header)
        self.assertEqual(0, code)
        self.assertEqual({"vat_number": "VAT Reg No", "amount": "Net EUR", "kind": "Goods/Services", "date": "Invoice date",
                          "document": "Invoice no", "customer": "Customer", "vat_amount": "VAT EUR"}, report["columns_used"])
        self.assertEqual(1001, report["rows"][0]["services"])
        # The same amount without quotes is cut in two by the comma: the run stops instead of filing "1".
        source = self.out / "cut.csv"
        source.write_text(header + "\n2026-08-03,INV-1,Alpha GmbH,DE123456789,1,000.50,0.00,Services\n")
        said = refused("vies", "--taxpayer", "12345678X", "--month", "2026-08", "--lines", str(source), "--out", str(self.out))
        self.assertIn("more cells than the header", said)

    def test_vat_numbers_are_read_the_way_they_are_printed(self) -> None:
        spec = importlib.util.spec_from_file_location("vat_return", VAT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual("CY12345678X", module.normalise_vat_number("12345678x"))
        self.assertEqual("EL123456789", module.normalise_vat_number("GR 123.456.789"))
        self.assertEqual("DE123456789", module.normalise_vat_number("de-123456789"))
        self.assertEqual(("12345678X", True), module.taxpayer_number("cy 12345678x"))
        self.assertEqual("Could not be checked", module.look_up("EU372000000", 1)["answer"])  # no request is made
        self.assertEqual(module.Decimal("-3"), module.whole(module.Decimal("-2.5")))
        self.assertEqual("0.00", module.money(module.Decimal("-0.004")))


DOC_HEADER = "document,date,type,counterparty,vat_number,country,supply,net,vat,rate,addressed_to_company,treatment,cy_rate,note"
DOCS = ["INV-101,2026-07-03,sale,Local One Ltd,10123451K,,services,4200.00,798.00,19,,,,",
        "INV-102,2026-07-10,sale,Alpha GmbH,DE811234567,,services,2500.00,0,0,,,,",
        "INV-103,2026-07-15,sale,Epsilon Srl,IT01234567890,,goods,3200.00,0,0,,,,",
        "INV-104,2026-07-18,sale,Zeta Trading LLC,,AE,goods,1500.00,0,0,,,,",
        "CN-11,2026-08-14,sale credit note,Local One Ltd,10123451K,,services,500.00,95.00,19,,,,",
        "BILL-301,2026-07-08,purchase,Cyprus Supplier Ltd,10987651P,,services,1200.00,228.00,19,yes,,,",
        "BILL-401,2026-07-15,purchase,Hamburg Parts GmbH,DE129876543,,goods,2000.00,0,0,yes,,,",
        "SCN-21,2026-09-20,purchase credit note,Hamburg Parts GmbH,DE129876543,,goods,400.00,0,0,yes,,,",
        "BILL-403,2026-07-18,purchase,Dublin Cloud Ltd,IE6388047V,,services,800.00,0,0,yes,,,",
        "BILL-405,2026-09-02,purchase,Pacific Software Inc,EU372041234,,services,600.00,0,0,yes,,,",
        "BILL-407,2026-09-12,purchase,Corner Stationery,,CY,goods,150.00,28.50,19,yes,,,",
        "BILL-408,2026-09-13,purchase,Hotel Berlin GmbH,DE111111111,,services,300.00,21.00,7,yes,,,",
        "BILL-409,2026-09-14,purchase,Phone Shop Ltd,10555555P,,goods,900.00,171.00,19,no,,,",
        "BILL-410,2026-10-02,purchase,Cyprus Supplier Ltd,10987651P,,services,300.00,57.00,19,yes,,,"]
SAID = ["--note", "documents=These are all our bills and invoices for the quarter"]


class PrepareFromDocumentsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.out = Path(self.dir.name)

    def tearDown(self) -> None:
        self.dir.cleanup()

    def go(self, lines: list[str], *extra: str) -> tuple[int, dict]:
        source = self.out / "documents.csv"
        source.write_text("\n".join([DOC_HEADER, *lines]) + "\n", encoding="utf-8")
        return run_any(VAT, "prepare", "--from", "2026-07-01", "--to", "2026-09-30", "--documents", str(source),
                       "--out", str(self.out), *extra)

    @staticmethod
    def boxes(report: dict) -> dict[str, str]:
        return {row["box"]: row["amount"] for row in report["boxes"]}

    @staticmethod
    def answer(report: dict, code: str) -> str:
        return next(item["answer"] for item in report["checks"] if item["code"] == code)

    def test_each_document_goes_into_its_boxes_by_rule(self) -> None:
        code, report = self.go(DOCS, *SAID)
        self.assertEqual(0, code)
        self.assertEqual({"read": 14, "in_the_return": 12, "rows_in_the_return": 12, "left_out": 1, "questions": 0,
                          "of_other_periods": {"2026-10": 1}}, report["documents"])
        self.assertEqual("2026-11-10", report["due"]["date"])
        self.assertEqual(["2026-08-15", "2026-09-15", "2026-10-15"], [month["date"] for month in report["vies_due"]])
        groups = {group["treatment"]: group for group in report["by_treatment"]}
        goods = groups["goods from a VAT-registered supplier in another Member State"]
        self.assertEqual(("304.00", ["2", "4", "7", "11A"]), (goods["vat_accounted_for_by_the_company"], goods["boxes"]))
        self.assertEqual({"1": "798.00", "6": "4200.00"}, report["placed"][0]["boxes"])
        self.assertEqual({
            "1": "969.00",    # 798 - 95 (own credit note) + 152 and 114 reverse charge on services
            "2": "304.00",    # 19% of the German goods, less the supplier's credit note
            "3": "1273.00", "4": "798.00", "5": "475.00",
            "6": "12300.00",  # sales, and the two services received under the reverse charge
            "7": "4650.00", "8A": "3200.00", "8B": "2500.00", "9": "1500.00", "10": "0.00",
            "11A": "1600.00",
            "11B": "800.00",  # the Irish supplier only: an EU... number is a business outside the EU
        }, self.boxes(report))
        self.assertEqual(["BILL-407", "BILL-408"], [doc["document"] for doc in report["vat_not_claimed"]])
        self.assertEqual(["BILL-409"], [doc["document"] for doc in report["left_out"]])
        self.assertEqual("Needs a look", self.answer(report, "PD-05"))  # the receipt without a supplier number
        self.assertEqual("Looks right", self.answer(report, "PD-06"))
        self.assertEqual("Could not be checked", self.answer(report, "PD-08"))  # said, and still not checked
        self.assertEqual([f"PD-{n:02d}" for n in range(1, 9)], [item["code"] for item in report["checks"]])
        with open(report["files"]["documents"], encoding="utf-8") as handle:
            trail = {row["document"]: row for row in csv.DictReader(handle)}
        self.assertEqual("-76.00", trail["SCN-21"]["box_2"])
        self.assertEqual("-400.00", trail["SCN-21"]["box_11A"])
        self.assertEqual("", trail["BILL-409"]["box_7"])
        # Foreign VAT alone is no fault of the list: it is listed, and the test passes.
        code, report = self.go([DOCS[0], DOCS[11]], *SAID)
        self.assertEqual("Passed", self.answer(report, "PD-05"))
        self.assertIn("VAT of another country on 1 document", next(c["detail"] for c in report["checks"] if c["code"] == "PD-05"))

    def test_the_draft_waits_for_the_person_to_say_the_documents_are_complete(self) -> None:
        code, report = self.go(DOCS)
        self.assertEqual(2, code)
        self.assertEqual(["PD-08"], report["blocks_file"])
        self.assertFalse(report["files"]["written"])
        self.assertEqual("475.00", self.boxes(report)["5"])  # shown as it would be
        self.assertEqual([], list(self.out.glob("prepared-*")))

    def test_a_document_the_rules_cannot_place_is_asked_about_not_guessed(self) -> None:
        cases = {
            "X-1,2026-07-05,purchase,Mystery Co,,,services,100,0,0,yes,,,": "country is not known",
            "X-2,2026-07-05,sale,Jean Dupont,,FR,services,100,0,0,,,,": "no VAT number",
            "X-3,2026-07-05,sale,Local Two Ltd,10123452K,,services,100,0,0,,,,": "zero rated, exempt or outside the scope",
            "X-4,2026-07-05,purchase,Lyon SARL,FR12345678901,,,100,0,0,yes,,,": "goods or services",
            "X-5,2026-07-05,invoice,Somebody,,,services,100,19,19,,,,": "is not one of",
            "X-6,,sale,Local Two Ltd,10123452K,,services,100,19,19,,,,": "No date",
            "X-7,2026-07-05,sale,Local Two Ltd,10123452K,,services,100,19,19,,zero rated,,": "shows VAT of 19.00",
            "X-8,2026-07-05,purchase,Berlin GmbH,DE811234567,,goods,100,0,0,yes,zero rated,,": "is for a sale",
            "X-9,2026-07-05,sale,Nicosia Co,HE123456,,services,100,0,0,,,,": "country is not known",
            "X-10,2026-07-05,sale,Somewhere Inc,,XX,services,100,0,0,,,,": "not a two-letter country code",
            "X-11,2026-07-05,purchase,Lyon SARL,FR12345678901,,goods,100,0,0,yes,,0.05,": "is not a rate in percent",
            "X-12,2026-07-05,purchase,Local Shop Ltd,10987651P,,goods,100,19,n/a,yes,,,": "is not a rate in percent",
        }
        code, report = self.go(list(cases), *SAID)
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "PD-01"))
        asked = {q["document"]: q["ask"] for q in report["questions"]}
        for line, words in cases.items():
            self.assertIn(words, asked[line.split(",")[0]])
        self.assertEqual({"0.00"}, set(self.boxes(report).values()))

    def test_special_cases_are_stated_not_inferred(self) -> None:
        code, report = self.go([
            "S-1,2026-07-05,sale,Tenant Ltd,10123452K,,services,1000,0,0,,exempt,,",
            "S-2,2026-07-06,sale,Bookshop Ltd,10123453K,,goods,200,0,0,,zero rated,,",
            "S-3,2026-07-07,sale,Oslo AS,,NO,services,300,0,0,,,,",
            "S-4,2026-07-08,sale,Milano Srl,IT01234567890,,triangular,400,0,0,,,,",
            "P-1,2026-07-09,purchase,Paris Bank SA,FR12345678901,,services,500,0,0,yes,,exempt,",
            "P-2,2026-07-10,purchase,Athens Books AE,GR123456789,,goods,600,0,0,yes,,5,",
            "P-3,2026-07-11,import vat,Customs,,,goods,0,190.00,,yes,,,",
            "P-4,2026-07-12,purchase,Shenzhen Co,,CN,goods,1000,0,0,yes,,,",
            "P-5,2026-07-13,purchase,Bakery,,CY,goods,50,9.50,19,yes,not business,,",
        ], *SAID)
        self.assertEqual(0, code)
        boxes = self.boxes(report)
        self.assertEqual("0.00", boxes["1"])
        self.assertEqual("30.00", boxes["2"])        # 5% of the Greek books
        self.assertEqual("220.00", boxes["4"])       # 30 acquisition VAT + 190 import VAT
        self.assertEqual("2400.00", boxes["6"])      # 1000 + 200 + 300 + 400 sales, 500 exempt service received
        self.assertEqual("2100.00", boxes["7"])
        self.assertEqual("200.00", boxes["9"])
        self.assertEqual("700.00", boxes["10"])      # the service to Norway and the triangular sale
        self.assertEqual("600.00", boxes["11A"])
        self.assertEqual("500.00", boxes["11B"])
        self.assertEqual("Worth a look", self.answer(report, "PD-07"))  # an exempt sale: deduction may be partial
        self.assertEqual(["P-5"], [doc["document"] for doc in report["left_out"]])
        self.assertIn("customs declaration", report["notes"][0]["note"])
        self.assertEqual(1, report["vies_lines"])

    def test_misreadings_show(self) -> None:
        code, report = self.go(["INV-001,2026-07-03,sale,Local One Ltd,10123451K,,services,1000.00,109.00,19,,,,",
                                "INV-002,2026-07-04,sale,Local One Ltd,10123451K,,services,100.00,19.00,19,,,,",
                                "INV-002,2026-07-04,sale,Local One Ltd,10123451K,,services,100.00,19.00,19,,,,",
                                "INV-005,2026-07-06,sale,Local One Ltd,10123451K,,services,100.00,19.00,19,,,,"], *SAID)
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "PD-04"))  # 109 is not 19% of 1000
        self.assertEqual("Needs a look", self.answer(report, "PD-02"))  # INV-002 twice
        self.assertEqual("Worth a look", self.answer(report, "PD-06"))  # INV-003 and INV-004 are not there
        self.assertIn("INV-003, INV-004", next(c["detail"] for c in report["checks"] if c["code"] == "PD-06"))
        self.assertEqual(["PD-02", "PD-04"], report["blocks_file"])

    def test_two_rows_of_one_document_are_not_a_duplicate(self) -> None:
        code, report = self.go(["INV-1,2026-07-03,sale,Alpha GmbH,DE811234567,,goods,1000,0,0,,,,",
                                "INV-1,2026-07-03,sale,Alpha GmbH,DE811234567,,services,200,0,0,,,,"], *SAID)
        self.assertEqual(0, code)
        self.assertEqual(("1000.00", "200.00"), (self.boxes(report)["8A"], self.boxes(report)["8B"]))
        self.assertEqual(1, report["documents"]["in_the_return"])
        self.assertEqual(2, report["documents"]["rows_in_the_return"])

    def test_a_big_gap_in_the_numbering_is_still_a_gap(self) -> None:
        code, report = self.go(["INV-1,2026-07-03,sale,Local One Ltd,10123451K,,services,100,19,19,,,,",
                                "INV-2,2026-07-04,sale,Local One Ltd,10123451K,,services,100,19,19,,,,",
                                "INV-20260050,2026-07-05,sale,Local One Ltd,10123451K,,services,100,19,19,,,,",
                                ",2026-07-06,sale,Local One Ltd,10123451K,,services,100,19,19,,,,"], *SAID)
        self.assertEqual("Worth a look", self.answer(report, "PD-06"))
        self.assertIn("20260047 numbers between", next(c["detail"] for c in report["checks"] if c["code"] == "PD-06"))

    def test_a_long_bill_rounded_line_by_line_is_not_a_misreading(self) -> None:
        code, report = self.go(["B-1,2026-07-03,purchase,Wholesale Ltd,10987651P,,goods,1000.00,190.12,19,yes,,,",
                                "B-2,2026-07-03,purchase,Corner Shop,,CY,goods,10.00,3.00,19,no,,,"], *SAID)
        self.assertEqual(0, code)
        self.assertEqual("Passed", self.answer(report, "PD-04"))  # 12 cents on 190; B-2 touches no box

    def test_a_receipt_made_out_to_no_one_does_not_carry_a_claim(self) -> None:
        code, report = self.go(["R-1,2026-07-03,purchase,Stationery Ltd,10987651P,,goods,150.00,28.50,19,not shown,,,"], *SAID)
        self.assertEqual(0, code)
        self.assertEqual(("0.00", "150.00"), (self.boxes(report)["4"], self.boxes(report)["7"]))
        self.assertIn("ask the supplier for a VAT invoice", report["vat_not_claimed"][0]["why"])
        self.assertEqual("Needs a look", self.answer(report, "PD-05"))

    def test_another_currency_and_dates_in_words(self) -> None:
        header = DOC_HEADER.replace(",net,", ",currency,net,")
        source = self.out / "documents.csv"
        source.write_text(header + "\nPS-1,\"September 2, 2026\",purchase,Pacific Inc,,US,services,USD,650,0,,yes,,,\n"
                          "DC-1,18 July 2026,purchase,Dublin Cloud Ltd,IE6388047V,,services,EUR,800,0,,yes,,,\n")
        code, report = run_any(VAT, "prepare", "--from", "2026-07-01", "--to", "2026-09-30", "--documents", str(source),
                               "--out", str(self.out), *SAID)
        self.assertEqual(2, code)
        self.assertEqual(["PS-1"], [q["document"] for q in report["questions"]])
        self.assertIn("is in USD", report["questions"][0]["ask"])
        self.assertEqual("800.00", self.boxes(report)["11B"])  # 18 July 2026 was read
        # The person gives the euro amount: it is used, and shown as theirs.
        header = header.replace(",net,", ",euro_amount_from,net,")
        source.write_text(header + "\nPS-1,2026-09-02,purchase,Pacific Inc,,US,services,USD,\"card statement, per the person\","
                          "598.00,0,,yes,,,\n")
        code, report = run_any(VAT, "prepare", "--from", "2026-07-01", "--to", "2026-09-30", "--documents", str(source),
                               "--out", str(self.out), *SAID)
        self.assertEqual(0, code)
        self.assertEqual("113.62", self.boxes(report)["1"])
        self.assertEqual("USD", report["euro_amounts_not_on_the_document"][0]["currency"])

    def test_no_draft_outlives_a_later_run_and_an_empty_period_is_not_nil(self) -> None:
        code, report = self.go(DOCS, *SAID)
        self.assertEqual(0, code)
        self.assertTrue((self.out / "prepared-vies-lines.csv").exists())
        code, report = self.go(DOCS[:1] + ["X-1,2026-07-05,purchase,Mystery Co,,,services,100,0,0,yes,,,"], *SAID)
        self.assertEqual(2, code)
        self.assertEqual([], list(self.out.glob("prepared-*")))  # the held draft left nothing to build from
        code, report = self.go(["INV-1,2025-07-03,sale,Local One Ltd,10123451K,,services,100,19,19,,,,"], *SAID)
        self.assertEqual(2, code)
        self.assertEqual("Needs a look", self.answer(report, "PD-01"))
        self.assertIn("No document of the list is dated in the period", report["files"]["why"][0])

    def test_from_documents_to_the_files_for_the_portal(self) -> None:
        code, draft = self.go(DOCS, *SAID)
        self.assertEqual(0, code)
        results = []
        for month in ("2026-07", "2026-08", "2026-09"):
            done = subprocess.run([sys.executable, "-I", str(VAT), "vies", "--taxpayer", "CY12345678X", "--month", month,
                                   "--lines", draft["files"]["vies_lines"], "--out", str(self.out)],
                                  capture_output=True, text=True)
            result = self.out / f"vies-{month}.json"
            result.write_text(done.stdout)
            results += ["--vies-result", str(result)]
        july = json.loads((self.out / "vies-2026-07.json").read_text())
        self.assertEqual({"goods": 3200, "triangular": 0, "services": 2500, "rows": 2}, july["totals"])
        self.assertEqual("Passed", next(c["answer"] for c in july["checks"] if c["code"] == "VS-04"))
        code, report = run_any(VAT, "xml", "--taxpayer", "CY12345678X", "--from", "2026-07-01", "--to", "2026-09-30",
                               "--boxes", draft["files"]["boxes"], *results, "--out", str(self.out))
        self.assertEqual(0, code)
        self.assertEqual([], report["blocks_file"])
        self.assertEqual("prepared from 12 documents", report["boxes"][0]["source"])
        self.assertEqual("These are all our bills and invoices for the quarter", report["prepared"]["statement"])
        path = Path(report["file"]["path"])
        self.assertIn("<mof:total-from-eu-supplied-services>800,00</mof:total-from-eu-supplied-services>", path.read_text())
        if validates(path, "cy-f4-2010-declaration.xsd") is not None:
            self.assertTrue(validates(path, "cy-f4-2010-declaration.xsd"))
        # A draft for one period is not used for another.
        said = refused("check", "--taxpayer", "CY12345678X", "--from", "2026-10-01", "--to", "2026-12-31",
                       "--boxes", draft["files"]["boxes"])
        self.assertIn("was prepared for 2026-07-01 to 2026-09-30", said)
        # Figures changed by hand are no longer "prepared from 12 documents".
        boxes = Path(draft["files"]["boxes"])
        boxes.write_text(boxes.read_text().replace('"4": "798.00"', '"4": "998.00"'))
        said = refused("check", "--taxpayer", "CY12345678X", "--from", "2026-07-01", "--to", "2026-09-30", "--boxes", str(boxes))
        self.assertIn("not the ones prepare wrote", said)


if __name__ == "__main__":
    unittest.main(verbosity=1)
