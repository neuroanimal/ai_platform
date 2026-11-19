"""
Spreadsheet for human review of benchmark answers (Excel .xlsx, openpyxl).

One row per item from ``review_service.review_items``. The ``verdict``
column has a drop-down (correct / incorrect / partial / unclear); everything
else is context. Hidden columns ``index`` and ``key`` let the import check
that the file belongs to the screening it is applied to - do not edit them.
"""

from typing import Any, Dict, List

from ai_platform.backend.service_layer.macro.llm_benchmark.review_service import (
    VERDICTS,
    ReviewError,
)

COLUMNS = [  # (field, header, width)
    ("index", "index", 6), ("key", "key", 10), ("model", "Model", 22),
    ("test_id", "Task", 22), ("language", "Lang", 6), ("run_index", "Run", 5),
    ("prompt", "Question", 40), ("expected", "Expected", 22), ("answer", "Answer", 80),
    ("automatic_status", "Rule status", 26), ("evidence", "Rule evidence", 40),
    ("verdict", "Verdict", 12), ("comment", "Comment", 30),
]
HIDDEN = ("index", "key")


def write_review_workbook(items: List[Dict[str, Any]], path: str,  # pylint: disable=too-many-locals
                          title: str = "Review") -> None:
    """Write the review spreadsheet."""
    from openpyxl import Workbook  # pylint: disable=import-outside-toplevel
    from openpyxl.styles import Alignment, Font  # pylint: disable=import-outside-toplevel
    from openpyxl.utils import get_column_letter  # pylint: disable=import-outside-toplevel
    from openpyxl.worksheet.datavalidation import (  # pylint: disable=import-outside-toplevel
        DataValidation,
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    sheet.append([header for _, header, _ in COLUMNS])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for item in items:
        sheet.append([_cell(item.get(field)) for field, _, _ in COLUMNS])
    wrap = Alignment(wrap_text=True, vertical="top")
    for number, (field, _, width) in enumerate(COLUMNS, start=1):
        letter = get_column_letter(number)
        sheet.column_dimensions[letter].width = width
        sheet.column_dimensions[letter].hidden = field in HIDDEN
        for row in sheet.iter_rows(min_row=2, min_col=number, max_col=number):
            row[0].alignment = wrap
    verdict_letter = get_column_letter([f for f, _, _ in COLUMNS].index("verdict") + 1)
    validation = DataValidation(type="list", formula1='"' + ",".join(VERDICTS) + '"',
                                allow_blank=True, showErrorMessage=True,
                                errorTitle="Verdict", error="Choose " + ", ".join(VERDICTS))
    sheet.add_data_validation(validation)
    validation.add(f"{verdict_letter}2:{verdict_letter}{max(2, len(items) + 1)}")
    sheet.freeze_panes = "C2"
    sheet.auto_filter.ref = sheet.dimensions
    workbook.save(path)


def read_review_workbook(path: str) -> List[Dict[str, Any]]:
    """Rows of a filled-in review spreadsheet as dicts keyed by field name."""
    from openpyxl import load_workbook  # pylint: disable=import-outside-toplevel

    sheet = load_workbook(path, read_only=True, data_only=True).active
    rows = sheet.iter_rows(values_only=True)
    headers = list(next(rows, []))
    expected = [header for _, header, _ in COLUMNS]
    if headers[:len(expected)] != expected:
        raise ReviewError(f"{path}: not a review sheet written by this tool (header {headers})")
    fields = [field for field, _, _ in COLUMNS]
    return [dict(zip(fields, row)) for row in rows if row and row[0] is not None]


def _cell(value: Any) -> Any:
    # Excel cells hold at most 32767 characters; long answers are cut with a mark.
    if isinstance(value, str) and len(value) > 32000:
        return value[:32000] + " [...]"
    return value
