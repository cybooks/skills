#!/usr/bin/env python3
"""Cyprus VAT return and VIES statement: the checks, and the XML files for upload to TFA.

    python3 vat_return.py check   --taxpayer CY12345678X --from 2026-07-01 --to 2026-09-30 --boxes boxes.csv
    python3 vat_return.py xml     the same arguments, plus --out DIR: the checks, then the VAT return file
    python3 vat_return.py vies    --taxpayer CY12345678X --month 2026-08 --lines sales.csv --default-kind services --out DIR
    python3 vat_return.py numbers DE123456789 12345678X
    python3 vat_return.py prepare --from 2026-07-01 --to 2026-09-30 --documents documents.csv --out DIR

Output: JSON on stdout. Standard library only. All figures are in euros. No file is written while a
test that stops it is open. Nothing is sent anywhere, except by `numbers`, which asks the EU's VIES
service whether a VAT number is registered.

Exit code: 0 done; 2 `xml`, `vies` or `prepare` wrote no file (the output says why); 1 the input could not be
read (the reason is on stderr, with no JSON). `check` and `numbers` exit 0 whatever they find.
Run each command with --help for every option.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

NAMESPACE = "http://www.mof.gov.cy"
SCHEMA_VERSION = "2010-1.0"
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "assets" / "schemas"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_VIES_ROWS = 12000
NIL_WORDS = {"nil", "none", "zero", "-"}

# Box, XML element, kind (a VAT amount with cents, or a value in whole euros), label.
BOXES = [
    ("1", "due-outflow-vat", "vat", "VAT due on sales and other outputs"),
    ("2", "due-eu-acquisition-vat", "vat", "VAT due on acquisitions of goods from other Member States"),
    ("3", "due-vat-total", "vat", "Total VAT due (box 1 + box 2)"),
    ("4", "deducted-eu-acquisition-vat", "vat", "VAT reclaimed on purchases and other inputs"),
    ("5", "total-vat", "vat", "VAT payable or refundable (box 3 - box 4)"),
    ("6", "total-outflows", "value", "Total value of sales and other outputs, excluding VAT"),
    ("7", "total-inflows", "value", "Total value of purchases and other inputs, excluding VAT"),
    ("8A", "total-to-eu-services", "value", "Supplies of goods to other Member States"),
    ("8B", "total-to-eu-supplied-services", "value", "Services supplied to other Member States"),
    ("9", "total-to-eu-zero-services", "value", "Zero rated outputs, other than boxes 8A and 8B"),
    ("10", "total-sales", "value", "Sales outside the scope with the right to deduct, other than box 8B"),
    ("11A", "total-from-eu-services", "value", "Acquisitions of goods from other Member States"),
    ("11B", "total-from-eu-supplied-services", "value", "Services received from other Member States"),
]
BOX_KEYS = [box for box, _, _, _ in BOXES]
VALUE_BOXES = [box for box, _, kind, _ in BOXES if kind == "value"]

# The member states a VIES row may name: the schema's list, without Cyprus itself and without GB.
# XI is Northern Ireland, for goods only.
VIES_COUNTRIES = {"AT", "BE", "BG", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU",
                  "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "XI"}
VIES_LOOKUP_COUNTRIES = VIES_COUNTRIES | {"CY"}
VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{country}/vat/{number}"

ALIASES = {
    "vat_number": ["customer vat number", "customer vat", "customer vat id", "customer vat no", "vat number", "vat no",
                   "vat id", "vat reg no", "vat reg number", "vat reg", "vat registration number", "vat registration no",
                   "tax number"],
    "country": ["country", "country code", "customer country"],
    "amount": ["net", "net amount", "net eur", "amount", "value", "total excl vat", "subtotal"],
    "kind": ["kind", "supply", "supply type", "type of supply", "goods or services", "goods/services", "goods / services"],
    "date": ["date", "invoice date", "issue date", "document date"],
    "document": ["document", "doc", "number", "invoice", "invoice number", "invoice no", "document number", "reference"],
    "customer": ["customer", "customer name", "client", "name"],
    "vat_amount": ["vat amount", "vat eur", "vat charged", "tax amount", "vat", "tax"],
}
KINDS = {"goods": "goods", "good": "goods", "supplies": "goods", "g": "goods",
         "services": "services", "service": "services", "s": "services",
         "triangular": "triangular", "triangle": "triangular", "triangulation": "triangular", "t": "triangular"}

CENT = Decimal("0.01")
ZERO = Decimal("0")
PASSED, NEEDS, NOT_CHECKED, NOT_RELEVANT = "Passed", "Needs a look", "Could not be checked", "Not relevant"
LOOKS_RIGHT, WORTH = "Looks right", "Worth a look"
COUNT_KEYS = {PASSED: "passed", NEEDS: "needs_a_look", NOT_CHECKED: "could_not_be_checked",
              NOT_RELEVANT: "not_relevant", LOOKS_RIGHT: "looks_right", WORTH: "worth_a_look"}


def norm(text: str) -> str:
    return re.sub(r"[\s_\-]+", " ", (text or "").strip().lower())


def bare(text: str) -> str:
    """The figure without a euro sign or EUR around it."""
    return re.sub(r"^(EUR|€)\s*|\s*(EUR|€)$", "", text.strip(), flags=re.I).strip()


def detect_decimal(samples: list[str]) -> str:
    samples = [bare(s) for s in samples]
    comma = sum(1 for s in samples if re.search(r",\d{1,2}\)?-?$", s))
    point = sum(1 for s in samples if re.search(r"\.\d{1,2}\)?-?$", s))
    # No decimals anywhere: 135.000 is a hundred and thirty-five thousand, not 135.
    dot_grouped = sum(1 for s in samples if re.fullmatch(r"[-(]?\d{1,3}(\.\d{3})+\)?-?", s))
    comma_grouped = sum(1 for s in samples if re.fullmatch(r"[-(]?\d{1,3}(,\d{3})+\)?-?", s))
    if (comma and point) or (dot_grouped and comma_grouped and not comma and not point):
        sys.exit("The figures mix two number formats (1.234,56 and 1,234.56). Write them one way, or say which "
                 "is meant with --decimal comma or --decimal point.")
    if comma or point:
        return "comma" if comma else "point"
    return "comma" if dot_grouped else "point"


def parse_amount(raw: object, decimal: str, where: str) -> Decimal:
    """A figure for a tax return is never guessed: text that is not plainly one number stops the run."""
    if isinstance(raw, bool) or raw is None:
        sys.exit(f"{where}: not a number: {raw!r}")
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    body = bare(str(raw))
    negative = False
    if body.startswith("(") and body.endswith(")"):
        negative, body = True, body[1:-1].strip()
    elif body.startswith("-"):
        negative, body = True, body[1:].strip()
    elif body.endswith("-"):
        negative, body = True, body[:-1].strip()
    if re.search(r"\s", body):  # 12 345,67: a space only between groups of three digits
        if not re.fullmatch(r"\d{1,3}(\s\d{3})+([.,]\d+)?", body):
            sys.exit(f"{where}: not a number: {raw!r}")
        body = re.sub(r"\s", "", body)
    if not re.fullmatch(r"[\d.,]+", body) or not re.search(r"\d", body):
        sys.exit(f"{where}: not a number: {raw!r}")
    group, mark = (r"\.", ",") if decimal == "comma" else (",", r"\.")
    match = re.fullmatch(rf"(\d{{1,3}}(?:{group}\d{{3}})+|\d+)(?:{mark}(\d+))?", body)
    if not match:
        sys.exit(f"{where}: {raw!r} does not read as a number with a decimal {decimal}. Say which format is meant "
                 "with --decimal comma or --decimal point.")
    if match.group(2) and len(match.group(2)) == 3 and re.fullmatch(r"[1-9]\d{0,2}", match.group(1)):
        sys.exit(f"{where}: {raw!r} can be read two ways (a thousands separator, or three decimals). Write it "
                 "without the separator.")
    digits = body.replace(".", "").replace(",", ".") if decimal == "comma" else body.replace(",", "")
    try:
        value = Decimal(digits)
    except InvalidOperation:
        sys.exit(f"{where}: not a number: {raw!r}")
    return -value if negative else value


def money(value: Decimal) -> str:
    cents = value.quantize(CENT, rounding=ROUND_HALF_UP)
    return f"{cents if cents else ZERO.quantize(CENT):.2f}"  # never -0.00


def whole(value: Decimal) -> Decimal:
    """Whole euros, half up. Python's round() rounds half to even, which a tax form does not."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def taxpayer_number(raw: str) -> tuple[str, bool]:
    text = re.sub(r"[\s.\-]", "", (raw or "").upper())
    if text.startswith("CY"):
        text = text[2:]
    return text, bool(re.fullmatch(r"\d{8}[A-Z]", text))


def parse_date(raw: str, option: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        sys.exit(f"{option}: expected a date as YYYY-MM-DD, got {raw!r}")


def parse_line_date(raw: str) -> date | None:
    """ISO, or day first as Cyprus writes it (31/08/2026, 31.08.2026). None when it is neither."""
    text = raw.strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})", raw.strip().split(" ")[0])
    if not match:
        return date_in_words(raw)
    try:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


MONTHS = {name: number for number, names in enumerate(
    ["january jan", "february feb", "march mar", "april apr", "may", "june jun", "july jul", "august aug",
     "september sep sept", "october oct", "november nov", "december dec"], start=1) for name in names.split()}


def date_in_words(raw: str) -> date | None:
    """18 July 2026, or July 18, 2026: a month in words leaves no doubt which number is the day."""
    words = re.sub(r"[,.]", " ", raw.strip().lower()).split()
    if len(words) != 3:
        return None
    if words[0] in MONTHS:
        words = [words[1], words[0], words[2]]
    day = re.sub(r"(st|nd|rd|th)$", "", words[0])
    if words[1] not in MONTHS or not day.isdigit() or not re.fullmatch(r"\d{4}", words[2]):
        return None
    try:
        return date(int(words[2]), MONTHS[words[1]], int(day))
    except ValueError:
        return None


def month_end(day: date) -> date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def parse_pairs(pairs: list[str], option: str, allowed: list[str] | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not value.strip() or (allowed is not None and key not in allowed):
            hint = f" with a key of: {', '.join(allowed)}" if allowed else ""
            sys.exit(f"{option} {pair}: expected KEY=VALUE{hint}")
        out[key] = value.strip()
    return out


def read_csv(path: str) -> tuple[list[str], list[dict[str, str]], list[int]]:
    """Header, rows, and the line of the file each row ends on (the header is line 1)."""
    try:
        handle = open(path, newline="", encoding="utf-8-sig")
    except OSError as error:
        sys.exit(f"{path}: {error.strerror}")
    with handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        header = reader.fieldnames or []
        rows, line_numbers = [], []
        for row in reader:
            if None in row:
                # More cells than the header: almost always an amount such as 1,234.56 written without
                # quotes, which the delimiter has cut in two. Reading on would file the first half.
                sys.exit(f"{path} line {reader.line_num}: more cells than the header has columns. Put quotes "
                         "around an amount that contains the delimiter.")
            rows.append({key: (value or "") for key, value in row.items()})  # a shorter row: empty cells
            line_numbers.append(reader.line_num)
    return header, rows, line_numbers


def check(code: str, title: str, grade: str, answer: str, detail: str, blocks: bool = False, holds: bool = False) -> dict:
    """`blocks`: an open answer stops the file. `holds`: so does this answer, whatever it is."""
    return {"code": code, "title": title, "grade": grade, "answer": answer, "detail": detail,
            "blocks_file": bool(holds or (blocks and answer in (NEEDS, WORTH)))}


def count(checks: list[dict]) -> dict[str, int]:
    counts = {key: 0 for key in COUNT_KEYS.values()}
    for item in checks:
        counts[COUNT_KEYS[item["answer"]]] += 1
    return counts


def schema_check(xml_text: str, schema_file: str) -> dict:
    """Validates against the Tax Department's published schema, with whichever validator is here."""
    schema = SCHEMA_DIR / schema_file
    if not schema.exists():
        return {"ran": False, "why": f"the schema files are not beside the script ({SCHEMA_DIR})"}
    try:
        from lxml import etree  # type: ignore
    except ImportError:
        etree = None
    if etree is not None:
        validator = etree.XMLSchema(etree.parse(str(schema)))
        valid = validator.validate(etree.fromstring(xml_text.encode("utf-8")))
        return {"ran": True, "with": "lxml", "schema": schema_file, "valid": bool(valid),
                "errors": [str(error) for error in validator.error_log][:10]}
    xmllint = shutil.which("xmllint")
    if xmllint:
        with tempfile.TemporaryDirectory() as folder:
            draft = Path(folder) / "draft.xml"
            draft.write_text(xml_text, encoding="utf-8")
            done = subprocess.run([xmllint, "--noout", "--nonet", "--schema", str(schema), str(draft)],
                                  capture_output=True, text=True)
        errors = [line.replace(str(draft), "file") for line in done.stderr.splitlines() if "validates" not in line]
        return {"ran": True, "with": "xmllint", "schema": schema_file, "valid": done.returncode == 0,
                "errors": errors[:10]}
    return {"ran": False, "why": "no XML schema validator here (lxml or xmllint). The script's own format "
                                 "checks ran; TFA checks the file against the schema on upload."}


def write_file(out_dir: str, name: str, xml_text: str, schema_file: str, replace: bool, checks: list[dict],
               read_back_code: str, read_back: str | None) -> dict:
    """Writes the file only when nothing stops it. Returns the `file` part of the output."""
    title = "The file holds the figures that were tested"
    blocking = [f"{item['code']} {item['title']}: {item['detail']}" for item in checks if item["blocks_file"]]
    if blocking:
        checks.append(check(read_back_code, title, "worked out", NOT_CHECKED, "No file was built."))
        return {"written": False, "why": blocking}
    if read_back:
        checks.append(check(read_back_code, title, "worked out", NEEDS, read_back, blocks=True))
        return {"written": False, "why": [f"{read_back_code} {title}: {read_back}"]}
    checks.append(check(read_back_code, title, "worked out", PASSED, "Read back from the XML and compared, figure by figure."))
    size = len(xml_text.encode("utf-8"))
    if size > MAX_FILE_BYTES:
        return {"written": False, "why": [f"The file would be {size} bytes. The portal takes at most 4 MB."]}
    schema = schema_check(xml_text, schema_file)
    if schema["ran"] and not schema["valid"]:
        return {"written": False, "why": ["The file does not pass the published schema."] + schema["errors"],
                "schema": schema}
    path = (Path(out_dir) / name).resolve()
    if path.exists() and not replace:
        return {"written": False, "schema": schema,
                "why": [f"{path} exists. A file that was uploaded is kept as it is; pass --replace only for a draft "
                        "that was never uploaded."]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(xml_text.encode("utf-8"))  # not write_text: Windows would turn \n into \r\n
    return {"written": True, "path": str(path), "name": name, "bytes": size,
            "sha256": hashlib.sha256(xml_text.encode("utf-8")).hexdigest(), "schema": schema}


def due_info(due: date, basis: str, today: date) -> dict:
    days = (due - today).days
    return {"date": str(due), "basis": basis, "days_left": days, "passed": days < 0,
            "note": "The Tax Department sometimes extends a date. Confirm it on the portal."}


def months_of(start: date, end: date) -> list[str]:
    months, day = [], start.replace(day=1)
    while day <= end:
        months.append(f"{day:%Y-%m}")
        day = add_months(day, 1)
    return months


# ---------------------------------------------------------------------------------------------
# The VAT return
# ---------------------------------------------------------------------------------------------

def box_key(raw: object) -> str | None:
    text = re.sub(r"^BOX", "", re.sub(r"[\s._\-]", "", str(raw).upper()))
    return text if text in BOX_KEYS else None


def no_repeats(pairs: list[tuple[str, object]]) -> dict:
    keys = [key for key, _ in pairs]
    twice = sorted({key for key in keys if keys.count(key) > 1})
    if twice:
        raise ValueError(f"given twice: {', '.join(twice)}")
    return dict(pairs)


def read_boxes(args: argparse.Namespace) -> dict[str, object]:
    raw: dict[str, object] = {}

    def put(key: object, value: object, where: str) -> None:
        box = box_key(key)
        if box is None:
            sys.exit(f"{where}: {key!r} is not a box. Boxes: {', '.join(BOX_KEYS)}")
        if box in raw:
            sys.exit(f"{where}: box {box} is given twice")
        if value is None or (isinstance(value, str) and not value.strip()):
            return  # an empty cell is a box without a figure, not a zero
        raw[box] = value

    if args.boxes:
        if args.boxes.lower().endswith(".json"):
            try:
                with open(args.boxes, encoding="utf-8") as handle:
                    data = json.load(handle, object_pairs_hook=no_repeats)
            except (OSError, ValueError) as error:
                sys.exit(f"{args.boxes}: {error}")
            if isinstance(data, dict) and isinstance(data.get("prepared"), dict):
                args.prepared = data["prepared"]  # written by the prepare command
                written = {str(box): str(amount) for box, amount in (data.get("boxes") or {}).items()}
                if args.prepared.get("seal") != seal(written):
                    sys.exit(f"{args.boxes}: the figures are not the ones prepare wrote. Run prepare again, or give "
                             "the figures as your own, without the 'prepared' part.")
            data = data.get("boxes", data) if isinstance(data, dict) else data
            if isinstance(data, dict):
                for key, value in data.items():
                    put(key, value, args.boxes)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and ("box" in item or "slug" in item) and "amount" in item:
                        put(item.get("box", item.get("slug")), item["amount"], args.boxes)
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        put(item[0], item[-1], args.boxes)
                    else:
                        sys.exit(f"{args.boxes}: expected a list of [box, amount] or of {{box, amount}}")
            else:
                sys.exit(f"{args.boxes}: expected an object of box to amount")
        else:
            header, rows, _ = read_csv(args.boxes)
            by_norm = {norm(h): h for h in header}
            box_col = next((by_norm[n] for n in ("box", "box no", "box number", "field") if n in by_norm), None)
            amount_col = next((by_norm[n] for n in ("amount", "value", "figure", "eur", "total") if n in by_norm), None)
            if not box_col or not amount_col:
                sys.exit(f"{args.boxes}: need the columns 'box' and 'amount'. Columns: {', '.join(header)}")
            for row in rows:
                if row[box_col].strip():
                    put(row[box_col], row[amount_col], args.boxes)
    for pair in args.box:
        key, sep, value = pair.partition("=")
        if not sep:
            sys.exit(f"--box {pair}: expected BOX=AMOUNT")
        put(key, value, "--box")
    return raw


def read_vies_statements(args: argparse.Namespace, months: list[str]) -> tuple[dict[str, dict], list[str]]:
    """The monthly VIES statements of the period, as given: typed (--vies) or built here (--vies-result)."""
    given: dict[str, dict] = {}
    strings: list[str] = []

    def put(month: str, entry: dict, where: str) -> None:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            sys.exit(f"{where}: expected a month as YYYY-MM, got {month!r}")
        if month in given:
            sys.exit(f"{where}: the statement of {month} is given twice")
        if month not in months:
            sys.exit(f"{where}: {month} is not a month of the period")
        given[month] = entry

    for item in args.vies:
        month, sep, rest = item.partition(":")
        pieces = [piece.strip() for piece in rest.split(",")] if sep else []
        parts = dict(piece.split("=", 1) for piece in pieces if "=" in piece)
        if (any("=" not in piece for piece in pieces) or len(parts) != len(pieces)
                or set(parts) - {"goods", "triangular", "services", "rows"}
                or not {"goods", "triangular", "services"} <= set(parts)):
            sys.exit(f"--vies {item}: expected MONTH:goods=N,triangular=N,services=N and optionally rows=N. "
                     "All three amounts are stated, with 0 for none, in whole euros and without a comma.")
        if "rows" in parts and not parts["rows"].isdigit():
            sys.exit(f"--vies {item}: rows is a whole number")
        strings += [parts[kind] for kind in ("goods", "triangular", "services")]
        put(month.strip(), {"raw": parts, "rows": int(parts["rows"]) if "rows" in parts else None, "source": "given"}, f"--vies {item}")
    for path in args.vies_result:
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            totals, month = data["totals"], data["month"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            sys.exit(f"--vies-result {path}: not the output of the vies command ({error})")
        entry = {"rows": totals["rows"], "source": f"built here ({Path(path).name})"}
        entry.update({kind: Decimal(totals[kind]) for kind in ("goods", "triangular", "services")})
        if data.get("blocks_file"):  # its own tests stopped it; an existing file or a nil month did not
            entry["not_built"] = ", ".join(data["blocks_file"])
        put(month, entry, f"--vies-result {path}")
    return given, strings


def return_checks(args: argparse.Namespace) -> tuple[dict, dict[str, Decimal], list[dict]]:
    taxpayer, taxpayer_ok = taxpayer_number(args.taxpayer)
    start, end = parse_date(args.start, "--from"), parse_date(args.end, "--to")
    if start > end:
        sys.exit("--from is after --to")
    today = parse_date(args.today, "--today") if args.today else date.today()
    months = months_of(start, end)
    notes = parse_pairs(args.note, "--note", ["box2", "box8a", "box8b"])
    args.prepared = None
    raw = read_boxes(args)
    if args.prepared and (args.prepared.get("from"), args.prepared.get("to")) != (str(start), str(end)):
        sys.exit(f"--boxes: the draft was prepared for {args.prepared.get('from')} to {args.prepared.get('to')}, "
                 f"not for {start} to {end}")
    statements, vies_strings = read_vies_statements(args, months)
    nil = {box for box, value in raw.items() if isinstance(value, str) and value.strip().lower() in NIL_WORDS}
    strings = [value for box, value in raw.items() if isinstance(value, str) and box not in nil] + vies_strings
    decimal = detect_decimal(strings) if args.decimal == "auto" else args.decimal
    rate = Decimal(str(args.standard_rate)) / 100
    rate_text = f"{args.standard_rate:g}%"

    amounts: dict[str, Decimal] = {box: ZERO if box in nil else parse_amount(value, decimal, f"box {box}")
                                   for box, value in raw.items()}
    drafted = f"prepared from {args.prepared.get('documents')} documents" if args.prepared else "given"
    source: dict[str, str] = {box: "given as nil" if box in nil else drafted for box in amounts}
    for month, entry in statements.items():
        for kind, text in entry.pop("raw", {}).items():
            if kind != "rows":
                entry[kind] = parse_amount(text, decimal, f"--vies {month} {kind}")
        if entry["rows"] is None and all(entry[kind] == ZERO for kind in ("goods", "triangular", "services")):
            entry["rows"] = 0  # a month with nothing to report has no row to round
    missing = [box for box in BOX_KEYS if box not in amounts and box not in ("3", "5")]
    if args.missing_zero:
        for box in missing:
            amounts[box], source[box] = ZERO, "zero, as told"
    checks: list[dict] = []
    still_missing = [box for box in BOX_KEYS if box not in amounts and box not in ("3", "5")]
    checks.append(check("VR-01", "Every box has a figure", "worked out",
                        NEEDS if still_missing else PASSED,
                        (f"No figure for box {', '.join(still_missing)}. Every box is completed, with 0 where nothing "
                         "applies. Give the figure, or pass --missing-zero once the person has said these are nil.")
                        if still_missing else
                        ("All thirteen boxes." + (f" Set to 0 as told: {', '.join(missing)}." if missing and args.missing_zero else "")),
                        blocks=True))

    def have(*boxes: str) -> bool:
        return all(box in amounts for box in boxes)

    def missing_of(*boxes: str) -> str:
        return f"Needs box {', '.join(box for box in boxes if box not in amounts)}."

    finer = [box for box in ("1", "2", "3", "4", "5") if box in amounts and amounts[box] != amounts[box].quantize(CENT)]
    checks.append(check("VR-02", "Boxes 1 to 5 are in euros and cents", "worked out", NEEDS if finer else PASSED,
                        f"More than two decimals: {', '.join(f'box {box} {amounts[box]}' for box in finer)}. Give each "
                        "figure to the cent, as the books hold it." if finer else "None has more than two decimals.",
                        blocks=True))

    # Whole euros before the value tests: they run on the figures that go into the file.
    rounded: list[str] = []
    not_whole = [box for box in VALUE_BOXES if box in amounts and amounts[box] != whole(amounts[box])]
    if args.round_values:
        for box in not_whole:
            rounded.append(f"box {box}: {money(amounts[box])} to {money(whole(amounts[box]))}")
            source[box] = f"rounded to the euro, from {money(amounts[box])}"
            amounts[box] = whole(amounts[box])
        not_whole = []
    checks.append(check("VR-03", "Boxes 6 to 11B are in whole euros", "worked out",
                        NEEDS if not_whole else PASSED,
                        (f"Not whole: {', '.join(f'box {box} {money(amounts[box])}' for box in not_whole)}. "
                         "Pass --round-values to round each to the nearest euro, half up.") if not_whole else
                        ("Rounded half up: " + "; ".join(rounded) + "." if rounded else "All whole."), blocks=True))

    # Boxes 3 and 5 are sums of other boxes: worked out when they are not given, compared when they are.
    for box, parts, sign, code, title in (("3", ("1", "2"), 1, "VR-04", "Box 3 is box 1 plus box 2"),
                                          ("5", ("3", "4"), -1, "VR-05", "Box 5 is box 3 minus box 4")):
        if not have(*parts):
            checks.append(check(code, title, "worked out", NOT_CHECKED, missing_of(*parts)))
            continue
        expected = amounts[parts[0]] + sign * amounts[parts[1]]
        if box not in amounts:
            amounts[box], source[box] = expected, "worked out from the other boxes"
            checks.append(check(code, title, "worked out", PASSED, f"Box {box} was not given. Worked out: {money(expected)}."))
        else:
            ok = amounts[box] == expected
            checks.append(check(code, title, "worked out", PASSED if ok else NEEDS,
                                f"Box {box} is {money(amounts[box])}; the other two give {money(expected)}."
                                + ("" if ok else f" Difference {amounts[box] - expected}."), blocks=True))

    for code, title, total, parts in (("VR-06", "Box 6 covers boxes 8A, 8B, 9, 10 and 11B", "6", ("8A", "8B", "9", "10", "11B")),
                                      ("VR-07", "Box 7 covers boxes 11A and 11B", "7", ("11A", "11B"))):
        if not have(total, *parts):
            checks.append(check(code, title, "worked out", NOT_CHECKED, missing_of(total, *parts)))
            continue
        inside = sum((amounts[box] for box in parts), ZERO)
        # Each box is rounded to the euro on its own, so the parts can exceed the whole by the rounding.
        allowed = Decimal("0.5") * (1 + sum(1 for box in parts if amounts[box] != ZERO))
        short = inside - amounts[total]
        ok = short <= allowed
        checks.append(check(code, title, "worked out", PASSED if ok else NEEDS,
                            f"Box {total} is {money(amounts[total])}; the boxes inside it add up to {money(inside)}."
                            + (f" Short by {money(short)}, allowed {money(allowed)} for the rounding of each box."
                               if short > ZERO else ""), blocks=True))

    title = f"Box 2 against {rate_text} of box 11A"
    if not have("2", "11A"):
        checks.append(check("VR-08", "Box 2 has acquisitions behind it in box 11A", "worked out", NOT_CHECKED, missing_of("2", "11A")))
        checks.append(check("VR-09", title, "scored", NOT_CHECKED, missing_of("2", "11A")))
    else:
        orphan = amounts["2"] > ZERO and amounts["11A"] < Decimal("0.5")
        checks.append(check("VR-08", "Box 2 has acquisitions behind it in box 11A", "worked out",
                            NEEDS if orphan else PASSED,
                            f"Box 2 is {money(amounts['2'])} and box 11A is {money(amounts['11A'])}."
                            + (" VAT on acquisitions needs the value of the goods in box 11A. Reverse charge VAT on "
                               "services belongs in box 1." if orphan else ""), blocks=True))
        expected = amounts["11A"] * rate
        gap = amounts["2"] - expected
        figures = f"Box 2 is {money(amounts['2'])}; {rate_text} of box 11A is {money(expected)}."
        if amounts["2"] == ZERO and amounts["11A"] == ZERO:
            checks.append(check("VR-09", title, "scored", NOT_RELEVANT, "No acquisitions of goods in the period."))
        elif abs(gap) <= Decimal("0.50"):
            checks.append(check("VR-09", title, "scored", LOOKS_RIGHT, f"{figures} Allowed difference: 0.50."))
        elif notes.get("box2"):
            checks.append(check("VR-09", title, "scored", WORTH, f"{figures} Gap {money(gap)}. Reason given: {notes['box2']}"))
        else:
            checks.append(check("VR-09", title, "scored", WORTH,
                                f"{figures} Gap {money(gap)}, allowed 0.50. Goods at a reduced rate are the usual "
                                "reason; a credit note that reached box 11A but not box 2, or a service whose VAT went "
                                "to box 2, the usual mistakes. Correct the figures, or give the reason with "
                                "--note box2=\"...\".", blocks=True))

    # Boxes 8A and 8B against the monthly VIES statements: goods with goods, services with services.
    absent = [month for month in months if month not in statements]
    not_built = [month for month in months if statements.get(month, {}).get("not_built")]
    complete = not absent and not not_built
    rows_known = not absent and all(statements[month]["rows"] is not None for month in months)
    allowed = (Decimal("0.5") * sum(statements[month]["rows"] for month in months) if rows_known
               else Decimal(len(months))) + Decimal("0.5")
    on_vies = {kind: sum((statements[month][kind] for month in months), ZERO) if not absent else None
               for kind in ("goods", "triangular", "services")}
    why_not = " ".join(filter(None, [
        f"No VIES statement was given for {', '.join(absent)}." if absent else "",
        "Not built: " + "; ".join(f"{month} ({statements[month]['not_built']})" for month in not_built) + "." if not_built else ""]))
    for code, box, kind, key in (("VR-10", "8A", "goods", "box8a"), ("VR-11", "8B", "services", "box8b")):
        title = f"Box {box} against the {kind} on the period's VIES statements"
        if box not in amounts:
            checks.append(check(code, title, "scored", NOT_CHECKED, missing_of(box)))
        elif not complete:
            would_be = (f" With the rows as they would be, the {kind} add up to {money(on_vies[kind])}."
                        if not absent else "")
            if amounts[box] == ZERO:
                checks.append(check(code, title, "scored", NOT_CHECKED, f"Box {box} is nil. {why_not}{would_be}"))
            else:
                checks.append(check(code, title, "scored", NOT_CHECKED,
                                    f"Box {box} is {money(amounts[box])} and was not tied to VIES. {why_not}{would_be} "
                                    + (f"Reason given: {notes[key]}" if notes.get(key) else
                                       "Give every month of the period with --vies or --vies-result (a month with "
                                       "nothing to report as zeros), clear what stopped a statement, or give the "
                                       f"reason the return goes ahead without the tie with --note {key}=\"...\"."),
                                    holds=not notes.get(key)))
        else:
            gap = amounts[box] - on_vies[kind]
            figures = (f"Box {box} is {money(amounts[box])}; the {kind} on VIES for {', '.join(months)} add up to "
                       f"{money(on_vies[kind])}.")
            with_triangular = kind == "goods" and on_vies["triangular"] != ZERO and abs(gap - on_vies["triangular"]) <= allowed
            how = (f"Allowed difference: {money(allowed)} (50 cents for each VIES row, rounded to the euro, and 50 "
                   "cents for the box).")
            if amounts[box] == ZERO and on_vies[kind] == ZERO:
                checks.append(check(code, title, "scored", NOT_RELEVANT, f"No {kind} to other Member States in the period."))
            elif abs(gap) <= allowed:
                checks.append(check(code, title, "scored", LOOKS_RIGHT, f"{figures} {how}"))
            elif with_triangular:
                checks.append(check(code, title, "scored", WORTH,
                                    f"{figures} Box 8A agrees once the triangular sales on VIES "
                                    f"({money(on_vies['triangular'])}) are added. The guide puts the sales value of "
                                    "triangular transactions in boxes 6 and 10. Confirm which box holds them."))
            else:
                checks.append(check(code, title, "scored", WORTH,
                                    f"{figures} Gap {money(gap)}. {how} "
                                    + (f"Reason given: {notes[key]}" if notes.get(key) else
                                       "A sale is on one and not on the other, or goods and services are swapped. "
                                       f"Correct the figures, or give the reason with --note {key}=\"...\"."),
                                    blocks=not notes.get(key)))

    title = f"Box 1 against {rate_text} of box 11B"
    if not have("1", "11B"):
        checks.append(check("VR-12", title, "scored", NOT_CHECKED, missing_of("1", "11B")))
    elif amounts["11B"] == ZERO:
        checks.append(check("VR-12", title, "scored", NOT_RELEVANT, "No services received from other Member States in the period."))
    else:
        floor = amounts["11B"] * rate
        low = amounts["1"] < floor - Decimal("0.50")
        checks.append(check("VR-12", title, "scored", WORTH if low else LOOKS_RIGHT,
                            f"Box 1 is {money(amounts['1'])}; {rate_text} of box 11B is {money(floor)}."
                            + (" The reverse charge on services received is output VAT in box 1. Lower is right only "
                               "where those services are exempt or at a reduced rate in Cyprus." if low else
                               " A weak test: box 1 also holds the VAT on sales, so it can only show a shortfall.")))

    if not have("2", "4"):
        checks.append(check("VR-13", "Box 4 covers the acquisition VAT of box 2", "scored", NOT_CHECKED, missing_of("2", "4")))
    elif amounts["2"] == ZERO:
        checks.append(check("VR-13", "Box 4 covers the acquisition VAT of box 2", "scored", NOT_RELEVANT, "Box 2 is nil."))
    else:
        low = amounts["4"] < amounts["2"]
        checks.append(check("VR-13", "Box 4 covers the acquisition VAT of box 2", "scored", WORTH if low else LOOKS_RIGHT,
                            f"Box 4 is {money(amounts['4'])}; box 2 is {money(amounts['2'])}."
                            + (" Acquisition VAT is also input VAT for a business that deducts in full. Lower is "
                               "right only where deduction is restricted." if low else
                               " A weak test: it can only show a shortfall.")))

    checks.append(check("VR-14", "The taxpayer number is a Cyprus VAT number", "worked out", PASSED if taxpayer_ok else NEEDS,
                        f"{taxpayer}: eight digits and a letter, without the CY." if taxpayer_ok else
                        f"{taxpayer or '(empty)'} is not eight digits and a letter.", blocks=True))

    whole_months = start.day == 1 and end == month_end(end)
    usual = whole_months and len(months) in (1, 3)
    checks.append(check("VR-15", "The period is whole months", "scored", LOOKS_RIGHT if usual else WORTH,
                        f"{start} to {end}: {len(months)} month{'s' if len(months) != 1 else ''}."
                        + ("" if usual else " A VAT period is normally three calendar months (one, for a monthly filer). "
                                            "Check it against the period the portal shows.")))

    too_long = [box for box in amounts if len(str(abs(whole(amounts[box])))) > 10]
    checks.append(check("VR-16", "Every figure fits the form", "worked out", NEEDS if too_long else PASSED,
                        f"More than ten digits before the decimal mark: box {', '.join(too_long)}." if too_long else
                        "None has more than ten digits before the decimal mark.", blocks=True))

    info = {
        "form": "VAT return",
        "currency": "EUR",
        "taxpayer": taxpayer,
        "period": {"from": str(start), "to": str(end)},
        "due": due_info(add_months(end, 2).replace(day=10), "the 10th day of the second month after the period ends", today),
        "decimal_mark_read": decimal,
        "standard_rate_percent": args.standard_rate,
        "boxes": [{"box": box, "label": label, "amount": money(amounts[box]) if box in amounts else None,
                   "source": source.get(box, "not given")} for box, _, _, label in BOXES],
        "vies_statements": [{"month": month,
                             **({kind: money(statements[month][kind]) for kind in ("goods", "triangular", "services")}
                                if month in statements else {}),
                             "rows": statements.get(month, {}).get("rows"),
                             "source": ("not given" if month not in statements else
                                        f"not built ({statements[month]['not_built']}); the rows as they would be"
                                        if statements[month].get("not_built") else statements[month]["source"])}
                            for month in months],
        "notes_given": notes,
    }
    if args.prepared:
        info["prepared"] = args.prepared
    if "5" in amounts:
        info["result"] = ("payable" if amounts["5"] > ZERO else "refundable or carried forward" if amounts["5"] < ZERO else "nil")
    return info, amounts, checks


def return_xml(taxpayer: str, start: date, end: date, amounts: dict[str, Decimal]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<mof:f4-declarations xmlns:mof="{NAMESPACE}">',
             f'  <mof:f4-declaration taxpayer="{taxpayer}" version="{SCHEMA_VERSION}">',
             "    <mof:form>",
             f'      <mof:period from="{start}" to="{end}"/>']
    for box, element, _, _ in BOXES:
        lines.append(f"      <mof:{element}>{money(amounts[box]).replace('.', ',')}</mof:{element}>")
    lines += ["    </mof:form>", "  </mof:f4-declaration>", "</mof:f4-declarations>", ""]
    return "\n".join(lines)


def return_read_back(xml_text: str, taxpayer: str, start: date, end: date, amounts: dict[str, Decimal]) -> str | None:
    """Parses the built file and compares it with the checked figures. Returns what differs, or None."""
    tag = lambda name: f"{{{NAMESPACE}}}{name}"  # noqa: E731
    root = ET.fromstring(xml_text)
    declarations = root.findall(tag("f4-declaration"))
    if root.tag != tag("f4-declarations") or len(declarations) != 1:
        return "the file does not hold exactly one return"
    declaration = declarations[0]
    form = declaration.find(tag("form"))
    period = form.find(tag("period")) if form is not None else None
    if declaration.get("taxpayer") != taxpayer or declaration.get("version") != SCHEMA_VERSION or period is None:
        return "taxpayer, version or period is not as checked"
    if period.get("from") != str(start) or period.get("to") != str(end):
        return "the period in the file is not the period that was checked"
    found = [child.tag for child in form if child.tag != tag("period")]
    if found != [tag(element) for _, element, _, _ in BOXES]:
        return "the thirteen boxes are not all there, once each, in the order of the form"
    for box, element, kind, _ in BOXES:
        text = form.find(tag(element)).text or ""
        pattern = r"-?\d{1,10},\d{2}" if kind == "vat" else r"-?\d{1,10},00"
        if not re.fullmatch(pattern, text) or Decimal(text.replace(",", ".")) != amounts[box].quantize(CENT, rounding=ROUND_HALF_UP):
            return f"box {box} reads {text!r} in the file; checked figure {money(amounts[box])}"
    return None


def command_return(args: argparse.Namespace, build: bool) -> int:
    info, amounts, checks = return_checks(args)
    if build:
        blocked = any(item["blocks_file"] for item in checks)
        start, end = date.fromisoformat(info["period"]["from"]), date.fromisoformat(info["period"]["to"])
        xml_text = "" if blocked else return_xml(info["taxpayer"], start, end, amounts)
        read_back = None if blocked else return_read_back(xml_text, info["taxpayer"], start, end, amounts)
        info["file"] = write_file(args.out, f"VAT-return_{info['taxpayer']}_{start}_{end}.xml", xml_text,
                                  "cy-f4-2010-declaration.xsd", args.replace, checks, "VR-17", read_back)
    info["checks"] = checks
    info["counts"] = count(checks)
    info["blocks_file"] = [item["code"] for item in checks if item["blocks_file"]]
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 2 if build and not info["file"]["written"] else 0


# ---------------------------------------------------------------------------------------------
# The VIES statement
# ---------------------------------------------------------------------------------------------

def split_vat_number(raw: str, country: str) -> tuple[str, str, bool]:
    """Country, number, and whether a country column and the number's own prefix name two countries."""
    text = re.sub(r"[\s.\-]", "", (raw or "").upper())
    given = {"GR": "EL"}.get(re.sub(r"\s", "", (country or "").upper()), re.sub(r"\s", "", (country or "").upper()))
    if re.fullmatch(r"\d{8}[A-Z]", text) and given in ("", "CY"):
        return "CY", text, False  # a Cyprus number printed without its prefix
    prefix = {"GR": "EL"}.get(text[:2], text[:2]) if re.match(r"[A-Z]{2}", text) else ""
    if not given:
        return prefix, text[2:] if prefix else text, False
    if prefix == given:
        return given, text[2:], False
    # FR + AB123456789 is a French number that starts with letters; FR + DE123456789 names two countries.
    return given, text, prefix in VIES_LOOKUP_COUNTRIES


def read_numbers_result(path: str | None) -> dict[str, str]:
    """The answers of the `numbers` command, by VAT number."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            return {item["vat_number"]: item["answer"] for item in json.load(handle)["results"]}
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"--numbers {path}: not the output of the numbers command ({error})")


def command_vies(args: argparse.Namespace) -> int:
    taxpayer, taxpayer_ok = taxpayer_number(args.taxpayer)
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.month):
        sys.exit(f"--month: expected YYYY-MM, got {args.month!r}. A VIES statement covers one calendar month.")
    start = date(int(args.month[:4]), int(args.month[5:]), 1)
    end = month_end(start)
    today = parse_date(args.today, "--today") if args.today else date.today()
    default_kind = KINDS.get(norm(args.default_kind)) if args.default_kind else None
    if args.default_kind and not default_kind:
        sys.exit("--default-kind: expected goods, services or triangular")
    looked_up = read_numbers_result(args.numbers)

    header, rows, line_numbers = read_csv(args.lines)
    by_norm = {norm(h): h for h in header}
    cols: dict[str, str] = {}
    for field, column in parse_pairs(args.map, "--map", list(ALIASES)).items():
        if norm(column) not in by_norm:
            sys.exit(f"--map {field}={column}: no such column in {args.lines}. Columns: {', '.join(header)}")
        cols[field] = by_norm[norm(column)]
    for field, names in ALIASES.items():
        if field in cols:
            continue
        for name in names:
            if norm(name) in by_norm and by_norm[norm(name)] not in cols.values():
                cols[field] = by_norm[norm(name)]
                break
    for field in ("vat_number", "amount"):
        if field not in cols:
            sys.exit(f"{args.lines}: no column found for the {field.replace('_', ' ')}. Columns: {', '.join(header)}. "
                     f"Use --map {field}=COLUMN.")
    if "kind" not in cols and not default_kind:
        sys.exit(f"{args.lines}: no column found for the kind of supply (goods, services or triangular). Columns: "
                 f"{', '.join(header)}. Name it with --map kind=COLUMN, or, when the person has said every line is "
                 "of one kind, pass --default-kind.")
    samples = [row[cols[f]] for row in rows for f in ("amount", "vat_amount") if f in cols and row[cols[f]].strip()]
    decimal = detect_decimal(samples) if args.decimal == "auto" else args.decimal

    def cell(row: dict[str, str], field: str) -> str:
        return row.get(cols[field], "").strip() if field in cols else ""

    usable: list[dict] = []
    unusable: list[dict] = []
    other_months: dict[str, int] = {}
    with_vat: list[str] = []
    bad_dates = 0
    lines_read = 0
    for index, row in zip(line_numbers, rows):
        if not any(value.strip() for value in row.values()):
            continue
        lines_read += 1
        label = cell(row, "document") or f"line {index}"
        where = f"{args.lines} line {index}"
        if "date" in cols and not cell(row, "date"):
            bad_dates += 1
            unusable.append({"line": index, "document": label, "customer": cell(row, "customer"),
                             "why": "no date: the month it belongs to is not known"})
            continue
        if cell(row, "date"):
            day = parse_line_date(cell(row, "date"))
            if day is None:
                bad_dates += 1
                unusable.append({"line": index, "document": label, "customer": cell(row, "customer"),
                                 "why": f"date {cell(row, 'date')!r} was not read (YYYY-MM-DD, or day first: 31/08/2026)"})
                continue
            if not start <= day <= end:
                other_months[f"{day:%Y-%m}"] = other_months.get(f"{day:%Y-%m}", 0) + 1
                continue  # another month's statement, not a fault
        if not cell(row, "amount"):
            unusable.append({"line": index, "document": label, "customer": cell(row, "customer"), "why": "no amount"})
            continue
        amount = parse_amount(cell(row, "amount"), decimal, where)
        vat = parse_amount(cell(row, "vat_amount"), decimal, where) if cell(row, "vat_amount") else ZERO
        country, number, two_countries = split_vat_number(cell(row, "vat_number"), cell(row, "country"))
        kind = KINDS.get(norm(cell(row, "kind"))) if cell(row, "kind") else default_kind
        problem = None
        if not number:
            problem = "no VAT number"
        elif two_countries:
            problem = (f"the country column says {country} and the number starts with {number[:2]}: write the number "
                       "with its own country code in front")
        elif country == "CY":
            problem = "a Cyprus VAT number: a sale to a Cyprus customer is not a VIES line"
        elif country not in VIES_COUNTRIES:
            problem = f"{country or 'no country'}{number}: not a VAT number of another Member State"
        elif not re.fullmatch(r"[A-Z0-9+*]{1,12}", number):
            problem = f"{country}{number}: the number after the country code is 1 to 12 letters and digits"
        elif kind is None:
            problem = ("the kind of supply is not stated (goods, services or triangular)" if not cell(row, "kind")
                       else f"kind of supply {cell(row, 'kind')!r} is not goods, services or triangular")
        elif country == "XI" and kind == "services":
            problem = "XI (Northern Ireland) is for goods only"
        elif vat != ZERO:
            problem = (f"carries VAT of {money(vat)}: a sale reported on VIES is one where the customer accounts for "
                       "the VAT")
        if vat != ZERO:
            with_vat.append(f"{label} ({money(vat)})")
        if problem:
            unusable.append({"line": index, "document": label, "customer": cell(row, "customer"),
                             "amount": money(amount), "why": problem})
            continue
        typed = re.sub(r"[\s.\-]", "", cell(row, "vat_number").upper())
        usable.append({"country": country, "number": number, "kind": kind, "amount": amount, "document": label,
                       "customer": cell(row, "customer"),
                       "given_as": typed if typed.startswith("GR") or cell(row, "country").strip().upper() == "GR" else ""})

    checks: list[dict] = [check("VS-01", "The taxpayer number is a Cyprus VAT number", "worked out",
                                PASSED if taxpayer_ok else NEEDS,
                                f"{taxpayer}: eight digits and a letter, without the CY." if taxpayer_ok else
                                f"{taxpayer or '(empty)'} is not eight digits and a letter.", blocks=True)]
    in_month = len(usable) + len(unusable)
    checks.append(check("VS-02", "Every line of the month can go on the statement", "worked out",
                        NEEDS if unusable else PASSED if usable else NOT_RELEVANT,
                        (f"{len(unusable)} of {in_month} lines cannot: see unusable_lines. "
                         + ("They were left off the statement, as told." if args.skip_unusable else
                            "Correct them in the file, or pass --skip-unusable once the person has said they do not "
                            "belong on it."))
                        if unusable else
                        f"All {len(usable)} lines carry a VAT number of another Member State, an amount and a kind "
                        "of supply." if usable else f"The file has no line for {args.month}.",
                        blocks=not args.skip_unusable))
    others = ", ".join(f"{month}: {n}" for month, n in sorted(other_months.items()))
    checks.append(check("VS-03", "Every line has a date that can be read", "worked out",
                        NOT_CHECKED if "date" not in cols else NEEDS if bad_dates else PASSED,
                        "The file has no date column. Whether each line belongs to the month was not tested."
                        if "date" not in cols else
                        f"{bad_dates} line(s) with no date or one that was not read: see unusable_lines." if bad_dates else
                        f"{len(usable) + len(unusable)} lines are dated in {args.month}."
                        + (f" Lines of other months were left for their own statements ({others})." if others else "")))
    checks.append(check("VS-04", "No line carries VAT", "worked out",
                        NOT_CHECKED if "vat_amount" not in cols else NEEDS if with_vat else PASSED,
                        "The file has no VAT amount column." if "vat_amount" not in cols else
                        ("With VAT charged, and listed under unusable_lines: " + ", ".join(with_vat[:20]) + ".")
                        if with_vat else "No line of the month has a VAT amount."))

    per_customer: OrderedDict[tuple[str, str], dict] = OrderedDict()
    for line in sorted(usable, key=lambda item: (item["country"], item["number"])):
        entry = per_customer.setdefault((line["country"], line["number"]),
                                        {"goods": ZERO, "triangular": ZERO, "services": ZERO, "documents": [], "customer": "",
                                         "given_as": ""})
        entry["given_as"] = entry["given_as"] or line["given_as"]
        entry[line["kind"]] += line["amount"]
        entry["documents"].append(f"{line['document']} ({line['kind']}, {money(line['amount'])})")
        entry["customer"] = entry["customer"] or line["customer"]
    table, left_out = [], []
    for (country, number), entry in per_customer.items():
        reported = {kind: int(whole(entry[kind])) for kind in ("goods", "triangular", "services")}
        record = {"country": country, "vat_number": number, "customer": entry["customer"],
                  "goods": reported["goods"], "triangular": reported["triangular"], "services": reported["services"],
                  "exact": {kind: money(entry[kind]) for kind in ("goods", "triangular", "services")},
                  "in_vies": looked_up.get(f"{country}{number}", "Not looked up"),
                  "documents": entry["documents"]}
        if entry["given_as"]:
            record["note"] = (f"Given as {entry['given_as']}. Greece is EL on VIES and on the statement: the "
                              "customer's record may want correcting.")
        (table if any(reported.values()) else left_out).append(record)
    for number, record in enumerate(table, start=1):
        record["row"] = number
    totals = {kind: sum(record[kind] for record in table) for kind in ("goods", "triangular", "services")}
    checks.append(check("VS-05", "One row per customer VAT number", "worked out", PASSED if table else NOT_RELEVANT,
                        f"{len(usable)} lines make {len(table)} rows."
                        + (f" {len(left_out)} customer(s) net to nil after rounding and are left out: see rows_left_out."
                           if left_out else "")))

    not_registered = [f"{r['country']}{r['vat_number']}" for r in table if r["in_vies"] == "Not registered"]
    unknown = [f"{r['country']}{r['vat_number']}" for r in table if r["in_vies"] not in ("Registered", "Not registered")]
    title = "Every customer VAT number is registered in VIES"
    if not table:
        checks.append(check("VS-06", title, "worked out", NOT_RELEVANT, "No rows."))
    elif not_registered:
        checks.append(check("VS-06", title, "worked out", NEEDS,
                            f"Not registered: {', '.join(not_registered)}. Most often a typing error: compare each "
                            "with the invoice and correct it in the file. A sale to a number that is not registered "
                            "does not belong on the statement.", blocks=True))
    elif unknown:
        checks.append(check("VS-06", title, "worked out", NOT_CHECKED,
                            (f"Not looked up or no answer: {', '.join(unknown)}. " if looked_up else "No number was looked up. ")
                            + "Run the numbers command and pass its output with --numbers."))
    else:
        checks.append(check("VS-06", title, "worked out", PASSED, f"All {len(table)} numbers were registered when asked."))

    too_big = [f"{r['country']}{r['vat_number']}" for r in table
               if any(not -999999999999 <= r[kind] <= 99999999999 for kind in ("goods", "triangular", "services"))]
    fits = not too_big and len(table) <= MAX_VIES_ROWS
    checks.append(check("VS-07", "The statement fits the form", "worked out", PASSED if fits else NEEDS,
                        f"{len(table)} rows; a statement holds at most {MAX_VIES_ROWS}. " +
                        (f"Amounts outside the range the schema allows: {', '.join(too_big)}." if too_big else
                         "Every amount is inside the range the schema allows."), blocks=True))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<mof:vies1-declarations xmlns:mof="{NAMESPACE}">',
             f'  <mof:vies1-declaration taxpayer="{taxpayer}" version="{SCHEMA_VERSION}">',
             f'    <mof:period from="{start}" to="{end}"/>',
             f"    <mof:month>{start.month}</mof:month>",
             f"    <mof:year>{start.year}</mof:year>",
             f"    <mof:total-rows>{len(table)}</mof:total-rows>",
             f"    <mof:sum-supplies-amount>{totals['goods']}</mof:sum-supplies-amount>",
             f"    <mof:sum-triangle-transactions-amount>{totals['triangular']}</mof:sum-triangle-transactions-amount>",
             f"    <mof:sum-services-amount>{totals['services']}</mof:sum-services-amount>"]
    for record in table:
        lines += [f'    <mof:row number="{record["row"]}">',
                  f'      <mof:vat-number country="{record["country"]}">{record["vat_number"]}</mof:vat-number>',
                  f'      <mof:supplies-amount>{record["goods"]}</mof:supplies-amount>',
                  f'      <mof:triangle-transactions-amount>{record["triangular"]}</mof:triangle-transactions-amount>',
                  f'      <mof:services-amount>{record["services"]}</mof:services-amount>',
                  "    </mof:row>"]
    lines += ["  </mof:vies1-declaration>", "</mof:vies1-declarations>", ""]
    xml_text = "\n".join(lines)

    name = f"VIES_{taxpayer}_{args.month}"
    blocked = any(item["blocks_file"] for item in checks)
    if not table and not blocked:
        checks.append(check("VS-08", "The file holds the figures that were tested", "worked out", NOT_RELEVANT, "No file was built."))
        file_info = {"written": False, "why": [f"No rows: there is nothing to report for {args.month}, so there is no file."]}
    else:
        read_back = None if blocked else vies_read_back(xml_text, taxpayer, start, end, table, totals)
        file_info = write_file(args.out, f"{name}.xml", xml_text, "cy-vies1-2010-declaration.xsd", args.replace, checks,
                               "VS-08", read_back)
    if file_info["written"]:
        trail = Path(file_info["path"]).with_name(f"{name}.lines.csv")
        with open(trail, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["row", "country", "vat_number", "customer", "goods_exact", "goods", "triangular_exact",
                             "triangular", "services_exact", "services", "documents"])
            for record in table:
                writer.writerow([record["row"], record["country"], record["vat_number"], record["customer"],
                                 record["exact"]["goods"], record["goods"], record["exact"]["triangular"],
                                 record["triangular"], record["exact"]["services"], record["services"],
                                 "; ".join(record["documents"])])
        file_info["lines_file"] = str(trail)

    print(json.dumps({
        "form": "VIES statement",
        "currency": "EUR",
        "taxpayer": taxpayer,
        "month": args.month,
        "period": {"from": str(start), "to": str(end)},
        "due": due_info(add_months(end, 1).replace(day=15), "the 15th day of the month after the month reported", today),
        "decimal_mark_read": decimal,
        "columns_used": cols,
        "lines_read": lines_read,
        "lines_of_other_months": dict(sorted(other_months.items())),
        "rows": table,
        "totals": {**totals, "rows": len(table)},
        "rows_left_out": left_out,
        "unusable_lines": unusable,
        "checks": checks,
        "counts": count(checks),
        "blocks_file": [item["code"] for item in checks if item["blocks_file"]],
        "file": file_info,
    }, indent=2, ensure_ascii=False))
    return 0 if file_info["written"] else 2


def vies_read_back(xml_text: str, taxpayer: str, start: date, end: date, table: list[dict], totals: dict[str, int]) -> str | None:
    tag = lambda name: f"{{{NAMESPACE}}}{name}"  # noqa: E731
    root = ET.fromstring(xml_text)
    declarations = root.findall(tag("vies1-declaration"))
    if root.tag != tag("vies1-declarations") or len(declarations) != 1:
        return "the file does not hold exactly one statement"
    declaration = declarations[0]
    period = declaration.find(tag("period"))
    if declaration.get("taxpayer") != taxpayer or period is None or period.get("from") != str(start) or period.get("to") != str(end):
        return "taxpayer or period is not as checked"
    if int(declaration.findtext(tag("month"))) != start.month or declaration.findtext(tag("year")) != str(start.year):
        return "month or year is not as checked"
    rows = declaration.findall(tag("row"))
    if int(declaration.findtext(tag("total-rows"))) != len(rows) or len(rows) != len(table):
        return "the number of rows is not the number stated"
    sums = {"goods": 0, "triangular": 0, "services": 0}
    seen = set()
    names = {"goods": "supplies-amount", "triangular": "triangle-transactions-amount", "services": "services-amount"}
    for row, record in zip(rows, table):
        vat = row.find(tag("vat-number"))
        key = (vat.get("country"), vat.text)
        if key != (record["country"], record["vat_number"]) or key in seen or row.get("number") != str(record["row"]):
            return f"row {row.get('number')} is not the row that was checked, or a VAT number appears twice"
        seen.add(key)
        for kind, element in names.items():
            value = int(row.findtext(tag(element)) or 0)
            if value != record[kind]:
                return f"row {record['row']} {kind} reads {value}; checked figure {record[kind]}"
            sums[kind] += value
    for kind, element in (("goods", "sum-supplies-amount"), ("triangular", "sum-triangle-transactions-amount"),
                          ("services", "sum-services-amount")):
        if int(declaration.findtext(tag(element))) != sums[kind] or sums[kind] != totals[kind]:
            return f"the {kind} total is not the sum of its rows"
    return None


# ---------------------------------------------------------------------------------------------
# A draft return from the documents
# ---------------------------------------------------------------------------------------------

DOC_ALIASES = {
    "document": ["document", "document number", "number", "invoice", "invoice number", "invoice no", "doc"],
    "date": ["date", "document date", "invoice date", "issue date"],
    "type": ["type", "document type"],
    "counterparty": ["counterparty", "customer or supplier", "name", "customer", "supplier", "contact"],
    "vat_number": ["vat number", "counterparty vat number", "vat no", "vat id", "vat reg no"],
    "country": ["country", "country code"],
    "supply": ["supply", "goods or services", "goods/services", "kind"],
    "net": ["net", "net amount", "net eur"],
    "vat": ["vat", "vat amount", "vat eur"],
    "rate": ["rate", "vat rate", "vat rate %", "rate %"],
    "currency": ["currency"],
    "euro_amount_from": ["euro amount from", "euros from"],
    "addressed_to_company": ["addressed to company", "addressed to the company", "in company name"],
    "treatment": ["treatment"],
    "cy_rate": ["cy rate", "cyprus rate", "rate in cyprus"],
    "note": ["note", "notes", "comment"],
}
DOC_TYPES = {  # what the person calls it -> (side, credit note)
    "sale": ("sale", False), "sale invoice": ("sale", False), "sales invoice": ("sale", False),
    "sale credit note": ("sale", True), "sales credit note": ("sale", True), "credit note issued": ("sale", True),
    "purchase": ("purchase", False), "purchase invoice": ("purchase", False), "bill": ("purchase", False),
    "receipt": ("purchase", False),
    "purchase credit note": ("purchase", True), "supplier credit note": ("purchase", True),
    "credit note received": ("purchase", True),
    "import vat": ("import", False), "customs declaration": ("import", False),
}
TREATMENTS = {"", "exempt", "zero rated", "outside the scope", "triangular", "not business", "outside the return"}
PURCHASE_TREATMENTS = {"", "exempt", "not business", "outside the return"}
# ISO 3166 two-letter codes, so that HE (a Cyprus company number), XX or VA(T) is not taken for a country.
COUNTRY_CODES = set("""AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW
BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB
GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM
KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC
NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL
SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE
YT ZA ZM ZW""".split()) | {"EL", "XI", "UK", "XK"}
NO = {"no", "n", "false", "0"}
NOT_SHOWN = {"not shown", "unknown", "nobody", "no name"}


def place_document(doc: dict) -> dict:
    """Which boxes one document belongs in, by fixed rules. Never a guess: a document the rules cannot
    place comes back with `ask`, the question for the person, and touches no box.

    Returns {"treatment", "boxes": {box: amount}, "vies": kind or None, "unclaimed": VAT left out of box 4,
    "why": reason for that, "ask": question or None, "excluded": reason or None, "practice": bool}.
    """
    net, vat, side, supply, region = doc["net"], doc["vat"], doc["side"], doc["supply"], doc["region"]
    has_number, wants = doc["has_number"], doc["treatment"]
    out = {"treatment": "", "boxes": {}, "vies": None, "unclaimed": ZERO, "why": "", "ask": None, "excluded": None,
           "practice": False, "check": False, "reverse_charge": ZERO}

    def done(treatment: str, boxes: dict[str, Decimal], **more: object) -> dict:
        out.update({"treatment": treatment, "boxes": {box: amount for box, amount in boxes.items() if amount != ZERO}})
        out.update(more)
        return out

    def ask(question: str) -> dict:
        out["ask"] = question
        return out

    if wants in ("not business", "outside the return"):
        return done(wants, {}, excluded="Left out as told: " + wants + ".")
    if side == "import":
        return done("import VAT on a customs declaration", {"4": vat})
    # The VAT the company accounts for itself under the reverse charge. cy_rate None: exempt in Cyprus, none due.
    reverse = (net * doc["cy_rate"]).quantize(CENT, rounding=ROUND_HALF_UP) if doc["cy_rate"] is not None else ZERO

    if wants in ("exempt", "zero rated", "outside the scope", "triangular") and vat != ZERO:
        return ask(f"The treatment says {wants}, and the document shows VAT of {money(vat)}. Which is right?")
    if side == "purchase" and wants not in PURCHASE_TREATMENTS:
        return ask(f"The treatment {wants} is for a sale. For a purchase it is exempt, not business or outside "
                   "the return.")

    if side == "sale":
        if wants == "exempt":
            return done("exempt sale", {"6": net})
        if wants == "zero rated":
            return done("zero rated sale", {"9": net, "6": net})
        if wants == "outside the scope":
            return done("sale outside the scope of Cyprus VAT, with the right to deduct", {"10": net, "6": net})
        if wants == "triangular":
            if region != "EU" or not has_number:
                return ask("A triangular sale needs the VAT number of the customer in another Member State.")
            return done("triangular sale", {"10": net, "6": net}, vies="triangular")
        if vat != ZERO:
            return done("sale with Cyprus VAT", {"1": vat, "6": net},
                        note="Cyprus VAT was charged to a customer with an EU VAT number: check that is right."
                        if region == "EU" and has_number else "")
        if region is None:
            return ask("No VAT on this sale, and the customer's country is not known. Give the VAT number or the "
                       "two-letter country.")
        if region == "CY":
            return ask("No VAT on a sale to a customer in Cyprus. Say which it is in the treatment column: "
                       "zero rated, exempt or outside the scope.")
        if supply is None:
            return ask("No VAT on this sale abroad. Say whether it is goods or services.")
        if region == "EU" and not has_number:
            return ask("No VAT on a sale to a customer in another Member State who has no VAT number. Sales to "
                       "consumers carry VAT. Give the VAT number, or the treatment (zero rated, exempt, outside "
                       "the scope).")
        if region == "EU" and supply == "goods":
            return done("goods to a VAT-registered customer in another Member State", {"8A": net, "6": net}, vies="goods")
        if region == "EU":
            return done("services to a VAT-registered customer in another Member State", {"8B": net, "6": net},
                        vies="services")
        if supply == "goods":
            return done("export of goods", {"9": net, "6": net}, practice=True)
        return done("services to a customer outside the EU", {"10": net, "6": net}, practice=True)

    # A purchase.
    if doc["addressed"] is False:
        return done("not addressed to the company", {}, practice=True,
                    excluded="Not addressed to the company: no input VAT, and out of box 7.")
    if doc["addressed"] == "not shown" and vat != ZERO and region in ("CY", None):
        return done("purchase on a receipt made out to no one, VAT not claimed", {"7": net}, unclaimed=vat, check=True,
                    why="a receipt that does not name the company: ask the supplier for a VAT invoice in its name")
    if wants == "exempt" or (region == "CY" and vat == ZERO):
        return done("purchase without VAT", {"7": net})
    if region is None:
        return ask("The supplier's country is not known. Give the VAT number or the two-letter country.")
    if region == "CY":
        if has_number:
            return done("purchase with Cyprus VAT", {"4": vat, "7": net})
        return done("purchase with Cyprus VAT, not claimed", {"7": net}, unclaimed=vat, check=True,
                    why="no supplier VAT number on the record: check the invoice itself")
    if vat != ZERO:
        return done("purchase with VAT of another country, not claimed", {"7": net}, unclaimed=vat, practice=True,
                    why="VAT of another Member State is reclaimed from that state" if region == "EU" else
                        "VAT charged by a supplier outside Cyprus is not input VAT here")
    if supply is None:
        return ask("No VAT on this purchase from abroad. Say whether it is goods or services.")
    if region == "EU" and not has_number:
        return ask("No VAT on a purchase from a supplier in another Member State who shows no VAT number. Give "
                   "the number. If no VAT is due on it in Cyprus either, the treatment is exempt.")
    if supply == "goods":
        if region == "EU":
            return done("goods from a VAT-registered supplier in another Member State",
                        {"2": reverse, "4": reverse, "7": net, "11A": net}, reverse_charge=reverse)
        return done("goods from outside the EU", {"7": net},
                    note="Import VAT is on the customs declaration. Add it as its own row, type import vat.")
    if region == "EU":
        return done("services from a VAT-registered supplier in another Member State (reverse charge)",
                    {"1": reverse, "4": reverse, "6": net, "7": net, "11B": net}, reverse_charge=reverse)
    return done("services from a supplier outside the EU (reverse charge)",
                {"1": reverse, "4": reverse, "6": net, "7": net}, reverse_charge=reverse)


def percent(text: str) -> Decimal | None:
    """A rate as a percentage: 0, or between 1 and 30. None when the cell holds something else (0.05, n/a)."""
    match = re.fullmatch(r"(\d{1,2})(?:[.,](\d{1,2}))?\s*%?", text.strip())
    value = Decimal(f"{match.group(1)}.{match.group(2) or 0}") if match else None
    return value if value is not None and (value == ZERO or Decimal("1") <= value <= Decimal("30")) else None


def seal(figures: dict[str, str]) -> str:
    """Ties "prepared from n documents" to the figures prepare wrote: a file edited by hand loses it."""
    return hashlib.sha256(json.dumps(figures, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def command_prepare(args: argparse.Namespace) -> int:
    start, end = parse_date(args.start, "--from"), parse_date(args.end, "--to")
    if start > end:
        sys.exit("--from is after --to")
    notes = parse_pairs(args.note, "--note", ["documents"])
    rate = Decimal(str(args.standard_rate)) / 100
    header, rows, line_numbers = read_csv(args.documents)
    by_norm = {norm(h): h for h in header}
    cols: dict[str, str] = {}
    for field, column in parse_pairs(args.map, "--map", list(DOC_ALIASES)).items():
        if norm(column) not in by_norm:
            sys.exit(f"--map {field}={column}: no such column in {args.documents}. Columns: {', '.join(header)}")
        cols[field] = by_norm[norm(column)]
    for field, names in DOC_ALIASES.items():
        if field not in cols:
            for name in names:
                if norm(name) in by_norm and by_norm[norm(name)] not in cols.values():
                    cols[field] = by_norm[norm(name)]
                    break
    lacking = [field for field in ("document", "date", "type", "net", "vat") if field not in cols]
    if lacking:
        sys.exit(f"{args.documents}: no column for {', '.join(lacking)}. Columns: {', '.join(header)}. The columns "
                 f"are: {', '.join(DOC_ALIASES)}.")

    def cell(row: dict[str, str], field: str) -> str:
        return row.get(cols[field], "").strip() if field in cols else ""

    samples = [row[cols[f]] for row in rows for f in ("net", "vat") if row[cols[f]].strip()]
    decimal = detect_decimal(samples) if args.decimal == "auto" else args.decimal

    placed: list[dict] = []
    not_on_document: list[dict] = []  # euro amounts the person gave for documents in another currency
    read: set[tuple] = set()
    questions: list[dict] = []
    other_periods: dict[str, int] = {}
    rate_mismatch: list[str] = []
    rate_unknown = 0
    bad_dates: list[str] = []
    seen: dict[tuple, int] = {}
    twice: list[str] = []
    for index, row in zip(line_numbers, rows):
        if not any(value.strip() for value in row.values()):
            continue
        number = cell(row, "document") or f"line {index}"
        where = f"{args.documents} line {index}"
        base = {"line": index, "document": number, "counterparty": cell(row, "counterparty")}
        read.add((norm(cell(row, "type")), norm(cell(row, "counterparty")), norm(number)))
        day = parse_line_date(cell(row, "date")) if cell(row, "date") else None
        if day is None:
            bad_dates.append(number)
            questions.append({**base, "ask": f"Date {cell(row, 'date')!r} was not read (YYYY-MM-DD, or day first)."
                              if cell(row, "date") else "No date: the period it belongs to is not known."})
            continue
        if not start <= day <= end:
            other_periods[f"{day:%Y-%m}"] = other_periods.get(f"{day:%Y-%m}", 0) + 1
            continue
        kind = DOC_TYPES.get(norm(cell(row, "type")))
        if kind is None:
            questions.append({**base, "ask": f"Type {cell(row, 'type')!r} is not one of: sale, sale credit note, "
                                             "purchase, purchase credit note, import vat."})
            continue
        side, credit = kind
        currency = cell(row, "currency").upper()
        if currency not in ("", "EUR", "€", "EURO"):
            if not (cell(row, "euro_amount_from") and cell(row, "net")):
                questions.append({**base, "ask": f"The document is in {currency}. Give its amount in euros (the bank "
                                                 "or card statement shows what was paid), or the rate the company uses."})
                continue
            not_on_document.append({**base, "currency": currency, "euros_from": cell(row, "euro_amount_from")})
        if not cell(row, "net") and side != "import":
            questions.append({**base, "ask": "No net amount in euros."})
            continue
        net = parse_amount(cell(row, "net"), decimal, where) if cell(row, "net") else ZERO
        vat = parse_amount(cell(row, "vat"), decimal, where) if cell(row, "vat") else ZERO
        if credit:  # a credit note is taken as negative, however its amounts are printed
            net, vat = -abs(net), -abs(vat)
        wants = norm(cell(row, "treatment"))
        if wants not in TREATMENTS:
            questions.append({**base, "ask": f"Treatment {cell(row, 'treatment')!r} is not one of: "
                                             + ", ".join(sorted(TREATMENTS - {''})) + "."})
            continue
        country, vat_no, two_countries = split_vat_number(cell(row, "vat_number"), cell(row, "country"))
        if two_countries:
            questions.append({**base, "ask": f"The country column says {country} and the VAT number starts with "
                                             f"{vat_no[:2]}. Which is it?"})
            continue
        typed = re.sub(r"[\s.\-]", "", cell(row, "vat_number").upper())
        stated = re.sub(r"\s", "", cell(row, "country").upper())
        if stated and stated not in COUNTRY_CODES:
            questions.append({**base, "ask": f"Country {cell(row, 'country')!r} is not a two-letter country code "
                                             "(DE, US, AE)."})
            continue
        if typed.startswith("EU") and not stated:
            region = "outside"  # a One Stop Shop number of a business outside the EU
        elif country == "CY":
            region = "CY"
        elif country in VIES_COUNTRIES:
            region = "EU"
        elif stated or country == "GB":
            region = "outside"
        else:
            # Letters in front of a number are a country only where the list knows them: HE 123456 is a
            # Cyprus company number, not a VAT number of a country called HE.
            region, vat_no, country = None, "", ""
        supply = KINDS.get(norm(cell(row, "supply")))
        if supply == "triangular":
            supply, wants = "goods", wants or "triangular"
        if region == "EU" and country == "XI" and supply == "services":
            region = "outside"  # Northern Ireland is in the EU's VAT area for goods only
        cy_rate_text = norm(cell(row, "cy_rate"))
        if cy_rate_text in ("", "standard"):
            cy_rate: Decimal | None = rate
        elif cy_rate_text in ("exempt", "none"):
            cy_rate = None
        elif percent(cy_rate_text) is None:
            questions.append({**base, "ask": f"cy_rate {cell(row, 'cy_rate')!r} is not a rate in percent (5, 9, 19), "
                                             "0 or exempt."})
            continue
        else:
            cy_rate = percent(cy_rate_text) / 100
        to_whom = norm(cell(row, "addressed_to_company"))
        addressed = None if not to_whom else "not shown" if to_whom in NOT_SHOWN else to_whom not in NO
        printed_rate = percent(cell(row, "rate")) if cell(row, "rate") else None
        if cell(row, "rate") and printed_rate is None:
            questions.append({**base, "ask": f"Rate {cell(row, 'rate')!r} is not a rate in percent. Leave the cell "
                                             "empty when the document prints none."})
            continue
        # The same document may fill several rows (two rates, goods and services). A row is there twice
        # when everything about it is the same.
        key = (side, credit, norm(cell(row, "counterparty")) or f"{country}{vat_no}", norm(number), printed_rate,
               supply, wants, net, vat)
        if cell(row, "document") and key in seen:
            twice.append(f"{number} ({cell(row, 'counterparty')}): lines {seen[key]} and {index}")
        seen[key] = index
        doc = {"net": net, "vat": vat, "side": side, "supply": supply, "region": region, "has_number": bool(vat_no),
               "treatment": wants, "cy_rate": cy_rate, "addressed": addressed}
        result = place_document(doc)
        record = {**base, "date": str(day), "type": ("sale" if side == "sale" else "purchase" if side == "purchase" else "import vat")
                  + (" credit note" if credit else ""), "vat_number": f"{country}{vat_no}" if vat_no else "",
                  "country": country, "supply": supply or "", "net": net, "vat": vat, "numbered": bool(cell(row, "document")),
                  "your_note": cell(row, "note"), **result}
        # A misread amount shows where the VAT is not the rate on the net. Allowed: 5 cents, or half a
        # percent of the VAT for a long bill whose lines are rounded one by one.
        if not result["ask"] and not result["excluded"] and side != "import":
            if printed_rate is not None:
                expected = net * printed_rate / 100
                if abs(vat - expected) > max(Decimal("0.05"), abs(expected) * Decimal("0.005")):
                    rate_mismatch.append(f"{number}: VAT {money(vat)}, but {printed_rate}% of {money(net)} is {money(expected)}")
            elif vat != ZERO:
                rate_unknown += 1
        if result["ask"]:
            questions.append({**base, "net": money(net), "vat": money(vat), "ask": result["ask"]})
        else:
            placed.append(record)

    def documents_in(rows_of: list[dict]) -> int:
        return len({(doc["type"], doc["counterparty"], doc["document"]) for doc in rows_of})

    counted = [doc for doc in placed if not doc["excluded"]]
    exact = {box: ZERO for box in BOX_KEYS}
    for doc in counted:
        for box, amount in doc["boxes"].items():
            exact[box] += amount
    boxes = {box: (exact[box] if box in ("1", "2", "4") else whole(exact[box])) for box in BOX_KEYS}
    boxes["3"] = boxes["1"] + boxes["2"]
    boxes["5"] = boxes["3"] - boxes["4"]
    unclaimed = [doc for doc in counted if doc["unclaimed"] != ZERO]
    excluded = [doc for doc in placed if doc["excluded"]]
    exempt_sales = [doc for doc in counted if doc["treatment"] == "exempt sale"]

    checks: list[dict] = []
    checks.append(check("PD-01", "Every document could be placed in the return", "worked out",
                        NEEDS if questions or not placed else PASSED,
                        f"{len(questions)} document(s) could not: see questions. Each needs an answer from the person, "
                        "or from the document itself." if questions else
                        f"{len(placed)} rows of the period, each by a fixed rule." if placed else
                        "No document of the list is dated in the period. Check the period and how the dates were "
                        "written (day first). A period with nothing in it is a nil return the person states, not a "
                        "draft.", blocks=True))
    checks.append(check("PD-02", "No document is in the list twice", "worked out", NEEDS if twice else PASSED,
                        "Twice: " + "; ".join(twice[:20]) + ". Take one out, or correct the number." if twice else
                        "No document number repeats for the same customer or supplier.", blocks=True))
    others = ", ".join(f"{month}: {n}" for month, n in sorted(other_periods.items()))
    checks.append(check("PD-03", "Every document has a date that can be read", "worked out",
                        NEEDS if bad_dates else PASSED,
                        f"No date, or one that was not read: {', '.join(bad_dates[:20])}." if bad_dates else
                        "All dates were read." + (f" Left out, dated outside the period: {others}." if others else ""),
                        blocks=True))
    checks.append(check("PD-04", "The VAT on each document agrees with its rate", "worked out",
                        NEEDS if rate_mismatch else NOT_CHECKED if "rate" not in cols else PASSED,
                        "Read again from the document: " + "; ".join(rate_mismatch[:20]) + "." if rate_mismatch else
                        "The list has no rate column, so an amount read wrongly would not show." if "rate" not in cols
                        else ("Within the rounding (5 cents, or half a percent of the VAT) on every document that states "
                              f"a rate. {rate_unknown} with VAT state no rate." if rate_unknown else
                              "Within the rounding (5 cents, or half a percent of the VAT) on every document."),
                        blocks=True))
    to_check = [doc for doc in unclaimed if doc["check"]]
    foreign = [doc for doc in unclaimed if not doc["check"]]
    held = sum((doc["unclaimed"] for doc in to_check), ZERO)
    abroad = (f" VAT of another country on {len(foreign)} document(s), {money(sum((d['unclaimed'] for d in foreign), ZERO))}, "
              "is not input VAT here: see vat_not_claimed." if foreign else "")
    checks.append(check("PD-05", "Input VAT is claimed only where the document supports it", "worked out",
                        NEEDS if to_check else PASSED,
                        (f"Cyprus VAT of {money(held)} on {len(to_check)} document(s) was left out of box 4, because "
                         "the document does not support the claim as it was read: see vat_not_claimed. Check each "
                         "against the document itself." if to_check else
                         "Every Cyprus purchase with VAT names the supplier's VAT number and the company.") + abroad))
    # Own invoice numbers that run without a gap are the one sign of completeness the documents carry.
    runs: dict[str, list[str]] = {}
    for doc in placed:
        match = re.fullmatch(r"(.*?)(\d+)", doc["document"])
        if doc["type"] == "sale" and doc["numbered"] and match:
            runs.setdefault(match.group(1), []).append(match.group(2))
    long_runs = {prefix: digits for prefix, digits in runs.items() if len(set(digits)) >= 3}
    gaps: list[str] = []
    for prefix, digits in long_runs.items():
        numbers = {int(d) for d in digits}
        missing = max(numbers) - min(numbers) + 1 - len(numbers)
        width = len(min(digits, key=len)) if all(len(d) == len(digits[0]) for d in digits) else 0
        if 0 < missing <= 20:
            gaps += [f"{prefix}{str(n).zfill(width)}" for n in range(min(numbers), max(numbers) + 1) if n not in numbers]
        elif missing:
            gaps.append(f"{missing} numbers between {prefix}{str(min(numbers)).zfill(width)} and "
                        f"{prefix}{str(max(numbers)).zfill(width)}")
    checks.append(check("PD-06", "Your own invoice numbers run without a gap", "scored",
                        NOT_CHECKED if not long_runs else WORTH if gaps else LOOKS_RIGHT,
                        "Fewer than three sales invoices with a running number." if not long_runs else
                        f"Not among the documents: {', '.join(gaps)}. A cancelled number is fine; a missing invoice "
                        "is a sale left out." if gaps else "No number is missing between the first and the last."))
    checks.append(check("PD-07", "Input VAT can be deducted in full", "scored", WORTH if exempt_sales else LOOKS_RIGHT,
                        f"{len(exempt_sales)} exempt sale(s) in the period. A business with exempt sales may deduct "
                        "only part of its input VAT. Box 4 here is the full amount: ask the accountant." if exempt_sales
                        else "No exempt sale among the documents."))
    statement = notes.get("documents", "")
    checks.append(check("PD-08", "The documents are all of the period's", "worked out", NOT_CHECKED,
                        "Documents cannot show what is missing: a bill that was never uploaded leaves no trace here. "
                        + (f"The person's statement: {statement}" if statement else
                           "The draft waits for the person to say the documents are complete: --note documents=\"...\" "
                           "in their words. A bank statement would show a payment with no document."),
                        holds=not statement))

    blocked = [item["code"] for item in checks if item["blocks_file"]]
    files: dict[str, object] = {"written": False}
    vies_lines = [doc for doc in counted if doc["vies"]]
    out = Path(args.out).resolve()
    # A draft of an earlier run must not outlive this one: a held draft leaves no file to build from.
    for name in ("prepared-boxes.json", "prepared-documents.csv", "prepared-vies-lines.csv"):
        (out / name).unlink(missing_ok=True)
    if blocked:
        files["why"] = [f"{item['code']} {item['title']}: {item['detail']}" for item in checks if item["blocks_file"]]
    else:
        out.mkdir(parents=True, exist_ok=True)
        boxes_file = out / "prepared-boxes.json"
        figures = {box: money(boxes[box]) for box in BOX_KEYS}
        boxes_file.write_text(json.dumps({
            "prepared": {"from": str(start), "to": str(end), "documents": documents_in(counted), "statement": statement,
                         "seal": seal(figures)},
            "boxes": figures}, indent=2) + "\n", encoding="utf-8")
        trail = out / "prepared-documents.csv"
        with open(trail, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["document", "date", "type", "counterparty", "vat_number", "supply", "net", "vat", "treatment",
                             *[f"box_{box}" for box in BOX_KEYS if box not in ("3", "5")], "vat_not_claimed", "note",
                             "your_note"])
            for doc in placed:
                writer.writerow([doc["document"], doc["date"], doc["type"], doc["counterparty"], doc["vat_number"],
                                 doc["supply"], money(doc["net"]), money(doc["vat"]), doc["treatment"],
                                 *[money(doc["boxes"][box]) if box in doc["boxes"] and not doc["excluded"] else ""
                                   for box in BOX_KEYS if box not in ("3", "5")],
                                 money(doc["unclaimed"]) if doc["unclaimed"] else "",
                                 doc["excluded"] or doc["why"] or doc.get("note", ""), doc["your_note"]])
        files = {"written": True, "boxes": str(boxes_file), "documents": str(trail)}
        if vies_lines:
            vies_file = out / "prepared-vies-lines.csv"
            with open(vies_file, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Document", "Date", "Customer", "Customer VAT number", "Net", "VAT amount", "Kind"])
                for doc in vies_lines:
                    writer.writerow([doc["document"], doc["date"], doc["counterparty"], doc["vat_number"],
                                     money(doc["net"]), money(doc["vat"]), doc["vies"]])
            files["vies_lines"] = str(vies_file)

    by_treatment: OrderedDict[str, dict] = OrderedDict()
    for doc in counted:
        group = by_treatment.setdefault(doc["treatment"], {"rows": [], "net": ZERO, "vat": ZERO, "reverse": ZERO,
                                                           "boxes": set(), "practice": doc["practice"]})
        group["rows"].append(doc)
        group["net"] += doc["net"]
        group["vat"] += doc["vat"]
        group["reverse"] += doc["reverse_charge"]
        group["boxes"] |= set(doc["boxes"])

    def brief(doc: dict) -> dict:
        return {"document": doc["document"], "date": doc["date"], "counterparty": doc["counterparty"],
                "net": money(doc["net"]), "vat": money(doc["vat"])}

    print(json.dumps({
        "form": "VAT return, a draft from the documents",
        "currency": "EUR",
        "period": {"from": str(start), "to": str(end)},
        "decimal_mark_read": decimal,
        "standard_rate_percent": args.standard_rate,
        "columns_used": cols,
        "due": due_info(add_months(end, 2).replace(day=10), "the 10th day of the second month after the period ends",
                        parse_date(args.today, "--today") if args.today else date.today()),
        "vies_due": [{"month": month, "date": str(add_months(date(int(month[:4]), int(month[5:]), 1), 1).replace(day=15))}
                     for month in months_of(start, end)],
        "documents": {"read": len(read), "in_the_return": documents_in(counted), "rows_in_the_return": len(counted),
                      "left_out": documents_in(excluded), "questions": len(questions),
                      "of_other_periods": dict(sorted(other_periods.items()))},
        "boxes": [{"box": box, "label": label, "amount": money(boxes[box]),
                   **({"before_rounding": money(exact[box])} if box in VALUE_BOXES and exact[box] != boxes[box] else {})}
                  for box, _, _, label in BOXES],
        "by_treatment": [{"treatment": name, "documents": documents_in(group["rows"]), "net": money(group["net"]),
                          "vat_on_the_documents": money(group["vat"]),
                          **({"vat_accounted_for_by_the_company": money(group["reverse"])} if group["reverse"] else {}),
                          "boxes": sorted(group["boxes"], key=BOX_KEYS.index), "rests_on_practice": group["practice"]}
                         for name, group in by_treatment.items()],
        "placed": [{**brief(doc), "type": doc["type"], "supply": doc["supply"], "treatment": doc["treatment"],
                    "left_out": bool(doc["excluded"]),
                    "boxes": {box: money(amount) for box, amount in doc["boxes"].items()} if not doc["excluded"] else {}}
                   for doc in placed],
        "euro_amounts_not_on_the_document": not_on_document,
        "questions": questions,
        "vat_not_claimed": [{**brief(doc), "vat_left_out": money(doc["unclaimed"]), "why": doc["why"]} for doc in unclaimed],
        "left_out": [{**brief(doc), "why": doc["excluded"]} for doc in excluded],
        "notes": [{**brief(doc), "note": doc["note"]} for doc in counted if doc.get("note")],
        "vies_lines": len(vies_lines),
        "checks": checks,
        "counts": count(checks),
        "blocks_file": blocked,
        "files": files,
    }, indent=2, ensure_ascii=False))
    return 0 if files["written"] else 2


# ---------------------------------------------------------------------------------------------
# VAT numbers
# ---------------------------------------------------------------------------------------------

def normalise_vat_number(raw: str) -> str:
    country, number, _ = split_vat_number(raw, "")
    return f"{country}{number}"


def shown(text: str | None) -> str | None:
    """Some Member States return '---' in place of a name or address they do not publish."""
    text = (text or "").strip()
    return None if not text or set(text) <= {"-"} else text


TRANSIENT = ("MS_UNAVAILABLE", "TIMEOUT", "SERVICE_UNAVAILABLE", "MS_MAX_CONCURRENT_REQ", "GLOBAL_MAX_CONCURRENT_REQ",
             "MS_MAX_CONCURRENT_REQ_TIME", "GLOBAL_MAX_CONCURRENT_REQ_TIME")
ELSEWHERE = "The same lookup is on the EU's VIES page: ec.europa.eu/taxation_customs/vies"


def look_up(vat: str, timeout: float) -> dict:
    """One number. `unreachable` is set when no answer came back at all: no network, or VIES is down."""
    country, number = vat[:2], vat[2:]
    if country not in VIES_LOOKUP_COUNTRIES or not number:
        return {"vat_number": vat, "answer": NOT_CHECKED,
                "why": "VIES holds the numbers of EU Member States only. Not there: numbers from outside the EU "
                       "(GB included) and numbers that start with EU, which belong to the One Stop Shop."}
    error, attempts = "", 2
    for attempt in range(attempts):
        if attempt:
            time.sleep(2)
        try:
            request = urllib.request.Request(VIES_URL.format(country=country, number=number),
                                             headers={"User-Agent": "cybooks-vat-skill/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
        except Exception as problem:  # no network, a timeout, a 5xx: all mean "not checked"
            error = str(problem)
            continue
        code = data.get("userError") or ""
        if code in TRANSIENT:
            error = code
            continue
        # Only a plain VALID or INVALID is an answer about the number. Anything else is about the service.
        if data.get("isValid") is True and code in ("VALID", ""):
            answer = "Registered"
        elif data.get("isValid") is False and code == "INVALID":
            answer = "Not registered"
        else:
            return {"vat_number": vat, "answer": NOT_CHECKED, "why": f"VIES gave no answer on the number ({code or 'no detail'}). {ELSEWHERE}"}
        return {"vat_number": vat, "answer": answer, "name": shown(data.get("name")),
                "address": shown((data.get("address") or "").replace("\n", ", ")), "asked_on": data.get("requestDate")}
    return {"vat_number": vat, "answer": NOT_CHECKED, "unreachable": error not in TRANSIENT,
            "why": f"VIES could not be reached from here ({error or 'no detail'}). {ELSEWHERE}"}


def command_numbers(args: argparse.Namespace) -> int:
    seen: list[str] = []
    for raw in args.vat_numbers:
        vat = normalise_vat_number(raw)
        if vat and vat not in seen:
            seen.append(vat)
    results: list[dict] = []
    down = ""
    for vat in seen:
        if down:  # no network here: do not wait out a timeout for every number
            results.append({"vat_number": vat, "answer": NOT_CHECKED, "why": down})
            continue
        result = look_up(vat, args.timeout)
        if result.pop("unreachable", False):
            down = result["why"]
        results.append(result)
        time.sleep(0.4)  # VIES limits requests per Member State
    answers = [item["answer"] for item in results]
    print(json.dumps({"asked": len(results), "registered": answers.count("Registered"),
                      "not_registered": answers.count("Not registered"),
                      "could_not_be_checked": answers.count(NOT_CHECKED), "results": results},
                     indent=2, ensure_ascii=False))
    return 0


class Parser(argparse.ArgumentParser):
    """Exit 1 on a wrong command line: 2 is kept for "no file was written, the output says why"."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: {message}\n")


def main() -> int:
    parser = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)

    def return_arguments(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--taxpayer", required=True, help="the company's Cyprus VAT number, with or without CY")
        sub.add_argument("--from", dest="start", required=True, metavar="YYYY-MM-DD", help="first day of the period")
        sub.add_argument("--to", dest="end", required=True, metavar="YYYY-MM-DD", help="last day of the period")
        sub.add_argument("--boxes", help="CSV with the columns box and amount, or JSON {\"1\": 500.00, ...}")
        sub.add_argument("--box", action="append", default=[], metavar="BOX=AMOUNT", help="one box; repeat. Adds to --boxes")
        sub.add_argument("--decimal", choices=["auto", "point", "comma"], default="auto",
                         help="decimal mark of the figures given as text (default: worked out from them)")
        sub.add_argument("--missing-zero", action="store_true",
                         help="boxes without a figure are nil. Only after the person has said so")
        sub.add_argument("--round-values", action="store_true",
                         help="round boxes 6 to 11B to the nearest euro, half up, and list each change")
        sub.add_argument("--vies", action="append", default=[], metavar="MONTH:goods=N,triangular=N,services=N[,rows=N]",
                         help="a monthly VIES statement of the period as it was filed, for the tests against boxes 8A "
                              "and 8B. Repeat for each month; a month with nothing to report is given as 0")
        sub.add_argument("--vies-result", action="append", default=[], metavar="FILE",
                         help="the JSON output of the vies command for one month, in place of --vies. Repeat")
        sub.add_argument("--note", action="append", default=[], metavar="KEY=REASON",
                         help="the person's written reason for a gap: box2 (box 2 against box 11A), box8a or box8b "
                              "(against the VIES statements)")
        sub.add_argument("--today", help=argparse.SUPPRESS)
        sub.add_argument("--standard-rate", type=float, default=19.0, help="standard VAT rate in percent (default 19)")

    checker = commands.add_parser("check", help="run the tests on the thirteen boxes; writes nothing")
    return_arguments(checker)
    builder = commands.add_parser("xml", help="run the tests, then write the VAT return file")
    return_arguments(builder)
    vies = commands.add_parser("vies", help="build the monthly VIES statement from the month's sales lines")
    vies.add_argument("--taxpayer", required=True, help="the company's Cyprus VAT number, with or without CY")
    vies.add_argument("--month", required=True, metavar="YYYY-MM")
    vies.add_argument("--lines", required=True,
                      help="CSV, one row per invoice or credit note, credit notes negative. It may cover more than "
                           "the month: with a date column, only the month's lines are used")
    vies.add_argument("--map", action="append", default=[], metavar="FIELD=COLUMN",
                      help=f"name a column by hand. Fields: {', '.join(ALIASES)}")
    vies.add_argument("--default-kind", help="goods, services or triangular: for lines that do not say")
    vies.add_argument("--decimal", choices=["auto", "point", "comma"], default="auto")
    vies.add_argument("--skip-unusable", action="store_true",
                      help="leave unusable lines off the statement. Only after the person has said they do not belong on it")
    vies.add_argument("--numbers", metavar="FILE", help="the JSON output of the numbers command, for the test that "
                                                        "every customer number is registered")
    vies.add_argument("--today", help=argparse.SUPPRESS)
    for sub in (builder, vies):
        sub.add_argument("--out", default=".", help="folder for the file (default: here)")
        sub.add_argument("--replace", action="store_true", help="overwrite a draft of the same name. Never an uploaded file")
    prepare = commands.add_parser("prepare", help="a draft of the thirteen boxes from a list of the period's documents")
    prepare.add_argument("--from", dest="start", required=True, metavar="YYYY-MM-DD", help="first day of the period")
    prepare.add_argument("--to", dest="end", required=True, metavar="YYYY-MM-DD", help="last day of the period")
    prepare.add_argument("--documents", required=True,
                         help="CSV, one row per document and VAT rate: document, date, type, counterparty, vat_number, "
                              "country, supply, net, vat, rate, addressed_to_company, treatment, cy_rate, note")
    prepare.add_argument("--map", action="append", default=[], metavar="FIELD=COLUMN",
                         help=f"name a column by hand. Fields: {', '.join(DOC_ALIASES)}")
    prepare.add_argument("--decimal", choices=["auto", "point", "comma"], default="auto")
    prepare.add_argument("--note", action="append", default=[], metavar="documents=STATEMENT",
                         help="the person's own statement that the documents are all of the period's")
    prepare.add_argument("--standard-rate", type=float, default=19.0, help="standard VAT rate in percent (default 19)")
    prepare.add_argument("--out", default=".", help="folder for the draft's files (default: here)")
    prepare.add_argument("--today", help=argparse.SUPPRESS)
    numbers = commands.add_parser("numbers", help="ask the EU's VIES service whether VAT numbers are registered")
    numbers.add_argument("vat_numbers", nargs="+", metavar="VAT_NUMBER")
    numbers.add_argument("--timeout", type=float, default=15.0, help="seconds to wait for VIES (default 15)")

    args = parser.parse_args()
    if args.command == "check":
        return command_return(args, build=False)
    if args.command == "xml":
        return command_return(args, build=True)
    if args.command == "vies":
        return command_vies(args)
    if args.command == "prepare":
        return command_prepare(args)
    return command_numbers(args)


if __name__ == "__main__":
    sys.exit(main())
