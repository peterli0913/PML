"""由《单元操作时间》计算操作工生产进度奖。

用法：
  python build_bonus.py
  python build_bonus.py --input 单元操作时间.xlsx --template 月--操作工2026版.xlsx --output 结果.xlsx

金额用 Decimal 四舍五入到分。进度奖比例按模板公式的分档，不用其中会让乘法报错的文本 "200%" / "50%"。
"""
from __future__ import annotations

import argparse
import re
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MONEY = Decimal("0.01")
ALIASES = {"加料": "投料", "调pH": "调PH", "调ph": "调PH", "调PH": "调PH"}
NAME_SPLIT = re.compile(r"[、,，/;；\s]+")
NUM_PREFIX = re.compile(r"^\d+\s*[、.．]\s*")

def _side(style):
    return Side(style=style, color="000000") if style else Side(style=None)


def _box(left="thin", right="thin", top="thin", bottom="thin"):
    return Border(left=_side(left), right=_side(right), top=_side(top), bottom=_side(bottom))


THIN_BOX = _box()
GRAY = PatternFill("solid", fgColor="C0C0C0")
BLUE = PatternFill("solid", fgColor="CCECFF")
YELLOW = PatternFill("solid", fgColor="FFFF99")
CREAM = PatternFill("solid", fgColor="FFCC99")
WHITE = PatternFill("solid", fgColor="FFFFFF")
WARN = PatternFill("solid", fgColor="FFF2CC")

F_CAL9 = Font(name="Calibri", size=9)
F_CAL9B = Font(name="Calibri", size=9, bold=True)
F_CAL9B_RED = Font(name="Calibri", size=9, bold=True, color="FF0000")
F_CAL9B_BLUE = Font(name="Calibri", size=9, bold=True, color="0000FF")
F_SONG9 = Font(name="宋体", size=9)
F_SONG9B = Font(name="宋体", size=9, bold=True)
F_SONG10B = Font(name="宋体", size=10, bold=True)
F_DX9B = Font(name="等线", size=9, bold=True)
F_ARIAL9 = Font(name="Arial", size=9)
F_ARIAL9B = Font(name="Arial", size=9, bold=True)
F_ARIAL9B_BLUE = Font(name="Arial", size=9, bold=True, color="0000FF")
F_ARIAL10B = Font(name="Arial", size=10, bold=True)
F_ARIAL11B = Font(name="Arial", size=11, bold=True)
F_TITLE = Font(name="宋体", size=12, bold=True)

FMT_HOUR = '0.0"h"'
FMT_YUAN = '¥#,##0.00;[Red](¥#,##0.00)'
FMT_YUAN_1 = '0.0"元"'
FMT_COEF = "0.0000"
FMT_PCT = "0.00%"
FMT_BATCH = '0"批"'
FMT_BATCH_1 = '0.0"批"'


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def D(value) -> Decimal:
    return Decimal(str(value))


def progress_factor(ratio: Decimal) -> Decimal:
    """与 Sheet15 的 AH13 同一套分档。<= -10% 为 2，>= 50% 为 0.5，刚好 0 为 1.3。"""
    if ratio <= D("-0.1"):
        return D("2")
    if ratio >= D("0.5"):
        return D("0.5")
    if ratio == 0:
        return D("1.3")
    bands = [(D("-0.1"), D("1.7")), (D("-0.05"), D("1.5")), (D("-0.03"), D("1.3")),
             (D("0"), D("1")), (D("0.2"), D("0.8")), (D("0.5"), D("0.5"))]
    rate = bands[0][1]
    for bound, value in bands:
        if bound <= ratio:
            rate = value
        else:
            break
    return rate


def norm(text) -> str:
    return re.sub(r"\s+", "", "" if text is None else str(text))


def operation_name(raw) -> str:
    name = NUM_PREFIX.sub("", "" if raw is None else str(raw).strip())
    return ALIASES.get(name, name)


def split_names(raw) -> list[str]:
    text = "" if raw is None else str(raw).strip()
    return [part for part in NAME_SPLIT.split(text) if part]


def colrow(ref: str) -> tuple[int, int]:
    col = "".join(ch for ch in ref if ch.isalpha())
    row = int("".join(ch for ch in ref if ch.isdigit()) or 0)
    number = 0
    for ch in col:
        number = number * 26 + ord(ch) - 64
    return number, row


def load_rates(template: Path):
    """从模板的「计件标准」读取设备×操作系数，和单批标准 150。"""
    z = zipfile.ZipFile(template)
    strings = []
    sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
    for si in sst.findall("m:si", NS):
        strings.append("".join(t.text or "" for t in si.iter(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
    root = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = None
    for sh in root.find("m:sheets", NS):
        if sh.attrib["name"] == "计件标准":
            rid = sh.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = {r.attrib["Id"]: r.attrib["Target"] for r in rels}[rid]
    if target is None:
        raise SystemExit("模板里没有「计件标准」")
    if not target.startswith("xl/"):
        target = "xl/" + target
    sheet = ET.fromstring(z.read(target))
    cells: dict[tuple[int, int], str] = {}
    for cell in sheet.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
        ref = cell.attrib.get("r")
        if not ref:
            continue
        col, row = colrow(ref)
        if row > 40 or col > 25:
            continue
        value = cell.find("m:v", NS)
        if value is None or value.text is None:
            continue
        cells[(row, col)] = strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text

    headers = {col: cells[(1, col)] for col in range(4, 26) if (1, col) in cells}
    rates: dict[str, dict[str, Decimal]] = {}
    for row in range(2, 38):
        if cells.get((row, 2)) != "标准系数":
            continue
        equipment = cells.get((row, 1))
        if not equipment:
            continue
        rates[equipment] = {name: D(cells[(row, col)]) for col, name in headers.items() if (row, col) in cells}
    price = D(cells[(40, 2)])
    return rates, headers, price


def resolve_equipment(raw, rates: dict) -> str | None:
    text = "" if raw is None else str(raw).strip()
    if not text:
        return None
    if text in rates:
        return text
    compact = norm(text)
    matches = [name for name in rates if norm(name) == compact or norm(name).startswith(compact)]
    if len(matches) == 1:
        return matches[0]
    number = re.match(r"^(\d+)", compact)
    if number:
        prefixed = [name for name in rates if norm(name).startswith(number.group(1) + "L")]
        if len(prefixed) == 1:
            return prefixed[0]
    return None


def parse_input(path: Path) -> list[dict]:
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)
    projects = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        starts = [col for col in range(1, ws.max_column + 1)
                  if "序号" in norm(ws.cell(2, col).value)]
        batches = []
        for index, start in enumerate(starts):
            end = (starts[index + 1] - 1) if index + 1 < len(starts) else ws.max_column
            fields = {}
            for col in range(start, end + 1):
                key = norm(ws.cell(2, col).value)
                if "序号" in key:
                    fields["seq"] = col
                elif "标准时间" in key:
                    fields["standard"] = col
                elif "设备规格" in key:
                    fields["equipment"] = col
                elif "操作总时长" in key:
                    fields["actual"] = col
                elif "操作人员" in key:
                    fields["people"] = col
            if not {"seq", "standard", "actual", "people"} <= fields.keys():
                batches.append({"batch_id": ws.cell(1, start).value, "error": f"{sheet_name} 第 {start} 列表头不完整", "ops": []})
                continue
            ops = []
            for row in range(3, ws.max_row + 1):
                seq = ws.cell(row, fields["seq"]).value
                if seq in (None, ""):
                    continue
                actual = ws.cell(row, fields["actual"]).value
                ops.append({
                    "seq": str(seq).strip(),
                    "raw_name": str(seq).strip(),
                    "name": operation_name(seq),
                    "standard": ws.cell(row, fields["standard"]).value,
                    "equipment": ws.cell(row, fields["equipment"]).value if "equipment" in fields else None,
                    "actual": actual,
                    "people": split_names(ws.cell(row, fields["people"]).value),
                })
            batches.append({"batch_id": str(ws.cell(1, start).value or "").strip(), "error": "", "ops": ops})
        projects.append({"sheet": sheet_name, "project": sheet_name, "batches": batches})
    return projects


def calculate(projects, rates, price) -> tuple[list[dict], list[str]]:
    warnings = []
    results = []
    known_names = {name for table in rates.values() for name in table}
    for project in projects:
        batch_results = []
        for batch in project["batches"]:
            if batch["error"]:
                warnings.append(batch["error"])
                continue
            if not batch["ops"]:
                warnings.append(f"{batch['batch_id']} 没有操作行，已跳过")
                continue
            counted = []
            for op in batch["ops"]:
                actual = None
                if op["actual"] not in (None, ""):
                    try:
                        actual = D(op["actual"])
                    except Exception:
                        warnings.append(f"{batch['batch_id']} 「{op['raw_name']}」实际用时不是数字")
                if actual is None and not op["people"]:
                    continue
                if actual is None or not op["people"]:
                    warnings.append(f"{batch['batch_id']} 「{op['raw_name']}」只填了用时或人员其中一项，不参与本批对比")
                    continue
                if op["name"] not in known_names:
                    warnings.append(f"{batch['batch_id']} 「{op['raw_name']}」对不上计件标准的操作名称，标准系数按 0")
                equipment = resolve_equipment(op["equipment"], rates)
                if equipment is None:
                    warnings.append(f"{batch['batch_id']} 「{op['raw_name']}」设备规格为空或无法对应，标准系数按 0")
                try:
                    standard = D(op["standard"]) if op["standard"] not in (None, "") else None
                except Exception:
                    standard = None
                    warnings.append(f"{batch['batch_id']} 「{op['raw_name']}」标准时间不是数字")
                if standard is None:
                    continue
                coef = rates.get(equipment, {}).get(op["name"], D("0")) if equipment else D("0")
                counted.append({**op, "standard": standard, "actual": actual, "coef": coef,
                                "theoretical": coef * price})
            if not counted:
                warnings.append(f"{batch['batch_id']} 还没有填写实际用时和操作人员")
                continue
            standard_sum = sum(op["standard"] for op in counted)
            actual_sum = sum(op["actual"] for op in counted)
            ratio = (actual_sum - standard_sum) / standard_sum if standard_sum else D("0")
            factor = progress_factor(ratio)
            person_bonus: dict[str, Decimal] = {}
            person_hours: dict[str, Decimal] = {}
            person_matrix: dict[str, list[Decimal]] = {}
            order: list[str] = []
            for op_index, op in enumerate(counted):
                share_hours = op["actual"] / D(len(op["people"]))
                share_bonus = op["theoretical"] / D(len(op["people"]))
                for person in op["people"]:
                    if person not in person_bonus:
                        order.append(person)
                        person_bonus[person] = D("0")
                        person_hours[person] = D("0")
                        person_matrix[person] = [D("0")] * len(counted)
                    person_hours[person] += share_hours
                    person_bonus[person] += share_bonus
                    person_matrix[person][op_index] = share_hours
            people = []
            for person in order:
                piece = person_bonus[person]
                final = money(piece * factor)
                people.append({
                    "name": person,
                    "hours": person_hours[person],
                    "hours_by_op": person_matrix[person],
                    "piece": piece,
                    "bonus": final,
                })
            batch_results.append({
                "batch_id": batch["batch_id"],
                "ops": counted,
                "standard_sum": standard_sum,
                "actual_sum": actual_sum,
                "ratio": ratio,
                "factor": factor,
                "coef_sum": sum(op["coef"] for op in counted),
                "people": people,
            })
        if batch_results:
            results.append({"sheet": project["sheet"], "project": project["project"], "batches": batch_results})
    return results, warnings


def put(ws, row, col, value=None, font=None, fill=None, border=THIN_BOX,
        align="center", wrap=False, fmt=None):
    cell = ws.cell(row, col)
    if value is not None:
        cell.value = value
    cell.font = font or F_CAL9
    cell.fill = fill or WHITE
    cell.border = border
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    if fmt:
        cell.number_format = fmt
    return cell


def paint_merge(ws, r1, c1, r2, c2, value, font, fill, border=THIN_BOX,
                align="center", wrap=False, fmt=None):
    for row in range(r1, r2 + 1):
        for col in range(c1, c2 + 1):
            put(ws, row, col, font=font, fill=fill, border=border, align=align, wrap=wrap)
    origin = ws.cell(r1, c1, value)
    if fmt:
        origin.number_format = fmt
    if r1 != r2 or c1 != c2:
        ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
    return origin


def prepare_sheet(ws):
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.horizontalCentered = True
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = 0.4
    ws.page_margins.right = 0.4
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5
    ws.page_margins.header = 0.2
    ws.page_margins.footer = 0.2
    ws.sheet_properties.tabColor = "1F4E79"
    ws.oddFooter.right.text = "第 &P 页"
    ws.oddFooter.left.text = "操作工生产进度奖"


def write_block(ws, start, batch, price):
    """按原表 Sheet15 的区块写一批：标准区在上，人员工时在下。"""
    ops = batch["ops"]
    people = batch["people"]
    count = len(ops)
    first = 4
    last = 3 + count
    s_sum, s_count, s_piece, s_bonus = last + 1, last + 2, last + 3, last + 4
    r0 = start
    r_step, r_name = start + 1, start + 2
    r_count, r_std = start + 3, start + 4
    r_coef, r_theory = start + 5, start + 6
    r_again, r_batch = start + 7, start + 8
    r_head, r_time, r_person = start + 9, start + 10, start + 11
    r_data = start + 12
    r_last = r_data + len(people) - 1
    r_rate = r_last + 1
    first_letter = get_column_letter(first)
    last_letter = get_column_letter(last)

    equipments = []
    for op in ops:
        name = op.get("equipment") or ""
        if name and name not in equipments:
            equipments.append(name)

    ws.row_dimensions[r0].height = 22
    ws.row_dimensions[r_step].height = 32
    for row in (r_name, r_count, r_std, r_coef, r_theory, r_again):
        ws.row_dimensions[row].height = 20
    for row in (r_batch, r_head, r_time, r_person):
        ws.row_dimensions[row].height = 24
    for row in range(r_data, r_rate + 1):
        ws.row_dimensions[row].height = 18

    paint_merge(ws, r0, 1, r0, 2, batch["batch_id"], F_TITLE, WHITE, align="center")
    put(ws, r0, 3, "计件标准值", font=F_CAL9B, fill=WHITE, align="left")
    paint_merge(ws, r_step, 1, r_step, 2, "步骤", F_CAL9B, WHITE)
    put(ws, r_step, 3, "合计", font=F_CAL9B, fill=WHITE)
    paint_merge(ws, r_name, 1, r_name, 2, "单元操作标准描述", F_CAL9B, WHITE, wrap=True)
    put(ws, r_name, 3, font=F_CAL9, fill=WHITE)

    for row in range(r_count, r_theory + 1):
        put(ws, row, 1, font=F_CAL9B, fill=WHITE, wrap=True)
    ws.cell(r_count, 1).value = "\n".join(equipments)
    ws.cell(r_count, 1).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.merge_cells(start_row=r_count, start_column=1, end_row=r_theory, end_column=1)
    put(ws, r_count, 2, "操作次数", font=F_CAL9B, fill=WHITE)
    put(ws, r_std, 2, "标准时间", font=F_CAL9B, fill=WHITE)
    put(ws, r_coef, 2, "标准系数", font=F_CAL9B, fill=WHITE)
    put(ws, r_theory, 2, "理论奖金", font=F_CAL9B_RED, fill=WHITE)
    put(ws, r_count, 3, f"=SUM({first_letter}{r_count}:{last_letter}{r_count})", font=F_CAL9B, fill=WHITE, fmt="0")
    put(ws, r_std, 3, f"=SUM({first_letter}{r_std}:{last_letter}{r_std})", font=F_CAL9B, fill=WHITE, fmt=FMT_HOUR)
    put(ws, r_coef, 3, f"=SUM({first_letter}{r_coef}:{last_letter}{r_coef})", font=F_CAL9B, fill=WHITE, fmt=FMT_COEF)
    put(ws, r_theory, 3, f"=SUM({first_letter}{r_theory}:{last_letter}{r_theory})", font=F_CAL9B_RED, fill=WHITE, fmt=FMT_YUAN_1)

    price_text = format(price, "f")
    for offset, op in enumerate(ops):
        col = first + offset
        letter = get_column_letter(col)
        put(ws, r_step, col, op["seq"], font=F_DX9B, fill=WHITE, wrap=True)
        put(ws, r_name, col, op["name"], font=F_CAL9B, fill=WHITE, wrap=True)
        put(ws, r_count, col, 1, font=F_CAL9, fill=WHITE, fmt="0")
        put(ws, r_std, col, float(op["standard"]), font=F_CAL9, fill=WHITE, fmt=FMT_HOUR)
        put(ws, r_coef, col, float(op["coef"]), font=F_CAL9, fill=WHITE, fmt=FMT_COEF)
        put(ws, r_theory, col, f"={letter}{r_coef}*{price_text}", font=F_CAL9B_RED, fill=WHITE, fmt=FMT_YUAN_1)
        put(ws, r_head, col, f"={letter}{r_step}", font=F_CAL9, fill=BLUE, wrap=True)
        put(ws, r_time, col, font=F_CAL9, fill=WHITE)
        put(ws, r_person, col, f"={letter}{r_theory}", font=F_CAL9B, fill=BLUE, fmt=FMT_YUAN_1)

    paint_merge(ws, r_again, 1, r_again, 2, f"=A{r0}", F_CAL9B, WHITE, align="center")
    put(ws, r_again, 3, "计件统计", font=F_CAL9B, fill=WHITE, align="left")
    put(ws, r_batch, 1, "批次", font=F_CAL9, fill=BLUE, wrap=True)
    paint_merge(ws, r_batch, 2, r_person, 2, "计件奖合计", F_CAL9B_BLUE, BLUE, wrap=True)
    put(ws, r_head, 1, "步骤", font=F_CAL9, fill=BLUE, wrap=True)
    put(ws, r_head, 3, font=F_CAL9, fill=BLUE)
    put(ws, r_time, 1, "时间", font=F_CAL9, fill=GRAY, align="right")
    put(ws, r_time, 3, font=F_CAL9, fill=WHITE)
    put(ws, r_person, 1, "操作人", font=F_CAL9, fill=GRAY, align="left")
    put(ws, r_person, 3, font=F_CAL9, fill=WHITE)

    put(ws, r_head, s_sum, "单批用时及奖金", font=F_CAL9B, fill=BLUE, wrap=True)
    put(ws, r_head, s_count, "参与操作个数", font=F_CAL9B_BLUE, fill=YELLOW, wrap=True)
    put(ws, r_head, s_piece, "个人计件奖", font=F_CAL9B_RED, fill=YELLOW, wrap=True)
    put(ws, r_head, s_bonus, "个人生产进度奖", font=F_CAL9B_RED, fill=YELLOW, wrap=True)
    hour_grid = f"{first_letter}{r_data}:{last_letter}{r_last}"
    put(ws, r_time, s_sum, f"=SUM({hour_grid})", font=F_CAL9B, fill=BLUE, fmt=FMT_HOUR)
    put(ws, r_time, s_count, "标准时间：", font=F_CAL9, fill=YELLOW)
    put(ws, r_time, s_piece, f"=$C${r_std}", font=F_CAL9B_BLUE, fill=YELLOW, fmt=FMT_HOUR)
    actual_cell = f"{get_column_letter(s_piece)}{r_person}"
    put(ws, r_time, s_bonus, f"=IF(C{r_std}=0,0,({actual_cell}-C{r_std})/C{r_std})", font=F_CAL9, fill=YELLOW, fmt=FMT_PCT)
    put(ws, r_person, s_sum, f"=SUM({first_letter}{r_person}:{last_letter}{r_person})", font=F_CAL9B, fill=BLUE, fmt=FMT_YUAN_1)
    put(ws, r_person, s_count, "实际用时：", font=F_CAL9, fill=YELLOW)
    put(ws, r_person, s_piece, f"=SUM({hour_grid})", font=F_CAL9, fill=YELLOW, fmt=FMT_HOUR)
    put(ws, r_person, s_bonus, float(batch["factor"]), font=F_CAL9B_RED, fill=YELLOW, fmt="0%")

    head = f"${first_letter}${r_head}:${get_column_letter(s_bonus)}${r_head}"
    for index, person in enumerate(people):
        row = r_data + index
        put(ws, row, 1, person["name"], font=F_SONG9, fill=WHITE)
        bonus_range = f"{first_letter}{row}:{get_column_letter(s_bonus)}{row}"
        put(ws, row, 2, f'=SUMIF({head},"个人生产进度奖",{bonus_range})', font=F_CAL9B_BLUE, fill=BLUE, fmt=FMT_YUAN)
        put(ws, row, 3, font=F_CAL9, fill=WHITE)
        for offset, hours in enumerate(person["hours_by_op"]):
            col = first + offset
            if hours:
                put(ws, row, col, float(hours), font=F_CAL9, fill=WHITE, fmt=FMT_HOUR)
            else:
                put(ws, row, col, font=F_CAL9, fill=WHITE, fmt=FMT_HOUR)
        put(ws, row, s_sum, f"=SUM({first_letter}{row}:{last_letter}{row})", font=F_CAL9, fill=YELLOW, fmt=FMT_HOUR)
        put(ws, row, s_count, f'=COUNTIF({first_letter}{row}:{last_letter}{row},">0")', font=F_CAL9, fill=YELLOW, fmt="0")
        put(ws, row, s_piece, float(person["piece"]), font=F_CAL9B, fill=CREAM, fmt=FMT_YUAN)
        put(ws, row, s_bonus, float(person["bonus"]), font=F_CAL9B_RED, fill=CREAM, fmt=FMT_YUAN)

    put(ws, r_rate, 1, "单人计件奖金", font=F_CAL9, fill=BLUE, wrap=True)
    put(ws, r_rate, 2, f"=SUM(B{r_data}:B{r_last})", font=F_CAL9B_BLUE, fill=BLUE, fmt=FMT_YUAN)
    put(ws, r_rate, 3, font=F_CAL9, fill=BLUE)
    for offset in range(count):
        letter = get_column_letter(first + offset)
        hours = f"{letter}{r_data}:{letter}{r_last}"
        put(ws, r_rate, first + offset,
            f'=IF(SUM({hours})=0,"",{letter}{r_theory}/SUM({hours}))',
            font=F_CAL9B, fill=BLUE, fmt=FMT_YUAN)
    for col in (s_sum, s_count, s_piece, s_bonus):
        put(ws, r_rate, col, font=F_CAL9, fill=BLUE)

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 12
    for col in range(first, last + 1):
        ws.column_dimensions[get_column_letter(col)].width = 12
    for col in (s_sum, s_count, s_piece, s_bonus):
        ws.column_dimensions[get_column_letter(col)].width = 14
    return {
        "id_cell": f"$A${r0}",
        "coef_cell": f"$C${r_coef}",
        "lookup": f"$A${r_data}:$B${r_last}",
        "next_row": r_rate + 2,
    }


def write_summary(ws, anchors, names):
    prepare_sheet(ws)
    ws.sheet_properties.tabColor = "C65911"
    ws.row_dimensions[1].height = 49.5
    title = ws.cell(1, 1, "2026年 月份车间生产进度奖")
    title.font = F_ARIAL11B
    title.alignment = Alignment(horizontal="left", vertical="center")
    title.border = Border(bottom=_side("medium"))
    for row in (2, 3, 4, 5):
        ws.row_dimensions[row].height = 22
    ws.row_dimensions[2].height = 36
    top = _box(top="medium")
    left_top = _box(left="medium", top="medium")
    paint_merge(ws, 2, 1, 5, 2, "No.", F_ARIAL9, GRAY, border=left_top)
    put(ws, 2, 3, "项目号", font=F_SONG9, fill=GRAY, border=top, wrap=True)
    for row in (3, 4, 5):
        put(ws, row, 3, font=F_SONG9, fill=GRAY)
    ws.cell(3, 3).value = "生产批数"
    ws.cell(4, 3).value = "标准系数"
    ws.cell(5, 3).value = "折算批次"
    paint_merge(ws, 2, 4, 5, 4, "生产进度奖核算金额", F_ARIAL9B_BLUE, GRAY, border=top, wrap=True)
    paint_merge(ws, 2, 5, 5, 5, "进度延误扣款金额", F_SONG9B, GRAY, border=top, wrap=True)
    put(ws, 2, 6, "合计", font=F_SONG10B, fill=GRAY, border=top)
    for row, fmt in ((3, FMT_BATCH), (4, FMT_COEF), (5, FMT_BATCH_1)):
        put(ws, row, 6, font=F_ARIAL10B, fill=GRAY, fmt=fmt)
    last_col = 6 + len(anchors)
    if anchors:
        start, end = get_column_letter(7), get_column_letter(last_col)
        ws.cell(3, 6).value = f"=SUM({start}3:{end}3)"
        ws.cell(4, 6).value = f"=SUM({start}4:{end}4)"
        ws.cell(5, 6).value = f"=SUM({start}5:{end}5)"
    for index, anchor in enumerate(anchors):
        col = 7 + index
        letter = get_column_letter(col)
        sheet = anchor["sheet"]
        put(ws, 2, col, f"='{sheet}'!{anchor['id_cell']}", font=F_SONG9, fill=GRAY, border=top, wrap=True)
        put(ws, 3, col, 1, font=F_ARIAL9, fill=GRAY, fmt=FMT_BATCH)
        put(ws, 4, col, f"='{sheet}'!{anchor['coef_cell']}", font=F_SONG9, fill=GRAY, wrap=True, fmt=FMT_COEF)
        put(ws, 5, col, f"={letter}3*{letter}4", font=F_ARIAL9, fill=GRAY, fmt=FMT_BATCH_1)
        ws.column_dimensions[letter].width = 14
    for index, name in enumerate(names):
        row = 6 + index
        ws.row_dimensions[row].height = 21.75
        put(ws, row, 1, "=ROW()-5", font=F_ARIAL9, fill=WHITE, border=_box(left="medium"))
        put(ws, row, 2, font=F_ARIAL9, fill=WHITE)
        put(ws, row, 3, name, font=F_SONG9, fill=WHITE)
        put(ws, row, 4, f"=F{row}", font=F_ARIAL9B_BLUE, fill=WHITE, fmt=FMT_YUAN)
        put(ws, row, 5, 0, font=F_SONG9B, fill=WHITE, fmt=FMT_YUAN)
        if anchors:
            start, end = get_column_letter(7), get_column_letter(last_col)
            put(ws, row, 6, f"=SUM({start}{row}:{end}{row})", font=F_ARIAL9B, fill=WHITE, fmt=FMT_YUAN)
        else:
            put(ws, row, 6, 0, font=F_ARIAL9B, fill=WHITE, fmt=FMT_YUAN)
        for anchor_index, anchor in enumerate(anchors):
            lookup = f"'{anchor['sheet']}'!{anchor['lookup']}"
            formula = f'=IF(ISNA(VLOOKUP($C{row},{lookup},2,FALSE)),0,VLOOKUP($C{row},{lookup},2,FALSE))'
            put(ws, row, 7 + anchor_index, formula, font=F_ARIAL9, fill=WHITE, fmt=FMT_YUAN)
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 4
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 12
    ws.freeze_panes = "G6"
    ws.print_title_rows = "1:5"
    ws.page_setup.orientation = "landscape"
    ws.oddHeader.center.text = '&"宋体,Bold"操作工生产进度奖'


def write_output(path: Path, results, warnings, rates, price):
    wb = Workbook()
    summary = wb.active
    summary.title = "生产进度奖"
    anchors = []
    for project_index, project in enumerate(results):
        ws = wb.create_sheet(f"Sheet{15 + project_index}")
        prepare_sheet(ws)
        row = 1
        for batch in project["batches"]:
            anchor = write_block(ws, row, batch, price)
            anchor["sheet"] = ws.title
            anchors.append(anchor)
            row = anchor["next_row"]
        ws.oddHeader.center.text = project["project"]
        ws.page_setup.fitToWidth = 1
        ws.print_title_rows = "1:1"
        ws.freeze_panes = "D2"
        ws.page_setup.orientation = "landscape"
        ws.sheet_view.zoomScale = 110
    names = []
    seen = set()
    for project in results:
        for batch in project["batches"]:
            for person in batch["people"]:
                if person["name"] not in seen:
                    seen.add(person["name"])
                    names.append(person["name"])
    write_summary(summary, anchors, names)

    check = wb.create_sheet("核对")
    prepare_sheet(check)
    check.sheet_properties.tabColor = "7F7F7F"
    check.sheet_view.showGridLines = True
    put(check, 1, 1, "计算核对", font=Font(name="等线", size=14, bold=True), fill=WHITE, border=Border())
    note = "金额四舍五入到分。进度奖比例：≤-10% 为 200%，-10%至-5% 为 170%，-5%至-3% 为 150%，-3%至0（含刚好0）为 130%，0至20% 为 100%，20%至50% 为 80%，≥50% 为 50%。"
    put(check, 2, 1, note, font=F_SONG9, fill=WHITE, border=Border(), align="left", wrap=True)
    check.row_dimensions[2].height = 32
    put(check, 4, 1, "需要人工确认", font=F_SONG9B, fill=GRAY)
    if warnings:
        for index, message in enumerate(warnings, 5):
            put(check, index, 1, message, font=F_SONG9, fill=WARN, align="left")
    else:
        put(check, 5, 1, "没有需要确认的问题", font=F_SONG9, fill=WHITE, align="left", border=Border())
    check.column_dimensions["A"].width = 110
    check.page_setup.orientation = "portrait"
    check.page_setup.fitToWidth = 1
    wb.save(path)


def self_test():
    assert progress_factor(D("-0.2")) == D("2")
    assert progress_factor(D("-0.1")) == D("2")
    assert progress_factor(D("-0.08")) == D("1.7")
    assert progress_factor(D("-0.04")) == D("1.5")
    assert progress_factor(D("0")) == D("1.3")
    assert progress_factor(D("0.1")) == D("1")
    assert progress_factor(D("0.3")) == D("0.8")
    assert progress_factor(D("0.5")) == D("0.5")
    rates = {"3000L搪瓷釜": {"投料": D("0.05"), "升温": D("0.03"), "浓缩": D("0.1")}}
    projects = [{"sheet": "P-1-06", "project": "P-1-06", "batches": [{
        "batch_id": "P-1-06-01", "error": "", "ops": [
            {"seq": "1、加料", "raw_name": "1、加料", "name": "投料", "standard": 2, "equipment": "3000L搪瓷釜", "actual": 1, "people": ["张三"]},
            {"seq": "2、升温", "raw_name": "2、升温", "name": "升温", "standard": 4, "equipment": "3000L搪瓷釜", "actual": 2, "people": ["张三"]},
            {"seq": "3、浓缩", "raw_name": "3、浓缩", "name": "浓缩", "standard": 8, "equipment": "3000L搪瓷釜", "actual": 8, "people": ["李四"]},
        ]}] }]
    results, warnings = calculate(projects, rates, D("150"))
    batch = results[0]["batches"][0]
    assert batch["ratio"] == D("-3") / D("14")
    assert batch["factor"] == D("2")
    bonus = {person["name"]: person["bonus"] for person in batch["people"]}
    assert bonus["张三"] == money((D("0.05") + D("0.03")) * D("150") * 2)
    assert bonus["李四"] == money(D("0.1") * D("150") * 2)
    assert not warnings
    print("self-test ok", bonus)


def main():
    parser = argparse.ArgumentParser()
    here = Path(__file__).parent
    parser.add_argument("--input", type=Path, default=here / "单元操作时间.xlsx")
    parser.add_argument("--template", type=Path, default=here / "月--操作工2026版.xlsx")
    parser.add_argument("--output", type=Path, default=here / "月--操作工2026版_计算结果.xlsx")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    rates, _, price = load_rates(args.template)
    projects = parse_input(args.input)
    results, warnings = calculate(projects, rates, price)
    write_output(args.output, results, warnings, rates, price)
    batches = sum(len(project["batches"]) for project in results)
    print(f"已生成 {args.output.name}：{len(results)} 个步骤，{batches} 个批次，需确认 {len(warnings)} 条")


if __name__ == "__main__":
    main()
