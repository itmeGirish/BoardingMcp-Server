import sys
sys.stdout.reconfigure(encoding="utf-8")
import openpyxl
wb = openpyxl.load_workbook("docs/Draft_test.xlsx")
ws = wb.active
for r in range(2, 12):
    val = ws.cell(row=r, column=7).value or ""
    if val.startswith("["):
        print(f"Row {r}: ERROR - {val[:80]}")
    else:
        print(f"Row {r}: {len(val)} chars | {len(val.split())} words")
