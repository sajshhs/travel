"""Generate /tmp/import_fe_i115.xlsx for frontend UI testing (iteration 115)."""
import io
import sys

sys.path.insert(0, "/app/backend")
from openpyxl import load_workbook  # noqa: E402
from services.master_import import build_template  # noqa: E402

wb = load_workbook(io.BytesIO(build_template()))
c = wb["Pelanggan"]
c.append(["TEST_FE115 Pelanggan Satu", "081966600201", "fe115a@uji.local", "Korporat", "Kota FE X 115", "Jl. FE 1", "ui test"])
c.append(["TEST_FE115 Pelanggan Dua", "081966600202", "", "individual", "Bandung", "Jl. FE 2", ""])
c.append(["", "081966600203", "", "individual", "", "tanpa nama", ""])   # error
c.append(["TEST_FE115 Jenis Salah", "081966600204", "", "vip", "", "", ""])  # error
wb["Armada"].append(["TEST_FE115 Hiace", "F 2151 AA", "", "", 14, "tersedia", 2023, "Putih", "20/04/2027", "", 900, ""])
wb["Driver"].append(["TEST_FE115 Driver", "081966600205", "", "", "", 200000])
wb["Kota"].append(["Kota FE Y 115"])
wb["Mitra"].append(["TEST_FE115 Mitra", "Pak FE", "081966600206", "", "Solo", "", "active", ""])
wb["Add-on"].append(["TEST_FE115 Addon", 75000, "ya"])
wb.save("/tmp/import_fe_i115.xlsx")
print("written /tmp/import_fe_i115.xlsx")
