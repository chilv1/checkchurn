# -*- coding: utf-8 -*-
"""Sinh workbook Excel KPI + dữ liệu phân loại từ aggregates.json & calls_classified.csv."""
import json, csv
import xlsxwriter

A = json.load(open("output/aggregates.json", encoding="utf-8"))
rows = list(csv.DictReader(open("output/calls_classified.csv", encoding="utf-8-sig")))

wb = xlsxwriter.Workbook("output/dashboard_churn_bitel.xlsx", {"nan_inf_to_errors": True})

# ---------- formats ----------
INK = "#0F172A"; AMBER = "#FDC700"; DARK = "#1F2937"; SLATE = "#475569"; GRAY = "#F1F5F9"
RED = "#E11D48"; ORG = "#EA580C"; GRN = "#059669"; BLU = "#2563EB"

f_title = wb.add_format({"bold": True, "font_size": 18, "font_color": INK})
f_sub   = wb.add_format({"font_size": 10, "font_color": SLATE, "italic": True})
f_sec   = wb.add_format({"bold": True, "font_size": 12, "font_color": "#B45309",
                         "bottom": 2, "border_color": AMBER})
f_hdr   = wb.add_format({"bold": True, "font_color": "white", "bg_color": DARK,
                         "align": "center", "valign": "vcenter", "border": 1, "border_color": "#334155",
                         "text_wrap": True})
f_hdr_l = wb.add_format({"bold": True, "font_color": "white", "bg_color": DARK,
                         "align": "left", "valign": "vcenter", "border": 1, "border_color": "#334155"})
f_cell  = wb.add_format({"border": 1, "border_color": "#E2E8F0", "valign": "vcenter"})
f_cell_c= wb.add_format({"border": 1, "border_color": "#E2E8F0", "align": "center"})
f_num   = wb.add_format({"border": 1, "border_color": "#E2E8F0", "num_format": "#,##0", "align": "right"})
f_pct   = wb.add_format({"border": 1, "border_color": "#E2E8F0", "num_format": "0.0%", "align": "right"})
f_pct1  = wb.add_format({"border": 1, "border_color": "#E2E8F0", "num_format": "0.0", "align": "right"})
f_es    = wb.add_format({"italic": True, "font_color": "#94A3B8", "border": 1, "border_color": "#E2E8F0"})
f_kpi_l = wb.add_format({"font_size": 10, "font_color": SLATE, "bold": True})
f_kpi_es= wb.add_format({"font_size": 9, "font_color": "#94A3B8", "italic": True})
f_note  = wb.add_format({"font_size": 9, "font_color": SLATE, "italic": True, "text_wrap": True, "valign": "top"})

def kpi_val_fmt(color):
    return wb.add_format({"bold": True, "font_size": 22, "font_color": color})

# =====================================================================
# SHEET 1 — TỔNG QUAN / RESUMEN
# =====================================================================
s = wb.add_worksheet("Tổng quan")
s.hide_gridlines(2); s.set_column("A:A", 2); s.set_column("B:I", 17)
s.merge_range("B2:I2", "BITEL PERÚ · Dashboard Khiếu nại Call Center", f_title)
s.merge_range("B3:I3", f"Análisis de {A['total_calls']:,} llamadas · Kỳ {A['months_vn'][0]}–{A['months_vn'][-1]} · Tạo lúc {A['generated_at']}", f_sub)

cards = [
    ("Tổng cuộc gọi", "Total llamadas", A["total_calls"], "#,##0", INK),
    ("Tổng giờ đàm thoại", "Horas de conversación", A["total_talk_hours"], "#,##0.0", INK),
    ("AHT (phút)", "Tiempo medio de atención", A["aht_min"], "0.00", BLU),
    ("Ý định rời mạng", "Intención de churn", A["churn_pct"]/100, "0.0%", RED),
    ("Nguy cơ cần giữ chân", "Riesgo de retención", A["retention_pct"]/100, "0.0%", ORG),
    ("Cảm xúc tiêu cực", "Sentimiento negativo", A["neg_pct"]/100, "0.0%", "#7C3AED"),
    ("Nhắc đối thủ", "Menciona competencia", A["comp_pct"]/100, "0.0%", INK),
    ("Tin cậy STT (TB)", "Confianza STT", A["avg_conf"], "0.00", GRN),
]
r0 = 4
for i, (vn, es, val, nf, col) in enumerate(cards):
    rr = r0 + (i // 4) * 4
    cc = 1 + (i % 4) * 2
    s.merge_range(rr, cc, rr, cc + 1, vn, f_kpi_l)
    s.merge_range(rr + 1, cc, rr + 1, cc + 1, es, f_kpi_es)
    vfmt = wb.add_format({"bold": True, "font_size": 20, "font_color": col, "num_format": nf})
    s.merge_range(rr + 2, cc, rr + 2, cc + 1, val, vfmt)
s.write(r0 + 8, 1, "Phát hiện chính / Hallazgos clave", f_sec)
top1, top2 = A["primary_dist"][0], A["primary_dist"][1]
ch = A["trend"]["churn_pct"]
top_drv = sorted([d for d in A["churn_by_cat"] if d["tot"] >= 40 and d["key"] not in ("cancel_churn", "general")],
                 key=lambda x: -x["pct"])[0]
comp = A["competitor_dist"][0]
findings = [
    f"• Hai lý do gọi lớn nhất: {top1['vn']} ({top1['pct']}%) và {top2['vn']} ({top2['pct']}%) — chiếm {round(top1['pct']+top2['pct'],1)}% tổng cuộc gọi.",
    f"• Tỷ lệ ý định rời mạng TĂNG từ {ch[0]}% ({A['months_vn'][0]}) lên {ch[-1]}% ({A['months_vn'][-1]}) — cần cảnh báo sớm.",
    f"• Lý do gọi gắn churn cao nhất (ngoài nhóm hủy): {top_drv['vn']} = {top_drv['pct']}% có ý định rời mạng.",
    f"• Đối thủ bị nhắc nhiều nhất: {comp['name']} ({comp['n']} lượt).",
    f"• Khó xử lý nhất (AHT dài nhất): {A['aht_by_cat'][0]['vn']} ~{A['aht_by_cat'][0]['aht_min']} phút/cuộc.",
]
for i, t in enumerate(findings):
    s.merge_range(r0 + 9 + i, 1, r0 + 9 + i, 8, t, f_note)

# =====================================================================
# SHEET 2 — LÝ DO GỌI / MOTIVOS
# =====================================================================
s2 = wb.add_worksheet("Lý do gọi")
s2.hide_gridlines(2); s2.set_column("A:A", 30); s2.set_column("B:B", 30); s2.set_column("C:E", 14)
s2.write("A1", "Phân bố lý do gọi (nhãn chính) / Motivos de llamada", f_sec)
hdr = ["Lý do gọi (VN)", "Motivo (ES)", "Số cuộc", "Tỷ lệ %"]
for c, h in enumerate(hdr): s2.write(2, c, h, f_hdr if c >= 2 else f_hdr_l)
r = 3
for d in A["primary_dist"]:
    s2.write(r, 0, d["vn"], f_cell); s2.write(r, 1, d["es"], f_es)
    s2.write(r, 2, d["n"], f_num); s2.write(r, 3, d["pct"]/100, f_pct); r += 1
data_end = r - 1
chart = wb.add_chart({"type": "bar"})
chart.add_series({
    "name": "Số cuộc gọi", "categories": ["Lý do gọi", 3, 0, data_end, 0],
    "values": ["Lý do gọi", 3, 2, data_end, 2],
    "fill": {"color": AMBER}, "data_labels": {"value": True}})
chart.set_title({"name": "Lý do khách hàng gọi / Motivos de contacto"})
chart.set_legend({"none": True}); chart.set_size({"width": 560, "height": 360})
chart.set_y_axis({"reverse": True})
s2.insert_chart("F2", chart)

# multi-label table
mr = r + 2
s2.write(mr - 1, 0, "Đa nhãn: chủ đề xuất hiện trong cuộc gọi / Temas (multi-etiqueta)", f_sec)
for c, h in enumerate(["Chủ đề (VN)", "Tema (ES)", "Số cuộc", "% tổng"]):
    s2.write(mr, c, h, f_hdr if c >= 2 else f_hdr_l)
r = mr + 1
for d in A["topic_dist"]:
    if d["key"] == "general": continue
    s2.write(r, 0, d["vn"], f_cell); s2.write(r, 1, d["es"], f_es)
    s2.write(r, 2, d["n"], f_num); s2.write(r, 3, d["pct"]/100, f_pct); r += 1

# =====================================================================
# SHEET 3 — XU HƯỚNG THÁNG / TENDENCIAS
# =====================================================================
s3 = wb.add_worksheet("Xu hướng tháng")
s3.hide_gridlines(2); s3.set_column("A:A", 14); s3.set_column("B:F", 16)
s3.write("A1", "Xu hướng theo tháng / Tendencias mensuales", f_sec)
hdr = ["Tháng / Mes", "Số cuộc gọi", "Ý định rời mạng (cuộc)", "% Churn", "Cảm xúc tiêu cực %", "AHT (phút)"]
for c, h in enumerate(hdr): s3.write(2, c, h, f_hdr if c else f_hdr_l)
tr = A["trend"]; r = 3
for i, mv in enumerate(tr["months_vn"]):
    s3.write(r, 0, mv, f_cell); s3.write(r, 1, tr["volume"][i], f_num)
    s3.write(r, 2, tr["churn"][i], f_num); s3.write(r, 3, tr["churn_pct"][i]/100, f_pct)
    s3.write(r, 4, tr["neg_pct"][i]/100, f_pct); s3.write(r, 5, tr["aht_min"][i], f_pct1); r += 1
de = r - 1
# combo: column volume + line churn%
c_col = wb.add_chart({"type": "column"})
c_col.add_series({"name": "Số cuộc gọi", "categories": ["Xu hướng tháng", 3, 0, de, 0],
                  "values": ["Xu hướng tháng", 3, 1, de, 1], "fill": {"color": "#CBD5E1"}})
c_line = wb.add_chart({"type": "line"})
c_line.add_series({"name": "% Churn", "categories": ["Xu hướng tháng", 3, 0, de, 0],
                   "values": ["Xu hướng tháng", 3, 3, de, 3], "line": {"color": RED, "width": 2.5},
                   "marker": {"type": "circle", "size": 6}, "y2_axis": True,
                   "data_labels": {"value": True, "num_format": "0.0%"}})
c_col.combine(c_line)
c_col.set_title({"name": "Sản lượng & % ý định rời mạng theo tháng"})
c_col.set_y_axis({"name": "Số cuộc gọi"})
c_col.set_y2_axis({"name": "% Churn", "num_format": "0%"})
c_col.set_size({"width": 640, "height": 360})
s3.insert_chart("H2", c_col)

# =====================================================================
# SHEET 4 — CHURN & ĐỐI THỦ
# =====================================================================
s4 = wb.add_worksheet("Churn & Đối thủ")
s4.hide_gridlines(2); s4.set_column("A:A", 30); s4.set_column("B:D", 14)
s4.write("A1", "Tỷ lệ churn theo lý do gọi / Churn por motivo", f_sec)
for c, h in enumerate(["Lý do gọi (VN)", "Có churn", "Tổng cuộc", "% Churn"]):
    s4.write(2, c, h, f_hdr if c else f_hdr_l)
r = 3
ch_cat = sorted([d for d in A["churn_by_cat"] if d["tot"] >= 40 and d["key"] not in ("cancel_churn", "general")],
                key=lambda x: -x["pct"])
for d in ch_cat:
    s4.write(r, 0, d["vn"], f_cell); s4.write(r, 1, d["n"], f_num)
    s4.write(r, 2, d["tot"], f_num); s4.write(r, 3, d["pct"]/100, f_pct); r += 1
de = r - 1
cc = wb.add_chart({"type": "bar"})
cc.add_series({"name": "% Churn", "categories": ["Churn & Đối thủ", 3, 0, de, 0],
               "values": ["Churn & Đối thủ", 3, 3, de, 3], "fill": {"color": RED},
               "data_labels": {"value": True, "num_format": "0.0%"}})
cc.set_title({"name": "Lý do gọi nào dẫn tới rời mạng nhiều nhất?"})
cc.set_legend({"none": True}); cc.set_y_axis({"reverse": True})
cc.set_x_axis({"num_format": "0%"}); cc.set_size({"width": 520, "height": 320})
s4.insert_chart("F2", cc)

# competitors
cr = r + 2
s4.write(cr - 1, 0, "Đối thủ được nhắc / Competidores mencionados", f_sec)
for c, h in enumerate(["Đối thủ", "Lượt nhắc"]):
    s4.write(cr, c, h, f_hdr if c else f_hdr_l)
r = cr + 1; cs = r
for d in A["competitor_dist"]:
    s4.write(r, 0, d["name"], f_cell); s4.write(r, 1, d["n"], f_num); r += 1
ce = r - 1
pie = wb.add_chart({"type": "pie"})
pie.add_series({"name": "Đối thủ", "categories": ["Churn & Đối thủ", cs, 0, ce, 0],
                "values": ["Churn & Đối thủ", cs, 1, ce, 1],
                "data_labels": {"percentage": True, "category": True},
                "points": [{"fill": {"color": RED}}, {"fill": {"color": BLU}}, {"fill": {"color": GRN}}]})
pie.set_title({"name": "Tỷ trọng nhắc đối thủ"}); pie.set_size({"width": 420, "height": 300})
s4.insert_chart("F20", pie)

# =====================================================================
# SHEET 5 — AHT & VẬN HÀNH
# =====================================================================
s5 = wb.add_worksheet("AHT & Vận hành")
s5.hide_gridlines(2); s5.set_column("A:A", 30); s5.set_column("B:C", 16)
s5.write("A1", "AHT theo lý do gọi / Tiempo medio por motivo (phút)", f_sec)
for c, h in enumerate(["Lý do gọi (VN)", "AHT (phút)", "Số cuộc"]):
    s5.write(2, c, h, f_hdr if c else f_hdr_l)
r = 3
for d in [x for x in A["aht_by_cat"] if x["n"] >= 20]:
    s5.write(r, 0, d["vn"], f_cell); s5.write(r, 1, d["aht_min"], f_pct1); s5.write(r, 2, d["n"], f_num); r += 1
de = r - 1
ac = wb.add_chart({"type": "bar"})
ac.add_series({"name": "AHT (phút)", "categories": ["AHT & Vận hành", 3, 0, de, 0],
               "values": ["AHT & Vận hành", 3, 1, de, 1], "fill": {"color": BLU},
               "data_labels": {"value": True}})
ac.set_title({"name": "AHT theo lý do gọi (phút)"}); ac.set_legend({"none": True})
ac.set_y_axis({"reverse": True}); ac.set_size({"width": 520, "height": 320})
s5.insert_chart("E2", ac)

# duration + confidence dist
dr = r + 2
s5.write(dr - 1, 0, "Phân bố thời lượng / Duración", f_sec)
for c, h in enumerate(["Khoảng", "Số cuộc"]): s5.write(dr, c, h, f_hdr if c else f_hdr_l)
r = dr + 1
for d in A["dur_dist"]:
    s5.write(r, 0, d["bucket"], f_cell); s5.write(r, 1, d["n"], f_num); r += 1
cfr = r + 1
s5.write(cfr - 1, 0, "Chất lượng STT / Confianza", f_sec)
for c, h in enumerate(["Mức", "Số cuộc"]): s5.write(cfr, c, h, f_hdr if c else f_hdr_l)
r = cfr + 1
for d in sorted(A["conf_dist"], key=lambda x: -x["n"]):
    s5.write(r, 0, d["band"], f_cell); s5.write(r, 1, d["n"], f_num); r += 1

# =====================================================================
# SHEET 6 — DỮ LIỆU CUỘC GỌI / DATOS POR LLAMADA
# =====================================================================
s6 = wb.add_worksheet("Dữ liệu cuộc gọi")
s6.freeze_panes(1, 0)
# bilingual-ish header mapping
COLMAP = [
    ("call_id", "call_id"), ("phone", "SĐT / teléfono"), ("month_vn", "Tháng"),
    ("duration_min", "Thời lượng (phút)"), ("duration_bucket", "Khoảng thời lượng"),
    ("confidence", "Tin cậy STT"), ("conf_band", "Mức tin cậy"),
    ("primary_vn", "Lý do chính (VN)"), ("primary_es", "Motivo (ES)"), ("tags", "Nhãn phụ"),
    ("churn_intent", "Ý định rời mạng"), ("retention_risk", "Nguy cơ giữ chân"),
    ("neg_sentiment", "Cảm xúc tiêu cực"), ("competitor", "Nhắc đối thủ"), ("competitors", "Đối thủ"),
    ("downgrade", "Đòi hạ gói"), ("loss_theft", "Mất/Trộm"), ("repeat_call", "Gọi lại"),
    ("csat_offered", "Mời CSAT"), ("n_chars", "Số ký tự"),
]
keys = [k for k, _ in COLMAP]
for c, (_, h) in enumerate(COLMAP):
    s6.write(0, c, h, f_hdr_l)
intcols = {"churn_intent","retention_risk","neg_sentiment","competitor","downgrade","loss_theft","repeat_call","csat_offered","n_chars"}
for ri, row in enumerate(rows, start=1):
    for c, k in enumerate(keys):
        v = row.get(k, "")
        if k in ("duration_min", "confidence"):
            try: s6.write_number(ri, c, float(v))
            except: s6.write(ri, c, v)
        elif k in intcols:
            try: s6.write_number(ri, c, int(v))
            except: s6.write(ri, c, v)
        else:
            s6.write(ri, c, v)
s6.autofilter(0, 0, len(rows), len(keys) - 1)
widths = [20, 12, 8, 13, 14, 10, 14, 22, 24, 18, 12, 12, 12, 10, 12, 9, 9, 8, 9, 9]
for c, w in enumerate(widths): s6.set_column(c, c, w)
# highlight churn rows
chfmt = wb.add_format({"bg_color": "#FFF1F2"})
s6.conditional_format(1, 10, len(rows), 10, {"type": "cell", "criteria": "==", "value": 1,
    "format": wb.add_format({"bg_color": "#FECDD3", "bold": True})})

wb.close()
print("→ output/dashboard_churn_bitel.xlsx | 6 sheet | %d dòng dữ liệu" % len(rows))
