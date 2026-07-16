import pandas as pd

file = "database.xlsx"

xls = pd.ExcelFile(file)

print(xls.sheet_names)