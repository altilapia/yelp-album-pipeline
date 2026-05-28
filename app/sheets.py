from __future__ import annotations

import re

import gspread
from gspread import Worksheet

from app.config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID, GOOGLE_WORKSHEET_NAME

COLUMNS = [
    "name",
    "biz_url",
    "category",
    "rating",
    "review_count",
    "price",
    "city",
    "state",
]

_HEADER_RANGE = f"A1:{chr(ord('A') + len(COLUMNS) - 1)}1"

# Dark blue-grey header; light alternating bands
_HEADER_BG  = {"red": 0.149, "green": 0.196, "blue": 0.220}
_BAND_ODD   = {"red": 1.0,   "green": 1.0,   "blue": 1.0}
_BAND_EVEN  = {"red": 0.925, "green": 0.941, "blue": 0.961}


def _extract_url(cell: str) -> str:
    """Return the URL from =HYPERLINK("url","display"), or the cell value as-is."""
    if cell.startswith("=HYPERLINK("):
        m = re.match(r'=HYPERLINK\("([^"]+)"', cell)
        if m:
            return m.group(1)
    return cell


def _to_row(biz: dict) -> list:
    def _v(key):
        v = biz.get(key)
        return "" if v is None else v

    url = _v("biz_url")
    name = _v("name")
    url_link = f'=HYPERLINK("{url}","Yelp ↗")' if url else ""

    return [
        name,
        url_link,
        _v("category"),
        _v("rating"),
        _v("review_count"),
        _v("price"),
        _v("city"),
        _v("state"),
    ]


def _write_header(ws: Worksheet) -> None:
    ws.insert_row(COLUMNS, 1)

    # Styled header: dark background, white bold text, centered
    ws.format(_HEADER_RANGE, {
        "backgroundColor": _HEADER_BG,
        "textFormat": {
            "bold": True,
            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
        },
        "horizontalAlignment": "CENTER",
    })

    # Clear any residual bold from data rows (old headers shifted down)
    _data_range = f"A2:{chr(ord('A') + len(COLUMNS) - 1)}1000"
    ws.format(_data_range, {"textFormat": {"bold": False}})

    # Rating column: always show one decimal place (4.0 not 4)
    _rating_col = chr(ord('A') + COLUMNS.index("rating"))
    ws.format(
        f"{_rating_col}2:{_rating_col}1000",
        {"numberFormat": {"type": "NUMBER", "pattern": "0.0"}},
    )

    # Freeze header row so it stays visible while scrolling
    ws.freeze(rows=1)

    sid = ws.id
    # Tab color is always safe to set
    ws.spreadsheet.batch_update({"requests": [
        {"updateSheetProperties": {
            "properties": {"sheetId": sid, "tabColor": _HEADER_BG},
            "fields": "tabColor",
        }},
    ]})
    # Banding fails if already present — skip gracefully
    try:
        ws.spreadsheet.batch_update({"requests": [
            {"addBanding": {"bandedRange": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(COLUMNS),
                },
                "rowProperties": {
                    "firstBandColor": _BAND_ODD,
                    "secondBandColor": _BAND_EVEN,
                },
            }}},
        ]})
    except gspread.exceptions.APIError:
        pass

    ws.set_basic_filter()


def _upsert(ws: Worksheet, businesses: list[dict]) -> dict:
    """Updates existing rows (matched by biz_url) and appends new ones."""
    # Use FORMULA render so we can extract URLs from HYPERLINK cells
    all_values = ws.get_all_values(value_render_option="FORMULA")

    if not all_values:
        _write_header(ws)
        all_values = [COLUMNS]
    elif not all_values[0] or all_values[0][0] != COLUMNS[0]:
        _write_header(ws)
        all_values = [COLUMNS] + all_values

    header = all_values[0]
    data_rows = all_values[1:]

    url_col = header.index("biz_url") if "biz_url" in header else 1

    # biz_url -> 1-based sheet row number
    url_to_row: dict[str, int] = {}
    for i, row in enumerate(data_rows, start=2):
        raw = row[url_col] if len(row) > url_col else ""
        url = _extract_url(raw)
        if url.startswith("/"):
            url = "https://www.yelp.com" + url
        if url:
            url_to_row[url] = i

    updates: list[dict] = []
    new_rows: list[list] = []

    for biz in businesses:
        url = biz.get("biz_url", "")
        if url in url_to_row:
            updates.append({
                "range": f"A{url_to_row[url]}",
                "values": [_to_row(biz)],
            })
        else:
            new_rows.append(_to_row(biz))

    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")

    # Resize after data is written so columns fit the largest entry, not just the header
    ws.spreadsheet.batch_update({"requests": [{"autoResizeDimensions": {"dimensions": {
        "sheetId": ws.id,
        "dimension": "COLUMNS",
        "startIndex": 0,
        "endIndex": len(COLUMNS),
    }}}]})

    return {"new": len(new_rows), "updated": len(updates)}


def _get_worksheet() -> Worksheet:
    client = gspread.service_account(filename=str(GOOGLE_CREDENTIALS_PATH))
    sh = client.open_by_key(GOOGLE_SHEET_ID)
    return sh.worksheet(GOOGLE_WORKSHEET_NAME)


def upload(businesses: list[dict]) -> dict:
    """Upsert businesses to the configured Google Sheet.

    Returns {'new': int, 'updated': int}.
    """
    return _upsert(_get_worksheet(), businesses)
