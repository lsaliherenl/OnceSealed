"""Read a project document's table of yearly net GHG emission reductions or removals.

Verra project descriptions (and monitoring reports) carry a table with one row per year and columns for
baseline emissions, project emissions, leakage and net reductions. The parser is deliberately strict: it
uses a table only when it can tell which column holds the net figure, and it reports the page, the table id
and the rows it read, so every number can be checked against the PDF. Rows covering more than one calendar
year (monitoring periods) are kept aside rather than split.

PDF tables often have merged header cells, so header labels and numbers do not share column indexes. The
parser therefore pairs the non-empty header labels with the non-empty numbers of each row, in order.
"""

import re
from dataclasses import dataclass, field

from core.ai.pdf_extract import Table

YEAR = re.compile(r"\b(19[89]\d|20\d\d)\b")
MONTH = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", re.I)
FULL_YEAR = re.compile(r"\b0?1\W*(st\W*)?jan[a-z]*\b.*\b31\W*(st\W*)?dec", re.I)
REDUCTION_WORDS = ("reduction", "removal")
# Tables of one component of the total (e.g. "Net GHG removal from ARR" split by deforestation agent) are not
# the project's yearly net figure; reading them would compare issuance with a fraction of it.
COMPONENT = re.compile(r"\b(?i:from)\s+(ARR|REDD|WRC|IFM|ALM|APD|AUDD)\b|\b[Aa]gents?\s+[A-Z]\b")
OTHER_COLUMNS = ("baseline", "project emission", "leakage", "buffer", "uncertainty", "deduction")


def parse_number(text: str) -> float | None:
    """'1,422,028' -> 1422028; '2,087,787.68' -> 2087787.68; '1.422.028' -> 1422028; '-' or text -> None."""
    s = text.strip().replace("−", "-").replace(" ", "").replace(" ", "")
    if not re.fullmatch(r"-?[\d.,]+", s) or not re.search(r"\d", s):
        return None
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):  # dots as thousands separators
        s = s.replace(".", "")
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


@dataclass(frozen=True)
class EstimateTable:
    table_id: str
    page: int
    column: str  # header label of the column read
    by_year: dict[int, float]
    total: float | None
    multi_year_rows: list[str] = field(default_factory=list)
    partial_years: frozenset[int] = frozenset()  # rows covering part of a calendar year (start or end of a period)
    rows_text: list[str] = field(default_factory=list)  # the rows read, as rendered text, for the evidence trail


def _label_index(row: list[str]) -> int | None:
    return next((i for i, c in enumerate(row) if c), None)


def _numbers(row: list[str]) -> list[float]:
    """Numbers in the cells after the row label (the label itself may be a year)."""
    i = _label_index(row)
    if i is None:
        return []
    return [v for v in (parse_number(c) for c in row[i + 1:] if c) if v is not None]


def _header_labels(header_rows: list[list[str]], width: int) -> list[tuple[int, str]]:
    labels = []
    for col in range(width):
        text = " ".join(r[col] for r in header_rows if col < len(r) and r[col]).strip()
        if text:
            labels.append((col, text))
    return labels[1:]  # the first labelled column holds the year or period


def _net_column(labels: list[str]) -> int | None:
    lower = [x.lower() for x in labels]
    usable = [i for i, x in enumerate(lower) if "cumulative" not in x]
    net = [i for i in usable if "net" in lower[i].split() and any(w in lower[i] for w in REDUCTION_WORDS)
           and "baseline" not in lower[i]]
    if net:
        return net[-1]
    plain = [i for i in usable
             if any(w in lower[i] for w in REDUCTION_WORDS) and not any(o in lower[i] for o in OTHER_COLUMNS)]
    return plain[-1] if plain else None


def _partial(label: str) -> bool:
    """A row label naming months is a partial year unless it runs 1 January to 31 December."""
    return bool(MONTH.search(label)) and not FULL_YEAR.search(label)


def _is_total(label: str) -> bool:
    low = label.lower()
    return low.startswith("total") and not any(w in low for w in ("number", "years", "average", "crediting year"))


def read_estimate_table(table: Table) -> EstimateTable | None:
    rows = table.rows
    first_data = next((i for i, r in enumerate(rows) if _numbers(r)), None)
    if not first_data:
        return None
    width = max(len(r) for r in rows)
    labels = _header_labels(rows[:first_data], width)
    if not any(w in " ".join(t for _, t in labels).lower() for w in REDUCTION_WORDS):
        return None
    target = _net_column([t for _, t in labels])
    if target is None or COMPONENT.search(" ".join(t for _, t in labels)):
        return None

    # Group rows into records: a row with numbers starts a record; rows without numbers continue its label
    # (PDF tables often wrap a date range such as "05-August-2020 - 31-December-2020" over several rows).
    records: list[tuple[list[str], list[float], int]] = []  # label parts, numbers, column of the last number
    for row in rows[first_data:]:
        nums = _numbers(row)
        cells = [c for c in row if c]
        if nums:
            last_col = max(i for i, c in enumerate(row) if c and parse_number(c) is not None)
            records.append(([cells[0]] if cells else [], nums, last_col))
        elif cells and records:
            records[-1][0].extend(cells)
    net_col = labels[target][0]

    by_year: dict[int, float] = {}
    total = None
    multi: list[str] = []
    read: list[str] = []
    partial: set[int] = set()
    for label_parts, values, last_col in records:
        label = " ".join(label_parts)
        if len(values) == len(labels):
            value = values[target]
        elif target == len(labels) - 1 and (last_col == net_col or (len(values) > 1 and last_col >= net_col - 2)):
            # the net column is the last one and the row's last number sits under it (merged cells can shift
            # a column or two, but a lone number elsewhere may be another column, e.g. project emissions)
            value = values[-1]
        else:
            continue
        line = f"{label} | {value:,.0f}"
        years = sorted(set(YEAR.findall(label)))
        if _is_total(label):
            if total is None:
                total = value
                read.append(line)
        elif len(years) == 1:
            by_year[int(years[0])] = value
            if _partial(label):
                partial.add(int(years[0]))
            read.append(line)
        elif len(years) > 1:
            multi.append(line)
    if len(by_year) < 2:
        return None
    return EstimateTable(table_id=table.id, page=table.page, column=labels[target][1], by_year=by_year, total=total,
                         multi_year_rows=multi, partial_years=frozenset(partial), rows_text=read)


def find_estimate_tables(tables: list[Table]) -> list[EstimateTable]:
    return [e for e in (read_estimate_table(t) for t in tables) if e is not None]
