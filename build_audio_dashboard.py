# -*- coding: utf-8 -*-
"""Dashboard riêng cho NHÓM AUDIO (đã tách vai pyannote) — chiến dịch gọi RA thu cước 'cpc'.
Tự chứa, inline SVG. Phân tích phản hồi khách + transcript tách vai Asesor/Cliente."""
import json, glob, re, csv, os, html
def nkl(s): return (s or "").lower().translate(str.maketrans("áéíóúüñàèìòù","aeiouunaeiou"))

DIAR_DIR="stt_diar_out"; OUT="output/audio_dashboard.html"

# ---- phân loại PHẢN HỒI khách (cuộc gọi RA thu cước) — ưu tiên theo thứ tự ----
OBJ=[
 ("Không phải của tôi / người thân","#7c3aed", r"(le puse (el plan|la linea) a|es de mi (hermana|hijo|esposa|esposo|mama|papa|hermano|cunad)|no es mi (numero|linea)|es otro numero|esa linea no es)"),
 ("Đã thanh toán rồi (tranh luận)","#e11d48", r"(ya (he )?(pague|cancele|pagado)|he pagado|se acaba de pagar|ya esta (pagado|cancelado)|hice el pago (ya|hace)|acabo de pagar|pague (doble|dos veces)|pago doble|ya cancele)"),
 ("Không trả được / xin khất","#ea580c", r"(no (he )?(puedo|podido) pagar|por motivos|por (mi )?salud|no tengo (para|como|dinero)|me olvide|todavia no|aun no he|la proxima semana|me esperan|me espera|cuando (pueda|cobre|tenga))"),
 ("Số tiền sai / cao bất thường","#d97706", r"(monto que (no|yo no)|no pagaba|me sale (mas|el monto)|me estan subiendo|mas (caro|elevado)|subio|aumento|esta mal el monto|no es el monto|por que (tan|me cobran mas))"),
 ("Muốn đổi / giảm gói","#0891b2", r"(bajar (al|el|de) plan|cambiar (de |el )?plan|plan de \d+ (igual|soles)|plan mas (barato|economico)|reducir)"),
 ("Cam kết / hỏi cách trả","#059669", r"(voy a pagar|si (voy|lo) a (pagar|cancelar)|quiero (hacer el |hacer mi )?pago|como (pago|hago el pago)|donde (pago|puedo pagar)|hoy (mismo|dia)|manana (pago|cancelo)|este fin)"),
 ("Thắc mắc nợ / hóa đơn","#2563eb", r"(tengo una deuda|que deuda|de que (mes|monto)|cuanto (debo|es mi)|no me (llega|llego)|no entiendo (el|por)|sobre el tema de|queria consultar)"),
]
def classify_resp(cust_cn):
    for name,col,pat in OBJ:
        if re.search(pat,cust_cn): return name,col
    return "Khác / xác nhận thông tin","#64748b"

# ---- DRILL-DOWN: chi nhánh lý do con (đọc thủ công từng cuộc, N=20) ----
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
# ---- CHỦ ĐỀ XUYÊN SUỐT (gốc rễ, cắt ngang các nhóm) ----
THEMES=[
 ("Phản ánh & xử lý thanh toán","#e11d48","Trả rồi chưa cập nhật/chưa mở line, trả trùng-nhầm số, app bên thứ 3 trễ. Nhóm LỚN NHẤT — gốc rễ khiến chiến dịch gọi nhầm người đã trả.",
   ["CALL_02","CALL_07","CALL_11","CALL_13","CALL_18","CALL_16"]),
 ("Khuyến mãi & giá không nhất quán","#ea580c","KM không được áp (27→39.90/79), giá tăng bất thường, phải gọi xác minh SMS ưu đãi. Gây mất niềm tin & tranh cãi cước.",
   ["CALL_19","CALL_08","CALL_17","CALL_14","CALL_01"]),
 ("Tranh luận nợ & phí","#d97706","Nghi ngờ khoản nợ + bị dọa cắt; phí trễ hạn/lãi bị phản đối.",
   ["CALL_03","CALL_10"]),
 ("Thuê bao của người thân","#7c3aed","Trả/đăng ký hộ line em/chồng/ông → nhầm chủ thể & chu kỳ cước.",
   ["CALL_16","CALL_18","CALL_10","CALL_06"]),
]

# flags từ phân tích chung (đã hiệu chỉnh, lời khách)
ROWS={r["call_id"]:r for r in csv.DictReader(open("output/calls_classified.csv",encoding="utf-8-sig"))}

calls=[]
for f in sorted(glob.glob(f"{DIAR_DIR}/*.json")):
    d=json.load(open(f,encoding="utf-8")); cid=d["call_id"]; t=d["transcript"]; turns=t["turns"]
    cust=" ".join(x["text"] for x in turns if x["speaker"]=="CLIENTE")
    ase_ch=sum(len(x["text"]) for x in turns if x["speaker"]=="ASESOR")
    cli_ch=sum(len(x["text"]) for x in turns if x["speaker"]=="CLIENTE")
    resp,rcol=classify_resp(nkl(cust))
    r=ROWS.get(cid,{})
    # trích câu khách dài nhất làm "tiếng nói khách"
    quote=max((x["text"] for x in turns if x["speaker"]=="CLIENTE"), key=len, default="")
    calls.append({
        "phone":d["metadata"].get("customer_phone",""),"agent":d["metadata"].get("agent_code",""),
        "dur":t["duration_sec"],"turns":turns,"resp":resp,"rcol":rcol,
        "primary":r.get("primary_vn","?"),"churn":r.get("churn_intent","0")=="1",
        "neg":r.get("neg_sentiment","0")=="1","comp":r.get("competitor","0")=="1",
        "ase_pct":round(100*ase_ch/(ase_ch+cli_ch)) if (ase_ch+cli_ch) else 0,
        "cli_pct":round(100*cli_ch/(ase_ch+cli_ch)) if (ase_ch+cli_ch) else 0,
        "conf":t.get("avg_confidence"),"quote":quote,
    })

N=len(calls); tot_min=round(sum(c["dur"] for c in calls)/60)
from collections import Counter
respc=Counter(c["resp"] for c in calls)
reasonc=Counter(c["primary"] for c in calls)
paid=respc.get("Đã thanh toán rồi (tranh luận)",0)
avg_ase=round(sum(c["ase_pct"] for c in calls)/N); avg_cli=100-avg_ase
churn_n=sum(c["churn"] for c in calls); neg_n=sum(c["neg"] for c in calls)
avg_turns=round(sum(len(c["turns"]) for c in calls)/N)
RESP_COL={name:col for name,col,_ in OBJ}; RESP_COL["Khác / xác nhận thông tin"]="#64748b"

def esc(s): return html.escape(s or "")

# ---- IVR/boilerplate detect để làm mờ trong transcript ----
import diarize as DZ
def render_turns(turns):
    out=[]
    for t in turns:
        spk=t["speaker"]; cls={"ASESOR":"ase","CLIENTE":"cli","IVR":"ivr"}.get(spk,"ase")
        lab={"ASESOR":"Tư vấn viên","CLIENTE":"KHÁCH","IVR":"IVR"}.get(spk,spk)
        txt=esc(re.sub(r"\s+"," ",t["text"]).strip())
        vi=esc(re.sub(r"\s+"," ",t.get("text_vi","")).strip())
        vihtml=f'<span class="vi">🇻🇳 {vi}</span>' if vi else ''
        out.append(f'<div class="tn {cls}"><span class="who">{lab}</span>'
                   f'<span class="ut"><span class="es">{txt}</span>{vihtml}</span></div>')
    return "".join(out)

# bar chart ngang (SVG)
def hbar(items, w=560, rh=30, pl=230):
    mx=max((v for _,v,_ in items), default=1); H=len(items)*rh+6; rows=[]
    for i,(lab,v,col) in enumerate(items):
        y=i*rh+3; bw=(w-pl-46)*(v/mx) if mx else 0
        rows.append(f'<g><text x="{pl-10}" y="{y+rh/2+1}" text-anchor="end" font-size="12.5" font-weight="600" fill="#334155">{esc(lab)}</text>'
                    f'<rect x="{pl}" y="{y+5}" width="{max(bw,2):.0f}" height="{rh-13}" rx="5" fill="{col}"/>'
                    f'<text x="{pl+max(bw,2)+8:.0f}" y="{y+rh/2+1}" font-size="12" font-weight="700" fill="#0f172a">{v}</text></g>')
    return f'<svg viewBox="0 0 {w} {H}" style="width:100%;height:auto">{"".join(rows)}</svg>'

resp_items=[(n,respc[n],RESP_COL.get(n,"#64748b")) for n in sorted(respc,key=lambda k:-respc[k])]
reason_items=[(n,reasonc[n],c) for n,c in zip([k for k in sorted(reasonc,key=lambda k:-reasonc[k])],
              ["#FDC700","#2563eb","#059669","#e11d48","#7c3aed","#ea580c"])][:6]
reason_items=[(n,reasonc[n],["#FDC700","#2563eb","#059669","#e11d48","#7c3aed","#ea580c"][i]) for i,n in enumerate(sorted(reasonc,key=lambda k:-reasonc[k]))]

cards=[]
for i,c in enumerate(sorted(calls,key=lambda x:-x["dur"]),1):
    flags=[]
    if c["churn"]: flags.append('<span class="fl churn">Ý định rời</span>')
    if c["neg"]: flags.append('<span class="fl neg">Tiêu cực</span>')
    if c["comp"]: flags.append('<span class="fl comp">Nhắc đối thủ</span>')
    cards.append(f'''
    <div class="card" data-phone="{esc(c['phone'])}">
      <div class="ch">
        <span class="rk">#{i}</span>
        <span class="ph">{esc(c['phone'])}</span>
        <span class="resp" style="background:{c['rcol']}">{esc(c['resp'])}</span>
        <span class="meta">TVV: {esc(c['agent'])} · {round(c['dur'])}s · {len(c['turns'])} lượt · STT {c['conf']}</span>
      </div>
      <div class="sub">Lý do (cả hội thoại): <b>{esc(c['primary'])}</b> {''.join(flags)}
        <span class="ratio">Tỷ lệ nói — TVV {c['ase_pct']}% / Khách {c['cli_pct']}%
          <span class="rbar"><i style="width:{c['ase_pct']}%"></i></span></span>
      </div>
      <details><summary>Xem nguyên văn (đã tách vai)</summary><div class="tx">{render_turns(c['turns'])}</div></details>
    </div>''')

# render CHỦ ĐỀ XUYÊN SUỐT
themes_html=""
for name,col,desc,phs in THEMES:
    themes_html+=(f'<div class="theme" style="border-left-color:{col}">'
                  f'<div class="tt"><b>{esc(name)}</b><span class="cnt" style="background:{col}">~{len(phs)} cuộc</span></div>'
                  f'<div class="td">{esc(desc)}</div><div class="tp">{" · ".join(phs)}</div></div>')
# render DRILL-DOWN theo thứ tự nhóm giảm dần
drill_html=""
for cat in sorted(respc,key=lambda k:-respc[k]):
    branches=DRILL.get(cat,[])
    if not branches: continue
    items=""
    for lab,desc,phs in branches:
        items+=(f'<li><span class="bn">{len(phs)}</span> <b>{esc(lab)}</b><br>'
                f'<span class="bd">{esc(desc)}</span> <span class="bp">{" · ".join(phs)}</span></li>')
    drill_html+=(f'<details class="drill"><summary>{esc(cat)} <span class="sc2">{respc[cat]} cuộc</span></summary>'
                 f'<ul>{items}</ul></details>')

HTML=f'''<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bitel · Dashboard nhóm Audio (gọi ra thu cước)</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:#f1f5f9;color:#0f172a;line-height:1.5}}
.wrap{{max-width:1020px;margin:0 auto;padding:20px 18px 60px}}
header{{background:linear-gradient(110deg,#111827,#1f2937);color:#fff;border-radius:14px;padding:22px 26px}}
header .badge{{background:#FDC700;color:#1a1a1a;font-weight:800;padding:3px 10px;border-radius:6px;font-size:11px;letter-spacing:.5px}}
header h1{{margin:10px 0 4px;font-size:21px}} header p{{margin:0;color:#cbd5e1;font-size:13px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin:16px 0}}
@media(max-width:780px){{.kpis{{grid-template-columns:repeat(2,1fr)}}}}
.kpi{{background:#fff;border:1px solid #e2e8f0;border-radius:13px;padding:14px 16px;position:relative;overflow:hidden}}
.kpi .v{{font-size:26px;font-weight:800}} .kpi .l{{font-size:12px;color:#475569;font-weight:600}} .kpi .s{{font-size:11px;color:#94a3b8;margin-top:2px}}
.kpi .bar{{position:absolute;left:0;top:0;bottom:0;width:5px;background:#FDC700}}
.kpi.red .bar{{background:#e11d48}} .kpi.red .v{{color:#e11d48}} .kpi.blu .bar{{background:#2563eb}} .kpi.gr .bar{{background:#059669}}
.card,.panel{{background:#fff;border:1px solid #e2e8f0;border-radius:13px;padding:16px 18px;margin-top:14px}}
.panel h2{{margin:0 0 4px;font-size:16px}} .panel .h2es{{font-size:12px;color:#94a3b8;font-style:italic;margin-bottom:10px}}
.find{{background:linear-gradient(180deg,#fffbeb,#fff);border:1px solid #fde68a}}
.find ul{{margin:6px 0 0;padding-left:20px}} .find li{{margin:6px 0;font-size:14px}} .find b{{color:#b45309}}
.sec{{font-size:12px;font-weight:800;color:#b45309;letter-spacing:1px;text-transform:uppercase;margin:26px 4px 0}}
.search{{padding:8px 12px;border:1px solid #cbd5e1;border-radius:9px;font-size:14px;width:200px;float:right}}
.ch{{display:flex;align-items:center;gap:11px;flex-wrap:wrap}}
.rk{{font-size:12px;font-weight:800;color:#fff;background:#475569;border-radius:7px;padding:2px 8px}}
.ph{{font-size:18px;font-weight:800}}
.resp{{color:#fff;font-size:11.5px;font-weight:700;padding:3px 10px;border-radius:20px}}
.meta{{font-size:11.5px;color:#94a3b8;margin-left:auto}}
.sub{{font-size:12.5px;color:#475569;margin-top:9px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.fl{{font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:3px}}
.fl.churn{{background:#FDE047}} .fl.neg{{background:#FECACA}} .fl.comp{{background:#FDBA74}}
.ratio{{margin-left:auto;display:flex;align-items:center;gap:7px;color:#64748b}}
.rbar{{display:inline-block;width:90px;height:8px;background:#bbf7d0;border-radius:4px;overflow:hidden;vertical-align:middle}}
.rbar i{{display:block;height:100%;background:#94a3b8}}
details{{margin-top:10px}} summary{{cursor:pointer;font-size:12.5px;color:#2563eb;font-weight:600}}
.tx{{margin-top:8px;background:#fafbfc;border:1px solid #f1f5f9;border-radius:9px;padding:8px 10px}}
.tn{{display:flex;gap:8px;margin:3px 0;padding:4px 8px;border-radius:6px;font-size:13px}}
.tn .who{{flex:0 0 80px;font-size:10px;font-weight:800;text-transform:uppercase;padding-top:2px}}
.tn.cli{{background:#fffbeb;border-left:3px solid #FDC700}} .tn.cli .who{{color:#b45309}}
.tn.ase{{background:#f8fafc;border-left:3px solid #cbd5e1;color:#64748b}} .tn.ase .who{{color:#64748b}}
.tn.ivr{{color:#cbd5e1;font-style:italic;border-left:3px solid #f1f5f9}} .tn.ivr .who{{color:#cbd5e1}}
.tn .ut .es{{display:block}}
.tn .ut .vi{{display:block;font-size:12px;color:#0369a1;margin-top:3px;padding-top:3px;border-top:1px dashed #e2e8f0;font-style:italic}}
body.hide-vi .tn .ut .vi{{display:none}}
.vitoggle{{float:right;font-size:12.5px;font-weight:700;color:#0369a1;background:#e0f2fe;border:1px solid #bae6fd;border-radius:8px;padding:6px 12px;cursor:pointer}}
.note{{font-size:12px;color:#64748b;font-style:italic;margin:8px 2px}}
.theme{{background:#fafbfc;border:1px solid #eef2f7;border-left:5px solid #999;border-radius:9px;padding:11px 14px;margin:9px 0}}
.theme .tt{{display:flex;align-items:center;gap:10px}} .theme .tt b{{font-size:14.5px}}
.theme .cnt{{color:#fff;font-size:11px;font-weight:700;padding:2px 9px;border-radius:20px;margin-left:auto}}
.theme .td{{font-size:13px;color:#334155;margin-top:4px}} .theme .tp{{font-size:11px;color:#94a3b8;font-family:monospace;margin-top:4px}}
details.drill{{border:1px solid #e2e8f0;border-radius:9px;margin:7px 0;padding:4px 12px;background:#fff}}
details.drill summary{{font-size:13.5px;font-weight:700;color:#0f172a}}
details.drill .sc2{{color:#64748b;font-weight:600;font-size:12px;margin-left:6px}}
details.drill ul{{margin:8px 0 6px;padding-left:6px;list-style:none}}
details.drill li{{margin:8px 0;font-size:13px;padding-left:34px;position:relative}}
details.drill .bn{{position:absolute;left:0;top:0;background:#1f2937;color:#fff;font-size:11px;font-weight:700;width:22px;height:22px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center}}
details.drill .bd{{color:#475569}} details.drill .bp{{color:#94a3b8;font-family:monospace;font-size:11px}}
</style></head><body><div class="wrap">
<header>
  <span class="badge">BITEL PERÚ · NHÓM AUDIO (PILOT) · TÁCH VAI PYANNOTE</span>
  <h1>Dashboard chiến dịch gọi RA thu cước — {N} cuộc gọi</h1>
  <p>Phân tích từ audio thật, đã tách vai Tư vấn viên/Khách. <i>Đây là cuộc gọi RA (outbound) Bitel chủ động gọi khách để nhắc/thu cước ("cpc"), KHÔNG phải khách gọi vào.</i></p>
</header>

<div class="kpis">
  <div class="kpi"><div class="bar"></div><div class="l">Số cuộc gọi</div><div class="v">{N}</div><div class="s">{tot_min} phút audio · TB {avg_turns} lượt/cuộc</div></div>
  <div class="kpi red"><div class="bar"></div><div class="l">Khách nói "ĐÃ thanh toán"</div><div class="v">{paid}</div><div class="s">{round(100*paid/N)}% — gọi nhầm người đã trả?</div></div>
  <div class="kpi blu"><div class="bar"></div><div class="l">Tỷ lệ nói: Khách</div><div class="v">{avg_cli}%</div><div class="s">Tư vấn viên {avg_ase}% (gọi ra, agent dẫn dắt)</div></div>
  <div class="kpi gr"><div class="bar"></div><div class="l">Ý định rời / Tiêu cực</div><div class="v">{churn_n}/{neg_n}</div><div class="s">trên {N} cuộc</div></div>
</div>

<div class="panel find">
  <h2>🔑 Phát hiện chính (nhóm pilot {N} cuộc)</h2>
  <ul>
    <li><b>{round(100*paid/N)}% khách phản hồi "tôi đã thanh toán rồi"</b> ({paid}/{N}) — kể cả trường hợp trả 2 lần. Chiến dịch đang gọi nhắc nợ nhiều người ĐÃ trả → nghi <b>độ trễ đồng bộ/phản ánh thanh toán</b> giữa hệ thống thu và hệ thống gọi. Cần đối soát dữ liệu trước khi gọi.</li>
    <li><b>Tư vấn viên nói {avg_ase}%, khách chỉ {avg_cli}%</b> — đúng đặc thù gọi RA (agent dẫn dắt). Vì vậy mọi phân tích "vấn đề" PHẢI tách vai để không tính nhầm lời agent.</li>
    <li>Nhóm nhỏ nhưng đã lộ các tình huống cần quy trình: <b>số tiền tăng bất thường</b>, <b>thuê bao của người thân</b>, <b>xin khất vì lý do sức khỏe/tài chính</b>.</li>
  </ul>
  <div class="note">⚠️ N={N} (pilot) — tỷ lệ chỉ mang tính tham khảo, cần thêm mẫu để kết luận thống kê.</div>
</div>

<div class="sec">① Phản hồi của khách / Respuesta del cliente</div>
<div class="panel">
  <h2>Khách phản hồi gì khi được gọi thu cước?</h2>
  <div class="h2es">Phân loại từ lời KHÁCH (đã tách vai)</div>
  {hbar(resp_items)}
</div>

<div class="sec">② Chi nhánh lý do chi tiết / Drill-down</div>
<div class="panel">
  <h2>Bóc tách lý do con trong từng nhóm phản hồi</h2>
  <div class="h2es">Đọc từng cuộc — bấm để mở. Số tròn = số cuộc; mã = số thuê bao để truy ngược.</div>
  {drill_html}
</div>

<div class="sec">③ Chủ đề xuyên suốt (gốc rễ) / Temas raíz</div>
<div class="panel">
  <h2>Bốn nhóm gốc rễ cắt ngang các phản hồi</h2>
  <div class="h2es">Tổng hợp nguyên nhân thực sự đằng sau cuộc gọi — quan trọng cho hành động</div>
  {themes_html}
  <div class="note">Một cuộc có thể thuộc nhiều chủ đề (vd vừa "đã trả" vừa "thuê bao người thân").</div>
</div>

<div class="sec">④ Lý do / chủ đề & chất lượng</div>
<div class="panel">
  <h2>Phân bố chủ đề (phân loại trên cả hội thoại)</h2>
  <div class="h2es">Đa số là Hóa đơn & Thanh toán — đúng bản chất chiến dịch thu cước</div>
  {hbar(reason_items)}
</div>

<div class="sec">⑤ Chi tiết từng cuộc (nguyên văn tách vai + dịch tiếng Việt)</div>
<button class="vitoggle" id="vibtn">🇻🇳 Ẩn bản dịch tiếng Việt</button>
<input class="search" id="q" placeholder="Tìm số thuê bao…">
<div style="clear:both"></div>
<div class="note">Mỗi lượt thoại hiển thị nguyên văn tiếng TBN + <b style="color:#0369a1">bản dịch tiếng Việt</b> (dịch máy NLLB, chạy GPU cục bộ). <b style="color:#b45309">KHÁCH</b> = nền vàng · <b style="color:#64748b">Tư vấn viên</b> = nền xám · IVR mờ.</div>
{''.join(cards)}
</div>
<script>
const q=document.getElementById('q');
q.addEventListener('input',()=>{{const v=q.value.trim();document.querySelectorAll('.card').forEach(c=>c.style.display=(!v||c.dataset.phone.includes(v))?'':'none');}});
const vb=document.getElementById('vibtn');
vb.addEventListener('click',()=>{{document.body.classList.toggle('hide-vi');
  vb.textContent=document.body.classList.contains('hide-vi')?'🇻🇳 Hiện bản dịch tiếng Việt':'🇻🇳 Ẩn bản dịch tiếng Việt';}});
</script>
</body></html>'''
os.makedirs("output",exist_ok=True)
open(OUT,"w",encoding="utf-8").write(HTML)
print(f"→ {OUT} ({len(HTML)//1024} KB) · {N} cuộc")
print(f"Phản hồi: {dict(respc)}")
print(f"Talk ratio: TVV {avg_ase}% / Khách {avg_cli}% | 'đã thanh toán': {paid}/{N}")
