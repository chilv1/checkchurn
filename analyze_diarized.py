# -*- coding: utf-8 -*-
"""Phân tích lại SAU KHI tách người nói: phân loại lý do gọi + churn CHỈ trên lời KHÁCH,
loại bỏ 'portabilidad vào Bitel' (inbound, ngược với churn).
Tái dùng taxonomy & regex từ analyze_calls.py."""
import json, glob, os, re, csv
from collections import Counter, defaultdict
import diarize as DZ

# import bộ phân loại (chạy lại pipeline gốc 1 lần - idempotent)
import analyze_calls as AC

STT_DIR="stt_out"; OUT="output"

# churn OUTBOUND do KHÁCH nói (loại inbound-to-Bitel)
OUTBOUND = re.compile(r"(otro operador|otra operadora|irme a (otro|claro|movistar|entel)|cambiarme de (operador|compania|empresa)|me quiero ir a (otro|claro|movistar|entel))")
INBOUND  = re.compile(r"(a bitel|que (ya )?(ha|he|hemos|habia) (realizado|hecho)|recien (hice|hizo|hicieron)|cumplir? .{0,20}a[nñ]o.{0,20}portab|vine de|me pase a bitel|portarme a bitel|portar a bitel)")
PORTAB   = re.compile(r"(portabilidad|portarme|me porto|\bportar\b)")

def cust_churn(cn):
    if not cn.strip(): return False, ""
    if OUTBOUND.search(cn): return True, "đổi nhà mạng (outbound)"
    if AC.CANCEL_LINE_RX.search(cn) and not AC.LOSS_RX.search(cn): return True, "hủy/đóng line"
    if PORTAB.search(cn) and not INBOUND.search(cn): return True, "portabilidad (outbound)"
    return False, ""

# nạp dữ liệu phân loại cũ để so sánh
old={r["call_id"]:r for r in csv.DictReader(open(f"{OUT}/calls_classified.csv",encoding="utf-8-sig"))}

rows=[]
files=sorted(glob.glob(os.path.join(STT_DIR,"*.json")))
for f in files:
    try: d=json.load(open(f,encoding="utf-8"))
    except: continue
    cid=d.get("call_id",""); m=d.get("metadata",{}) or {}; t=d.get("transcript",{}) or {}
    raw=t.get("text") or ""
    turns=DZ.diarize(raw)
    cust=" ".join(x["text"] for x in turns if x["speaker"]=="CLIENTE")
    ase =" ".join(x["text"] for x in turns if x["speaker"]=="ASESOR")
    chars={"CLIENTE":len(cust),"ASESOR":len(ase),
           "IVR":sum(len(x["text"]) for x in turns if x["speaker"]=="IVR")}
    tot=sum(chars.values()) or 1
    # phân loại lý do gọi trên LỜI KHÁCH (đã chuẩn hóa, bỏ boilerplate)
    cust_cn,_=AC.clean_text(cust)
    prim,tags,_=AC.classify(cust_cn)
    churn_new,reason=cust_churn(cust_cn)
    o=old.get(cid,{})
    rows.append({
        "call_id":cid,"phone":m.get("customer_phone",""),"period":m.get("period",""),
        "month_vn":o.get("month_vn",""),
        "n_turns":len(turns),
        "cliente_chars":chars["CLIENTE"],"asesor_chars":chars["ASESOR"],"ivr_chars":chars["IVR"],
        "cliente_pct":round(100*chars["CLIENTE"]/tot,1),
        "primary_old":o.get("primary",""),"primary_old_vn":o.get("primary_vn",""),
        "primary_cust":prim,"primary_cust_vn":AC.LABELS[prim][0],
        "churn_old":int(o.get("churn_intent","0")),
        "churn_cust":int(churn_new),"churn_reason":reason,
        "neg_old":int(o.get("neg_sentiment","0")),
        "duration_min":o.get("duration_min",""),
        "cust_text":cust[:1500],
    })

# lưu CSV
os.makedirs(OUT,exist_ok=True)
with open(f"{OUT}/calls_diarized.csv","w",newline="",encoding="utf-8-sig") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

N=len(rows)
co=sum(r["churn_old"] for r in rows); cn=sum(r["churn_cust"] for r in rows)
empty_cust=sum(1 for r in rows if r["cliente_chars"]==0)
avg_cli=sum(r["cliente_pct"] for r in rows)/N
print(f"Đã tách & phân tích lại {N} cuộc → {OUT}/calls_diarized.csv")
print(f"\nTỶ TRỌNG LỜI NÓI (trung bình mỗi cuộc): Khách {avg_cli:.0f}% | còn lại Tư vấn viên+IVR")
print(f"Cuộc không trích được lời khách (toàn bộ bị hút sang turn khác): {empty_cust}")
print(f"\n=== CHURN: TRƯỚC vs SAU khi tách người nói ===")
print(f"  Churn cũ (mọi câu):           {co}  ({100*co/N:.1f}%)")
print(f"  Churn mới (chỉ lời khách,      {cn}  ({100*cn/N:.1f}%)")
print(f"            loại portab-vào-Bitel)")
print(f"  Chênh lệch: {co-cn} cuộc bị gỡ cờ ({100*(co-cn)/co:.0f}% so với cũ)")

# lý do gỡ cờ
removed=[r for r in rows if r["churn_old"]==1 and r["churn_cust"]==0]
added=[r for r in rows if r["churn_old"]==0 and r["churn_cust"]==1]
print(f"\n  Gỡ cờ (cũ=churn, mới=không): {len(removed)} | Thêm cờ (cũ=ko, mới=churn): {len(added)}")

# dịch chuyển phân bố lý do chính
print(f"\n=== LÝ DO CHÍNH: dịch chuyển khi chỉ xét lời khách (top khác biệt) ===")
old_pc=Counter(r["primary_old_vn"] for r in rows); new_pc=Counter(r["primary_cust_vn"] for r in rows)
allk=set(old_pc)|set(new_pc)
diffs=sorted(allk,key=lambda k:-abs(new_pc[k]-old_pc[k]))
for k in diffs[:6]:
    print(f"  {k:<32} cũ {old_pc[k]:4d} → mới {new_pc[k]:4d}  ({new_pc[k]-old_pc[k]:+d})")
