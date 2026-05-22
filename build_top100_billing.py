# -*- coding: utf-8 -*-
"""Top 100 thuê bao nhóm HÓA ĐƠN & THANH TOÁN có nguy cơ rời mạng cao nhất.
Điểm rủi ro có trọng số theo sức dự báo (lift) đã đo + trích câu bằng chứng."""
import json, glob, re, csv, unicodedata
import xlsxwriter

def strip_accents(s): return "".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
def norm(s): return strip_accents((s or "").lower())

BOILER=[norm(x) for x in ["asesores se encuentran ocupados","en breve lo atenderemos","horario de atencion de esta central","lunes a domingo","app mibitel","con la app mibitel","descarga e ingresa","sin salir de tu casa","estes donde estes","este donde estes","canal exclusivo de migraciones","su opinion es importante","invitamos a responder","breve encuesta","calificar la atencion","area de migraciones y cancelaciones","podras solicitar y ejecutar tramites","la linea debe de encontrarse activa","quiere realizar el proceso de migracion","reintegro del costo del equipo","no se mantendra los saldos","cambio de plan no tiene costo","bienvenido a bitel","manejo de informacion"]]
def kept(raw):
    out=[]
    for s in re.split(r'(?<=[.?!])\s+', raw or ""):
        if any(b in norm(s) for b in BOILER): continue
        if s.strip(): out.append((s.strip(), norm(s)))
    return out

HARD=re.compile(r"(portabilidad|portarme|me porto|\bportar\b|irme a (otro|claro|movistar|entel)|cambiarme de (operador|compania|empresa)|otro operador|otra operadora)")
CANCEL=re.compile(r"(dar(me|se)? de baja|\bde baja\b|cancelar (mi |la |el )?(linea|servicio|plan|cuenta|contrato)|anular (mi |la |el )?(linea|servicio))")
LOSS=re.compile(r"(perdida|\brobo\b|me robaron|se me perdio|extravi|hurto|equipo robado)")
NEG=re.compile(r"(reclam|\bqueja|molest|malestar|indignad|fastidi|incomod|pesimo|mal servicio|terrible|estafa|engan|cobro indebido|cobrado de mas|abuso|fraude)")
BILL=re.compile(r"(recibo|factura|deuda|no me funciona el pago|no se refleja|sigo con deuda|me cobr|cobro|monto|vencid|pago)")
COMP_CTX=re.compile(r"(de claro\b|a claro\b|con claro\b|tengo claro\b|estoy (con|en) claro|claro me (ofrec|da|dio)|me ofrece claro|portarme a claro|irme a claro)")

# transcripts
TX={}
for f in glob.glob("stt_out/*.json"):
    try: d=json.load(open(f,encoding="utf-8"))
    except: continue
    TX[d.get("call_id")]=d.get("transcript",{}).get("text","")

rows=[r for r in csv.DictReader(open("output/calls_classified.csv",encoding="utf-8-sig")) if r["primary"]=="billing"]
def b(r,k): return r[k]=="1"

# --- Trọng số điểm (neo theo lift: đối thủ x2,3 > hạ gói x1,7 > gọi lại x1,4 > tiêu cực x1,3) ---
W={"churn_intent":45,"competitor":25,"downgrade":18,"repeat_call":14,"neg_sentiment":12}

def evidence(cid):
    """Câu bằng chứng mạnh nhất + đối thủ."""
    sents=kept(TX.get(cid,""));
    full=norm(" ".join(s for _,s in sents))
    loss=bool(LOSS.search(full))
    # ưu tiên câu có tín hiệu rời mạng
    for disp,sn in sents:
        if HARD.search(sn) or (CANCEL.search(sn) and not loss):
            return clip(disp)
    for disp,sn in sents:
        if COMP_CTX.search(sn) or re.search(r"\b(movistar|entel)\b",sn):
            return clip(disp)
    for disp,sn in sents:
        if NEG.search(sn): return clip(disp)
    for disp,sn in sents:
        if BILL.search(sn): return clip(disp)
    return clip(sents[0][0]) if sents else ""

def clip(s, n=220):
    s=re.sub(r"\s+"," ",s).strip()
    return s if len(s)<=n else s[:n]+"…"

def which_comp(cid):
    cn=norm(" ".join(s for _,s in kept(TX.get(cid,""))))
    names=[]
    if COMP_CTX.search(cn): names.append("Claro")
    if re.search(r"\bmovistar\b",cn): names.append("Movistar")
    if re.search(r"\bentel\b",cn): names.append("Entel")
    return "/".join(dict.fromkeys(names)) if names else ""

scored=[]
for r in rows:
    s=sum(W[k] for k in W if b(r,k))
    # cộng nhẹ theo thời lượng (cuộc dài = giằng co), tối đa +6
    s+= min(float(r["duration_min"]),20)*0.3
    s=round(s,1)
    scored.append((s,r))
scored.sort(key=lambda x:(-x[0], -float(x[1]["duration_min"])))

def level(s):
    if s>=70: return "Rất cao"
    if s>=45: return "Cao"
    if s>=20: return "Trung bình"
    return "Thấp"

top=scored[:100]
# bảng đầy đủ (tất cả 962 có rủi ro) để tham khảo
allrisk=[(s,r) for s,r in scored if s>=20]

# ============== EXCEL ==============
wb=xlsxwriter.Workbook("output/Top100_HoaDon_NguyCoRoiMang.xlsx")
INK="#0F172A";DARK="#1F2937";RED="#E11D48";ORG="#EA580C";AMB="#FDC700";GRN="#059669";GRAY="#F1F5F9"
f_title=wb.add_format({"bold":True,"font_size":16,"font_color":INK})
f_sub=wb.add_format({"font_size":10,"italic":True,"font_color":"#475569"})
f_hdr=wb.add_format({"bold":True,"font_color":"white","bg_color":DARK,"align":"center","valign":"vcenter","border":1,"text_wrap":True})
f_c=wb.add_format({"border":1,"border_color":"#E2E8F0","valign":"vcenter"})
f_cc=wb.add_format({"border":1,"border_color":"#E2E8F0","align":"center","valign":"vcenter"})
f_num=wb.add_format({"border":1,"border_color":"#E2E8F0","align":"center","num_format":"0.0","valign":"vcenter"})
f_ev=wb.add_format({"border":1,"border_color":"#E2E8F0","valign":"vcenter","text_wrap":True,"font_size":9,"italic":True,"font_color":"#334155"})
f_phone=wb.add_format({"border":1,"border_color":"#E2E8F0","align":"center","bold":True,"valign":"vcenter"})
lv_fmt={"Rất cao":wb.add_format({"border":1,"bg_color":"#FECDD3","font_color":"#9F1239","bold":True,"align":"center","valign":"vcenter"}),
        "Cao":wb.add_format({"border":1,"bg_color":"#FED7AA","font_color":"#9A3412","bold":True,"align":"center","valign":"vcenter"}),
        "Trung bình":wb.add_format({"border":1,"bg_color":"#FEF3C7","font_color":"#92400E","align":"center","valign":"vcenter"}),
        "Thấp":wb.add_format({"border":1,"align":"center","valign":"vcenter"})}
chk=wb.add_format({"border":1,"align":"center","font_color":GRN,"bold":True,"valign":"vcenter"})
dash=wb.add_format({"border":1,"align":"center","font_color":"#CBD5E1","valign":"vcenter"})

def write_sheet(ws, data, title):
    ws.set_column("A:A",6); ws.set_column("B:B",13); ws.set_column("C:C",9); ws.set_column("D:D",11)
    ws.set_column("E:E",9); ws.set_column("F:F",10); ws.set_column("G:G",9); ws.set_column("H:H",12)
    ws.set_column("I:I",9); ws.set_column("J:J",8); ws.set_column("K:K",11); ws.set_column("L:L",58); ws.set_column("M:M",22)
    ws.merge_range("A1:M1", title, f_title)
    ws.merge_range("A2:M2", "Điểm rủi ro = 45·(ý định rời) + 25·(nhắc đối thủ) + 18·(đòi hạ gói) + 14·(gọi lại) + 12·(cảm xúc tiêu cực) + thưởng thời lượng. Trọng số neo theo sức dự báo (lift) đã đo.", f_sub)
    hdr=["Hạng","Số thuê bao","Điểm","Mức rủi ro","Tháng","Thời lượng\n(phút)","Ý định\nrời?","Đối thủ","Đòi\nhạ gói?","Gọi\nlại?","Cảm xúc\ntiêu cực?","Bằng chứng (câu khách nói — tiếng TBN)","call_id (truy ngược ghi âm)"]
    for c,h in enumerate(hdr): ws.write(3,c,h,f_hdr)
    ws.freeze_panes(4,0)
    rr=4
    for i,(sc,r) in enumerate(data,1):
        cid=r["call_id"]
        ws.write(rr,0,i,f_cc); ws.write(rr,1,r["phone"],f_phone)
        ws.write(rr,2,sc,f_num); ws.write(rr,3,level(sc),lv_fmt[level(sc)])
        ws.write(rr,4,r["month_vn"],f_cc); ws.write(rr,5,float(r["duration_min"]),f_num)
        ws.write(rr,6,"✓" if b(r,"churn_intent") else "—", chk if b(r,"churn_intent") else dash)
        ws.write(rr,7, which_comp(cid) or "—", f_cc if which_comp(cid) else dash)
        ws.write(rr,8,"✓" if b(r,"downgrade") else "—", chk if b(r,"downgrade") else dash)
        ws.write(rr,9,"✓" if b(r,"repeat_call") else "—", chk if b(r,"repeat_call") else dash)
        ws.write(rr,10,"✓" if b(r,"neg_sentiment") else "—", chk if b(r,"neg_sentiment") else dash)
        ws.write(rr,11,evidence(cid),f_ev); ws.write(rr,12,cid,f_cc)
        rr+=1
    ws.autofilter(3,0,rr-1,12)

write_sheet(wb.add_worksheet("Top 100 nguy cơ cao"), top,
            "TOP 100 THUÊ BAO HÓA ĐƠN & THANH TOÁN — NGUY CƠ RỜI MẠNG CAO NHẤT")
write_sheet(wb.add_worksheet("Tất cả (rủi ro ≥20)"), allrisk,
            f"DANH SÁCH ĐẦY ĐỦ — {len(allrisk)} thuê bao hóa đơn có điểm rủi ro ≥ 20")
wb.close()

# preview top 20 ra console
print(f"Nhóm Hóa đơn: {len(rows)} thuê bao | xếp hạng rủi ro | Top100 ngưỡng điểm: {top[-1][0]} → {top[0][0]}")
print(f"Phân bố mức trong Top100: ", end="")
from collections import Counter
lc=Counter(level(s) for s,_ in top); print(dict(lc))
print(f"→ output/Top100_HoaDon_NguyCoRoiMang.xlsx (2 sheet: Top100 + đầy đủ {len(allrisk)} số)\n")
print("="*100)
print(f"{'#':>3} {'Số thuê bao':<12} {'Điểm':>5} {'Mức':<9} {'Th.lượng':>8} {'Đối thủ':<10} Bằng chứng")
print("="*100)
for i,(sc,r) in enumerate(top[:20],1):
    print(f"{i:>3} {r['phone']:<12} {sc:>5} {level(sc):<9} {r['duration_min']:>7}' {(which_comp(r['call_id']) or '—'):<10} {clip(evidence(r['call_id']),60)}")
