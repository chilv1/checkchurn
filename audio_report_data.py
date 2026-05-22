# -*- coding: utf-8 -*-
"""Tính dữ liệu + biểu đồ cho báo cáo .docx nhóm audio (chiến dịch gọi ra thu cước)."""
import json, glob, re, csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
os.makedirs("output/charts", exist_ok=True)
def nkl(s): return (s or "").lower().translate(str.maketrans("áéíóúüñàèìòù","aeiouunaeiou"))

OBJ=[
 ("Không phải của tôi / người thân", r"(le puse (el plan|la linea) a|es de mi (hermana|hijo|esposa|esposo|mama|papa|hermano|cunad)|no es mi (numero|linea)|es otro numero|esa linea no es)"),
 ("Đã thanh toán rồi (tranh luận)", r"(ya (he )?(pague|cancele|pagado)|he pagado|se acaba de pagar|ya esta (pagado|cancelado)|hice el pago (ya|hace)|acabo de pagar|pague (doble|dos veces)|pago doble|ya cancele)"),
 ("Không trả được / xin khất", r"(no (he )?(puedo|podido) pagar|por motivos|por (mi )?salud|no tengo (para|como|dinero)|me olvide|todavia no|aun no he|la proxima semana|me esperan|me espera|cuando (pueda|cobre|tenga))"),
 ("Số tiền sai / cao bất thường", r"(monto que (no|yo no)|no pagaba|me sale (mas|el monto)|me estan subiendo|mas (caro|elevado)|subio|aumento|esta mal el monto|no es el monto|por que (tan|me cobran mas))"),
 ("Muốn đổi / giảm gói", r"(bajar (al|el|de) plan|cambiar (de |el )?plan|plan de \d+ (igual|soles)|plan mas (barato|economico)|reducir)"),
 ("Cam kết / hỏi cách trả", r"(voy a pagar|si (voy|lo) a (pagar|cancelar)|quiero (hacer el |hacer mi )?pago|como (pago|hago el pago)|donde (pago|puedo pagar)|hoy (mismo|dia)|manana (pago|cancelo)|este fin)"),
 ("Thắc mắc nợ / hóa đơn", r"(tengo una deuda|que deuda|de que (mes|monto)|cuanto (debo|es mi)|no me (llega|llego)|no entiendo (el|por)|sobre el tema de|queria consultar)"),
]
def classify(cn):
    for n,p in OBJ:
        if re.search(p,cn): return n
    return "Khác / xác nhận thông tin"

DRILL={
 "Đã thanh toán rồi (tranh luận)":[
   ("Đã trả nhưng line/dịch vụ chưa mở lại","Trả tối qua/30 phút trước, có biên lai, nhưng line vẫn bị khóa — chờ kích hoạt.",["CALL_07","CALL_11"]),
   ("Trả nhầm số / trả 2 lần → xin hoàn-bù","Trả trùng hoặc nhầm sang số người thân; muốn hoàn tiền hoặc cấn trừ tháng sau.",["CALL_13","CALL_18"]),
   ("Trả qua app bên thứ 3, chưa phản ánh / thiếu cashback","Trả qua B-Pay/Yape; hệ thống chưa ghi nhận hoặc thiếu hoàn tiền KM.",["CALL_02"]),
   ("Tranh luận phí trễ hạn / lãi","Trả trễ 1-2 ngày bị tính lãi ~10 soles, khách không đồng ý.",["CALL_10"]),
   ("Trả hộ thuê bao người thân + hỏi chu kỳ","Trả hộ line em/chị; hỏi chu kỳ cước & ngày phải trả.",["CALL_16"]),
   ("Giá tăng bất thường khi định trả","Định trả thì số tiền nhảy ~+10 soles dù không đổi gói.",["CALL_08"]),
 ],
 "Thắc mắc nợ / hóa đơn":[
   ("Xác minh tin nhắn KM/ưu đãi (Liga1, giảm 50%)","Nhận SMS/cuộc gọi báo 'Liga 1 miễn phí' hoặc 'giảm 50% 12 tháng'; không chắc thật hay mất phí.",["CALL_14","CALL_17"]),
   ("Nghi ngờ khoản nợ + bị dọa cắt","Bị gọi báo có nợ & dọa cắt dịch vụ, nhưng tin mình đã đóng đủ.",["CALL_03"]),
 ],
 "Khác / xác nhận thông tin":[
   ("Khuyến mãi không được áp / billing sai giá","Đăng ký KM 27 soles nhưng bị tính 39.90/79; hỏi cách trả & app.",["CALL_19"]),
   ("Hỏi số tiền/ngày để đi trả","Chưa nhận hóa đơn; hỏi số tiền & ngày thanh toán.",["CALL_05","CALL_20"]),
   ("Sự cố dịch vụ (mất internet)","Mua gói vài ngày, mất internet, tưởng line 'hết hạn'.",["CALL_04"]),
   ("Nhiễu / không liên quan","Audio lẫn tạp âm/nói chuyện ngoài lề (máy giặt…).",["CALL_15"]),
 ],
 "Số tiền sai / cao bất thường":[("Số tiền cao hơn thường lệ","Bình thường trả 39.90, nay bị tính cao hơn.",["CALL_01"])],
 "Không phải của tôi / người thân":[("Line/gói của người thân","Khách báo line/gói là của người thân, không phải của mình.",["CALL_06"])],
 "Không trả được / xin khất":[("Xin khất vì lý do cá nhân","Quá hạn vì lý do sức khỏe; xin gia hạn.",["CALL_09"])],
 "Muốn đổi / giảm gói":[("Hỏi hạ gói","Hỏi có thể chuyển xuống gói 40 soles không.",["CALL_12"])],
}
THEMES=[
 ("Phản ánh & xử lý thanh toán","Trả rồi chưa cập nhật/chưa mở line, trả trùng-nhầm số, app bên thứ 3 trễ. Nhóm LỚN NHẤT — gốc rễ khiến chiến dịch gọi nhầm người đã trả.",
   ["CALL_02","CALL_07","CALL_11","CALL_13","CALL_18","CALL_16"]),
 ("Khuyến mãi & giá không nhất quán","KM không được áp (27→39.90/79), giá tăng bất thường, phải gọi xác minh SMS ưu đãi. Gây mất niềm tin & tranh cãi cước.",
   ["CALL_19","CALL_08","CALL_17","CALL_14","CALL_01"]),
 ("Tranh luận nợ & phí","Nghi ngờ khoản nợ + bị dọa cắt; phí trễ hạn/lãi bị phản đối.",["CALL_03","CALL_10"]),
 ("Thuê bao của người thân","Trả/đăng ký hộ line em/chồng/ông → nhầm chủ thể & chu kỳ cước.",["CALL_16","CALL_18","CALL_10","CALL_06"]),
]

ROWS={r["call_id"]:r for r in csv.DictReader(open("output/calls_classified.csv",encoding="utf-8-sig"))}
calls=[]
for f in sorted(glob.glob("stt_diar_out/*.json")):
    d=json.load(open(f,encoding="utf-8")); cid=d["call_id"]; t=d["transcript"]; turns=t["turns"]
    cust=" ".join(x["text"] for x in turns if x["speaker"]=="CLIENTE")
    ase=sum(len(x["text"]) for x in turns if x["speaker"]=="ASESOR")
    cli=sum(len(x["text"]) for x in turns if x["speaker"]=="CLIENTE")
    r=ROWS.get(cid,{})
    quote=max((x["text"] for x in turns if x["speaker"]=="CLIENTE"), key=len, default="")
    quote=re.sub(r"\s+"," ",quote).strip()
    calls.append({"phone":d["metadata"].get("customer_phone",""),"agent":d["metadata"].get("agent_code",""),
        "dur":round(t["duration_sec"]),"resp":classify(nkl(cust)),"primary":r.get("primary_vn","?"),
        "churn":r.get("churn_intent","0")=="1","neg":r.get("neg_sentiment","0")=="1",
        "ase_pct":round(100*ase/(ase+cli)) if (ase+cli) else 0,
        "quote":quote[:180]})

N=len(calls); respc=Counter(c["resp"] for c in calls)
paid=respc.get("Đã thanh toán rồi (tranh luận)",0)
avg_ase=round(sum(c["ase_pct"] for c in calls)/N)
data={"N":N,"minutes":round(sum(c["dur"] for c in calls)/60),"paid":paid,
      "paid_pct":round(100*paid/N),"avg_ase":avg_ase,"avg_cli":100-avg_ase,
      "churn":sum(c["churn"] for c in calls),"neg":sum(c["neg"] for c in calls),
      "resp_dist":respc.most_common(),"drill":DRILL,"themes":[(n,d,len(p)) for n,d,p in THEMES],
      "calls":sorted(calls,key=lambda x:-x["dur"])}
json.dump(data,open("output/audio_report_data.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)

# ---- biểu đồ ----
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.spines.top":False,"axes.spines.right":False})
# 1) phản hồi khách
items=respc.most_common()[::-1]
COLS={"Đã thanh toán rồi (tranh luận)":"#e11d48","Khác / xác nhận thông tin":"#64748b","Thắc mắc nợ / hóa đơn":"#2563eb",
      "Số tiền sai / cao bất thường":"#d97706","Không phải của tôi / người thân":"#7c3aed","Không trả được / xin khất":"#ea580c","Muốn đổi / giảm gói":"#0891b2"}
fig,ax=plt.subplots(figsize=(8,3.6))
bars=ax.barh([k for k,_ in items],[v for _,v in items],color=[COLS.get(k,"#999") for k,_ in items])
for b,(_,v) in zip(bars,items): ax.text(b.get_width()+0.1,b.get_y()+b.get_height()/2,str(v),va="center",fontweight="bold")
ax.set_xlim(0,max(v for _,v in items)+1); ax.set_title("Khách phản hồi gì khi được gọi thu cước? (n=%d)"%N,fontweight="bold",fontsize=12,pad=10)
fig.tight_layout(); fig.savefig("output/charts/audio_response.png",dpi=150,bbox_inches="tight",facecolor="white"); plt.close(fig)

# 2) chủ đề gốc rễ
th=[(n,len(p)) for n,_,p in THEMES][::-1]
fig,ax=plt.subplots(figsize=(8,2.8))
bars=ax.barh([n for n,_ in th],[c for _,c in th],color=["#7c3aed","#d97706","#ea580c","#e11d48"])
for b,(_,c) in zip(bars,th): ax.text(b.get_width()+0.05,b.get_y()+b.get_height()/2,"~%d"%c,va="center",fontweight="bold")
ax.set_xlim(0,7); ax.set_title("Chủ đề gốc rễ (cắt ngang các phản hồi)",fontweight="bold",fontsize=12,pad=10)
fig.tight_layout(); fig.savefig("output/charts/audio_themes.png",dpi=150,bbox_inches="tight",facecolor="white"); plt.close(fig)

print("→ output/audio_report_data.json + 2 charts")
print(f"N={N} | paid={paid} ({data['paid_pct']}%) | agent {avg_ase}% | churn={data['churn']} neg={data['neg']}")
