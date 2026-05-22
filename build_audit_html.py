# -*- coding: utf-8 -*-
"""File kiểm toán: nguyên văn transcript 100 thuê bao top hóa đơn,
bôi màu các cụm trigger (VÀNG = ý định rời mạng) ngay trên văn bản CÓ DẤU.
Chuẩn hóa giữ-độ-dài để vị trí khớp tuyệt đối."""
import json, glob, re, csv, html
import diarize as DZ

# --- chuẩn hóa GIỮ ĐỘ DÀI (1 ký tự -> 1 ký tự) để map vị trí về bản gốc ---
TRANS = str.maketrans("áéíóúüñàèìòù", "aeiouunaeiou")
def nkl(s): return s.lower().translate(TRANS)   # độ dài == len(s)

BOILER=[nkl(x) for x in ["asesores se encuentran ocupados","en breve lo atenderemos","horario de atencion de esta central","lunes a domingo","seis de la manana","media noche","medianoche","realiza tus tramites de manera rapida","app mibitel","con la app mibitel","descarga e ingresa","actualizar tus datos","reactivar tu linea y otras funciones","sin salir de tu casa","con un solo clic","estes donde estes","este donde estes","puedes visualizar informacion de tu linea","saldos, descuentos","recibos pendientes","canal exclusivo de migraciones","disposiciones emitidas por","estado de emergencia","planes de estudiante","no se mantendra los saldos","misma sim card","cambio de plan no tiene costo","reintegro del costo del equipo","mantengase en espera","bienvenido a bitel","gracias por comunicarse","su opinion es importante","invitamos a responder","breve encuesta","recibira una llamada","calificar la atencion","calificar nuestra atencion","podras solicitar y ejecutar tramites","area de migraciones y cancelaciones","suspension temporal podras","requiere atencion en el departamento","tipo de documento","centro de atencion al","si usted es titular","si usted no es titular","la linea debe de encontrarse activa"]]

# --- patterns trigger (khớp trên nkl). thứ tự = ưu tiên khi chồng lấn ---
PATS = [
 ("churn", re.compile(r"(portabilidad|portarme|me porto|\bportar\b|irme a (otro|claro|movistar|entel)|cambiarme de (operador|compania|empresa)|otro operador|otra operadora|dar(me|se)? de baja|\bde baja\b|cancelar (mi |la |el )?(linea|servicio|plan|cuenta|contrato)|anular (mi |la |el )?(linea|servicio))")),
 ("comp",  re.compile(r"(de claro\b|a claro\b|con claro\b|tengo claro\b|estoy (con|en) claro|claro me (ofrec|da|dio)|me ofrece claro|portarme a claro|irme a claro|\bmovistar\b|\bentel\b)")),
 ("down",  re.compile(r"(plan menor|reducir (mi )?plan|bajar de plan|reduccion de plan|un plan mas barato|algo mas economico)")),
 ("neg",   re.compile(r"(reclam|\bqueja|quejar|molest|malestar|indignad|fastidi|incomod|pesimo|mal servicio|terrible|horrible|estafa|engan|cobro indebido|cobrado de mas|abuso|fraude)")),
 ("bill",  re.compile(r"(recibo|factura|deuda|pagar|\bpago\b|\bcobr|monto|tarifa|vencid|reintegro|estado de cuenta)")),
]
LOSS=re.compile(r"(perdida|\brobo\b|me robaron|se me perdio|extravi|hurto|equipo robado)")
LABELS={"churn":"RỜI MẠNG","comp":"ĐỐI THỦ","down":"HẠ GÓI","neg":"TIÊU CỰC","bill":"HÓA ĐƠN"}

# ===== nạp dữ liệu & tính lại top 100 (giống build_top100_billing) =====
TX={}; FN={}
for f in glob.glob("stt_out/*.json"):
    try: d=json.load(open(f,encoding="utf-8"))
    except: continue
    TX[d.get("call_id")]=d.get("transcript",{}).get("text","")
    FN[d.get("call_id")]=d.get("file_name","")
rows=[r for r in csv.DictReader(open("output/calls_classified.csv",encoding="utf-8-sig")) if r["primary"]=="billing"]
def b(r,k): return r[k]=="1"
W={"churn_intent":45,"competitor":25,"downgrade":18,"repeat_call":14,"neg_sentiment":12}
scored=[]
for r in rows:
    s=sum(W[k] for k in W if b(r,k))+min(float(r["duration_min"]),20)*0.3
    scored.append((round(s,1),r))
scored.sort(key=lambda x:(-x[0],-float(x[1]["duration_min"])))
top=scored[:100]
def level(s): return "Rất cao" if s>=70 else ("Cao" if s>=45 else ("Trung bình" if s>=20 else "Thấp"))

def is_boiler(sent_nkl): return any(bp in sent_nkl for bp in BOILER)

def highlight_sentence(disp):
    """disp: câu gốc có dấu. Trả về HTML đã bôi màu (boilerplate -> mờ)."""
    nk=nkl(disp)
    if is_boiler(nk):
        return f'<span class="boiler">{html.escape(disp)}</span>'
    cat=[None]*len(disp)   # mỗi vị trí -> category (ưu tiên theo thứ tự PATS)
    loss=bool(LOSS.search(nk))
    for name,rx in PATS:
        for m in rx.finditer(nk):
            st,en=m.start(),m.end()
            if name=="churn" and loss and not re.search(r"(portab|otro operador|otra operadora|irme a|cambiarme)", m.group(0)):
                continue  # de baja do mất/trộm -> không tô churn
            for i in range(st,en):
                if cat[i] is None: cat[i]=name
    # build runs
    out=[]; i=0; n=len(disp)
    while i<n:
        c=cat[i]
        j=i
        while j<n and cat[j]==c: j+=1
        seg=html.escape(disp[i:j])
        out.append(seg if c is None else f'<mark class="{c}">{seg}</mark>')
        i=j
    return "".join(out)

def render_transcript(cid):
    """Render theo TURN đã tách người nói: Cliente (nổi bật) / Asesor (mờ) / IVR (rất mờ)."""
    raw=TX.get(cid,"")
    turns=DZ.diarize(raw)
    SPK={"CLIENTE":("KHÁCH","sp-cli"),"ASESOR":("Tư vấn viên","sp-ase"),
         "IVR":("IVR/Hệ thống","sp-ivr"),"?":("?","sp-unk")}
    out=[]
    for t in turns:
        lab,cls=SPK.get(t["speaker"],("?","sp-unk"))
        sents=re.split(r'(?<=[.?!])\s+', t["text"])
        body=" ".join(highlight_sentence(s) for s in sents if s.strip())
        out.append(f'<div class="turn {cls}"><span class="spk">{lab}</span><span class="utt">{body}</span></div>')
    return "".join(out)

def which_comp(cid):
    cn=nkl(" ".join(TX.get(cid,"").split()))
    names=[]
    if re.search(r"(de claro\b|a claro\b|con claro\b|tengo claro\b|estoy (con|en) claro|claro me (ofrec|da|dio)|me ofrece claro)",cn): names.append("Claro")
    if re.search(r"\bmovistar\b",cn): names.append("Movistar")
    if re.search(r"\bentel\b",cn): names.append("Entel")
    return "/".join(dict.fromkeys(names))

# ===== render HTML =====
cards=[]
for i,(sc,r) in enumerate(top,1):
    cid=r["call_id"]; comp=which_comp(cid)
    chips=[]
    if b(r,"churn_intent"): chips.append('<span class="chip churn">Ý định rời</span>')
    if comp: chips.append(f'<span class="chip comp">Đối thủ: {html.escape(comp)}</span>')
    if b(r,"downgrade"): chips.append('<span class="chip down">Đòi hạ gói</span>')
    if b(r,"repeat_call"): chips.append('<span class="chip rep">Gọi lại</span>')
    if b(r,"neg_sentiment"): chips.append('<span class="chip neg">Cảm xúc tiêu cực</span>')
    cards.append(f'''
    <div class="card" data-phone="{html.escape(r['phone'])}">
      <div class="ch">
        <div class="rk">#{i}</div>
        <div class="ph">{html.escape(r['phone'])}</div>
        <div class="sc">Điểm <b>{sc}</b> · <span class="lv">{level(sc)}</span></div>
        <div class="meta">{html.escape(r['month_vn'])} · {r['duration_min']}′ · STT {r['confidence']}</div>
      </div>
      <div class="chips">{''.join(chips)}</div>
      <div class="tx">{render_transcript(cid)}</div>
      <div class="cid">call_id: {html.escape(cid)} &nbsp;·&nbsp; file: {html.escape(FN.get(cid,''))}</div>
    </div>''')

HTML=f'''<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kiểm toán nguyên văn — Top 100 Hóa đơn nguy cơ rời mạng · Bitel</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:#f1f5f9;color:#0f172a;line-height:1.6}}
.wrap{{max-width:1000px;margin:0 auto;padding:20px 18px 60px}}
header{{background:linear-gradient(110deg,#111827,#1f2937);color:#fff;border-radius:14px;padding:20px 24px;box-shadow:0 10px 30px rgba(2,6,23,.18)}}
header .badge{{background:#FDC700;color:#1a1a1a;font-weight:800;padding:3px 10px;border-radius:6px;font-size:11px;letter-spacing:.5px}}
header h1{{margin:10px 0 4px;font-size:21px}}
header p{{margin:0;color:#cbd5e1;font-size:13px}}
.legend{{position:sticky;top:0;z-index:10;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 16px;margin:14px 0;display:flex;gap:16px;flex-wrap:wrap;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.04)}}
.legend b{{font-size:13px}}
.lg{{font-size:12.5px;font-weight:600;padding:2px 8px;border-radius:5px}}
mark{{padding:1px 2px;border-radius:3px;font-weight:600}}
mark.churn,.lg.churn{{background:#FDE047}}   /* VÀNG = rời mạng */
mark.comp,.lg.comp{{background:#FDBA74}}
mark.down,.lg.down{{background:#D8B4FE}}
mark.neg,.lg.neg{{background:#FECACA}}
mark.bill,.lg.bill{{background:#BAE6FD}}
.search{{padding:8px 12px;border:1px solid #cbd5e1;border-radius:9px;font-size:14px;width:220px;margin-left:auto}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:13px;padding:16px 18px;margin:14px 0;box-shadow:0 1px 4px rgba(0,0,0,.04)}}
.ch{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;border-bottom:1px solid #f1f5f9;padding-bottom:10px}}
.rk{{font-size:13px;font-weight:800;color:#fff;background:#e11d48;border-radius:7px;padding:3px 9px}}
.ph{{font-size:21px;font-weight:800;letter-spacing:.5px}}
.sc{{font-size:13px;color:#475569}} .sc .lv{{color:#9f1239;font-weight:700}}
.meta{{font-size:12px;color:#94a3b8;margin-left:auto}}
.chips{{margin:10px 0}}
.chip{{display:inline-block;font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:20px;margin:2px 4px 2px 0}}
.chip.churn{{background:#FDE047}} .chip.comp{{background:#FDBA74}} .chip.down{{background:#D8B4FE}} .chip.rep{{background:#bbf7d0}} .chip.neg{{background:#FECACA}}
.tx{{font-size:14px;color:#1e293b;background:#fafbfc;border:1px solid #f1f5f9;border-radius:9px;padding:11px 12px;max-height:none}}
.turn{{display:flex;gap:9px;margin:4px 0;padding:5px 9px;border-radius:7px;align-items:flex-start}}
.turn .spk{{flex:0 0 88px;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px;padding-top:2px}}
.turn .utt{{flex:1}}
.sp-cli{{background:#fffbeb;border-left:3px solid #FDC700}}
.sp-cli .spk{{color:#b45309}}
.sp-ase{{background:#f8fafc;border-left:3px solid #cbd5e1;color:#64748b}}
.sp-ase .spk{{color:#64748b}}
.sp-ivr{{background:transparent;color:#cbd5e1;font-style:italic;border-left:3px solid #f1f5f9}}
.sp-ivr .spk{{color:#cbd5e1}}
.sp-unk{{background:#fafafa;border-left:3px solid #e5e7eb;color:#94a3b8}}
.sp-unk .spk{{color:#94a3b8}}
.tx .boiler{{color:#cbd5e1;font-style:italic}}   /* IVR/boilerplate đã bỏ qua -> mờ */
.cid{{font-size:11px;color:#94a3b8;margin-top:8px;font-family:monospace}}
.hide{{display:none}}
.note{{font-size:12.5px;color:#64748b;font-style:italic;margin:6px 2px}}
</style></head><body><div class="wrap">
<header>
  <span class="badge">BITEL PERÚ · KIỂM TOÁN PHÂN LOẠI</span>
  <h1>Nguyên văn transcript + bôi vàng cụm xác định — Top 100 Hóa đơn nguy cơ rời mạng</h1>
  <p>Mỗi thẻ là toàn văn cuộc gọi, ĐÃ TÁCH NGƯỜI NÓI: <b style="color:#b45309">KHÁCH</b> (nền vàng nhạt) · <b style="color:#64748b">Tư vấn viên</b> (nền xám) · IVR (mờ). Cụm <b style="color:#FDE047">VÀNG</b> = chữ xác định "ý định rời mạng". Churn nay chỉ tính trên LỜI KHÁCH.</p>
</header>
<div class="legend">
  <b>Chú giải bôi màu:</b>
  <span class="lg churn">VÀNG · Rời mạng (portabilidad/hủy line)</span>
  <span class="lg comp">Đối thủ (Movistar/Claro/Entel)</span>
  <span class="lg down">Đòi hạ gói</span>
  <span class="lg neg">Cảm xúc tiêu cực</span>
  <span class="lg bill">Hóa đơn</span>
  <input class="search" id="q" placeholder="Tìm theo số thuê bao…">
</div>
<div class="note">Nguồn: {len(top)} thuê bao điểm cao nhất nhóm Hóa đơn & Thanh toán (churn đã hiệu chỉnh, chỉ tính lời khách). Tô màu = đúng cụm từ khóa quy tắc đã khớp. Người nói được tách bằng dấu hiệu ngôn ngữ — cụm churn nằm trong turn "Tư vấn viên" thì KHÔNG tính là ý định rời của khách.</div>
{''.join(cards)}
</div>
<script>
const q=document.getElementById('q');
q.addEventListener('input',()=>{{const v=q.value.trim();
  document.querySelectorAll('.card').forEach(c=>{{
    c.classList.toggle('hide', v && !c.dataset.phone.includes(v));}});}});
</script>
</body></html>'''

open("output/Audit_Top100_NguyenVan.html","w",encoding="utf-8").write(HTML)
print(f"→ output/Audit_Top100_NguyenVan.html ({len(HTML)//1024} KB) · {len(top)} thẻ")
