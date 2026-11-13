"""生成一份可计算的单元操作时间样例，并写出对应的奖金结果。

固定随机种子，重复运行得到同一份数据。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from build_bonus import calculate, load_rates, parse_input, write_output  # noqa: E402

SEED = 20261113

TITLE_FONT = Font(name="等线", size=16, bold=True, color="000000")
HEADER_FONT = Font(name="等线", size=11, color="000000")
HEADER_FONT_CAL = Font(name="Calibri", size=11, color="000000")
CELL_FONT = Font(name="等线", size=12, color="000000")
THIN = Border(
    left=Side(style="thin", color="000000"),
    right=Side(style="thin", color="000000"),
    top=Side(style="thin", color="000000"),
    bottom=Side(style="thin", color="000000"),
)
WIDTHS = {"seq": 14, "standard": 12, "equipment": 18, "start": 14, "end": 16, "actual": 18, "people": 16}

LAYOUTS = (
    ["seq", "standard", "equipment", "start", "end", "actual", "people"],
    ["seq", "equipment", "standard", "start", "end", "actual", "people"],
)
LABELS = {
    "seq": "操作\n序号",
    "standard": "标准\n时间",
    "equipment": "设备规格",
    "start": "开始时间\n（月/日）",
    "end": "      结束时间\n      （月/日）        ",
    "actual": "操作总时长（h）\n（结束时间减开始时间）",
    "people": "操作人员\n(涉及计件)",
}
PEOPLE = ["周明", "孙丽", "吴刚", "郑洁", "冯涛", "韩雪"]
EQUIPMENT_POOL = ["3000L搪瓷釜", "5000L搪瓷釜", "2000L搪瓷釜", "1000L高压釜", "3000L白钢低温釜", "2000L白钢釜"]
PROJECTS = [
    ("DH2601-01", ["06", "07"]),
    ("DH2602-01", ["03", "05"]),
]


def pick_operations(table: dict, rng: random.Random, count: int) -> list[str]:
    available = [name for name, coef in table.items() if coef > 0]
    return rng.sample(available, count)


def build_steps(rates: dict, rng: random.Random) -> list[dict]:
    steps = []
    for project, step_numbers in PROJECTS:
        for step_no in step_numbers:
            equipment = rng.choice(EQUIPMENT_POOL)
            operations = pick_operations(rates[equipment], rng, 6)
            batch_count = rng.randint(2, 3)
            batches = []
            for batch_no in range(1, batch_count + 1):
                multiplier = rng.choice([0.82, 0.94, 0.98, 1.12, 1.28, 1.55])
                rows = []
                day = rng.randint(2, 20)
                for index, name in enumerate(operations, 1):
                    standard = rng.choice([1, 1.5, 2, 2, 3, 4, 5, 6])
                    actual = round(standard * multiplier + rng.choice([-0.2, 0, 0.2]), 1)
                    actual = max(actual, 0.5)
                    crew = rng.sample(PEOPLE, 2 if rng.random() < 0.35 else 1)
                    rows.append({
                        "seq": f"{index}、{name}",
                        "standard": standard,
                        "equipment": equipment,
                        "start": f"11/{day:02d}",
                        "end": f"11/{day:02d}",
                        "actual": actual,
                        "people": "、".join(crew),
                    })
                    day = min(day + 1, 28)
                batches.append({
                    "batch_id": f"{project}-{step_no}-{batch_no:02d}",
                    "rows": rows,
                })
            steps.append({
                "sheet": f"{project}-{step_no}",
                "batches": batches,
            })
    return steps


def write_input(path: Path, steps: list[dict]) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    data_align = Alignment(horizontal="center", vertical="center")
    for step in steps:
        ws = wb.create_sheet(step["sheet"])
        ws.row_dimensions[1].height = 35.25
        ws.row_dimensions[2].height = 48
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
        ws.print_title_rows = "1:2"
        ws.oddFooter.right.text = "第 &P 页"
        ws.oddFooter.left.text = step["sheet"]
        for batch_index, batch in enumerate(step["batches"]):
            layout = LAYOUTS[batch_index % 2]
            start_col = 1 + batch_index * len(layout)
            end_col = start_col + len(layout) - 1
            ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
            title = ws.cell(1, start_col, batch["batch_id"])
            title.font = TITLE_FONT
            title.alignment = Alignment(horizontal="center", vertical="center")
            for offset, key in enumerate(layout):
                cell = ws.cell(2, start_col + offset, LABELS[key])
                cell.font = HEADER_FONT if key in ("seq", "standard", "equipment") else HEADER_FONT_CAL
                cell.alignment = center
                cell.border = THIN
                ws.column_dimensions[get_column_letter(start_col + offset)].width = WIDTHS[key]
            for row_index, record in enumerate(batch["rows"], 3):
                ws.row_dimensions[row_index].height = 21.75
                for offset, key in enumerate(layout):
                    cell = ws.cell(row_index, start_col + offset, record[key])
                    cell.font = CELL_FONT
                    cell.border = THIN
                    cell.alignment = data_align
                    if key in ("standard", "actual"):
                        cell.number_format = '0.0"h"'
    wb.save(path)


def main() -> None:
    rng = random.Random(SEED)
    template = ROOT / "月--操作工2026版.xlsx"
    rates, _, price = load_rates(template)
    steps = build_steps(rates, rng)
    input_path = HERE / "单元操作时间.xlsx"
    output_path = HERE / "月--操作工2026版_计算结果.xlsx"
    write_input(input_path, steps)
    projects = parse_input(input_path)
    results, warnings = calculate(projects, rates, price)
    write_output(output_path, results, warnings, rates, price)
    batches = [batch for project in results for batch in project["batches"]]
    names = sorted({person["name"] for batch in batches for person in batch["people"]})
    print(f"input {input_path.name}")
    print(f"output {output_path.name}")
    print(f"steps {len(results)} batches {len(batches)} people {len(names)} warnings {len(warnings)}")
    for project in results:
        for batch in project["batches"]:
            total = sum(person["bonus"] for person in batch["people"])
            print(
                f"{batch['batch_id']}  ops={len(batch['ops'])}  "
                f"std={batch['standard_sum']}  act={batch['actual_sum']}  "
                f"ratio={batch['ratio']:.2%}  factor={batch['factor']}  bonus={total}"
            )
    if warnings:
        print("WARNINGS")
        for message in warnings:
            print(message)


if __name__ == "__main__":
    main()
