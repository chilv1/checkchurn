# -*- coding: utf-8 -*-
"""
Bitel Peru - Call Center Churn Analysis
Phân loại 5.288 transcript cuộc gọi (tiếng Tây Ban Nha) thành lý do gọi + tín hiệu churn.
Xuất: calls_classified.csv (per-call) + aggregates.json (cho dashboard).
"""
import json, glob, re, os, unicodedata
from collections import Counter, defaultdict
from datetime import datetime
import diarize as DZ   # bộ tách vai Asesor/Cliente (churn/cảm xúc/đối thủ chỉ tính trên lời khách)

STT_DIRS = ["stt_diar_out", "stt_out"]  # ưu tiên audio đã tách vai (schema 2.0), fallback transcript cũ
OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1) Chuẩn hoá văn bản: bỏ dấu để khớp ổn định (STT hay rớt dấu)
# ---------------------------------------------------------------------------
def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                    if unicodedata.category(c) != "Mn")

def norm(s):
    return strip_accents((s or "").lower())

# ---------------------------------------------------------------------------
# 2) Bỏ các câu boilerplate IVR/giữ máy/khảo sát/menu để không gây nhiễu
#    (so khớp trên văn bản đã chuẩn hoá - không dấu)
# ---------------------------------------------------------------------------
BOILERPLATE = [norm(x) for x in [
 "asesores se encuentran ocupados","en breve lo atenderemos","horario de atencion de esta central",
 "lunes a domingo","seis de la manana","media noche","medianoche",
 "realiza tus tramites de manera rapida","app mibitel","con la app mibitel","descarga e ingresa",
 "actualizar tus datos","reactivar tu linea y otras funciones","sin salir de tu casa","con un solo clic",
 "estes donde estes","este donde estes","puedes visualizar informacion de tu linea",
 "saldos, descuentos","recibos pendientes","canal exclusivo de migraciones",
 "disposiciones emitidas por","estado de emergencia","planes de estudiante",
 "no se mantendra los saldos","misma sim card","cambio de plan no tiene costo",
 "reintegro del costo del equipo","mantengase en espera","bienvenido a bitel",
 "le saluda","les saluda","gracias por comunicarse","planes con consideraciones especiales",
 "su opinion es importante","invitamos a responder","breve encuesta","recibira una llamada",
 "calificar la atencion","calificar nuestra atencion","podras solicitar y ejecutar tramites",
 "area de migraciones y cancelaciones","suspension temporal podras","requiere atencion en el departamento",
 "departamento, provincia","tipo de documento","manejo de informacion","centro de atencion al",
 "para su atencion","si usted es titular","si usted no es titular","no debe estar suspendida o bloqueada",
 "la linea debe de encontrarse activa","quiere realizar el proceso de migracion",
]]

def clean_text(raw):
    """Tách câu và loại câu chứa cụm boilerplate. Trả về (clean_norm, clean_display)."""
    disp = raw or ""
    sents = re.split(r'(?<=[.?!])\s+', disp)
    kept_disp, kept_norm = [], []
    for s in sents:
        sn = norm(s)
        if any(b in sn for b in BOILERPLATE):
            continue
        kept_disp.append(s); kept_norm.append(sn)
    return " ".join(kept_norm), " ".join(kept_disp)

# ---------------------------------------------------------------------------
# 3) Taxonomy lý do gọi (đa nhãn). Mỗi danh mục: từ khoá MẠNH (w=3) + HỖ TRỢ (w=1)
#    Pattern viết KHÔNG DẤU (vì khớp trên văn bản đã chuẩn hoá).
# ---------------------------------------------------------------------------
# (key, VN, ES, strong[], weak[])
CATEGORIES = [
 ("billing", "Hóa đơn & Thanh toán", "Facturación y pagos",
   [r"\brecibo", r"\bfactura", r"\bdeuda", r"\bpagar\b", r"\bpago\b", r"monto a pagar",
    r"vencid", r"cancelar (mi |la |el )?(deuda|recibo|factura|pago|monto|cuenta)",
    r"cobro indebido", r"me (cobr|estan cobrando)", r"doble cobro", r"facturacion"],
   [r"\bcobr", r"\btarifa", r"cuanto (pago|debo|es)", r"\bsoles\b", r"fecha de pago",
    r"corte por (deuda|falta)", r"estado de cuenta"]),

 ("plan_change", "Đổi gói cước", "Migración / Cambio de plan",
   [r"\bmigra", r"migracion", r"cambio de plan", r"cambiar (de |mi )?plan",
    r"plan menor", r"plan mayor", r"reducir (mi )?plan", r"reduccion de plan",
    r"subir de plan", r"bajar de plan", r"cambiarme de plan"],
   [r"otro plan", r"cambio de tarifa", r"plan de \d", r"que plan"]),

 ("internet", "Internet & Tốc độ", "Internet y velocidad de datos",
   [r"\binternet", r"velocidad", r"navega", r"\bgigas\b", r"\bmegas\b",
    r"datos? mobil", r"datos? movil", r"sin internet", r"no tengo internet",
    r"internet (lent|no)", r"alta velocidad", r"se acaba(ron)? (mis )?(gigas|datos)"],
   [r"\blent", r"\bnavegar", r"consumo de datos", r"\bgb\b", r"se va el internet"]),

 ("coverage", "Phủ sóng & Tín hiệu", "Cobertura y señal",
   [r"cobertura", r"\bsenal\b", r"sin senal", r"no (tengo|hay) senal",
    r"no (tengo|hay) cobertura", r"mala senal", r"no entra (la )?senal", r"sin cobertura"],
   [r"\bantena", r"zona sin", r"se cae la (senal|red)", r"\bred\b movil"]),

 ("promo", "Khuyến mãi & Ưu đãi", "Promociones y descuentos",
   [r"promocion", r"descuento", r"\boferta", r"beneficio", r"campana", r"promo\b"],
   [r"regalo", r"gratis", r"bono", r"doble de gigas"]),

 ("suspension", "Tạm ngưng / Khôi phục / Cắt", "Suspensión / Reactivación / Corte",
   [r"suspension", r"suspend", r"bloque", r"reactiv", r"reposicion",
    r"linea (cortad|suspendi|bloquead)", r"esta (cortad|suspendi|bloquead)",
    r"corte de (linea|servicio)", r"me cortaron", r"esta inactiva"],
   [r"\bcorte\b", r"cortad", r"activar (mi |la )?linea", r"habilitar"]),

 ("voice_sms", "Cuộc gọi, SMS & Thoại", "Llamadas, SMS y voz",
   [r"no puedo (llamar|hacer llamadas)", r"no me (llegan|entran) (los )?mensajes",
    r"no (puedo|me deja) (enviar|mandar) mensajes", r"problema(s)? (para|con) (las )?llamadas",
    r"no entran (las )?llamadas", r"se corta(n)? (las )?llamadas", r"buzon de voz", r"no recibo llamadas"],
   [r"\bmensaje de texto", r"\bsms\b", r"llamadas internacionales"]),

 ("device_sim", "Thiết bị / SIM / Chip", "Equipo / SIM / Chip",
   [r"\bchip\b", r"sim card", r"cambio de chip", r"chip nuevo", r"equipo bloqueado",
    r"\bimei\b", r"duplicado de chip", r"\besim\b", r"mi equipo no", r"celular bloqueado"],
   [r"\bequipo\b", r"\bcelular\b", r"\btelefono\b", r"\bgama\b", r"\bmodelo\b"]),

 ("account_kyc", "Chủ thuê bao / Thủ tục", "Titularidad / Datos / Trámites",
   [r"cambio de titular", r"cambio de nombre", r"actualizar (mis )?datos", r"cambio de titularidad",
    r"duplicado de (dni|documento)", r"soy (el|la) titular pero", r"transferir la linea",
    r"cesion de linea", r"actualizacion de datos"],
   [r"\btitular", r"\bdni\b", r"documento de identidad", r"mis datos", r"\btramite"]),

 ("cancel_churn", "Hủy / Rời mạng / Portabilidad", "Cancelación / Baja / Portabilidad",
   [r"dar(me|se)? de baja", r"\bde baja\b", r"baja de (la|mi) (linea|servicio)",
    r"cancelar (mi |la |el )?(linea|servicio|plan|cuenta|contrato|numero)",
    r"anular (mi |la |el )?(linea|servicio|plan)", r"portabilidad", r"portarme", r"me porto",
    r"irme a (otro|claro|movistar|entel)", r"cambiarme de (operador|compania|empresa)",
    r"ya no quiero (la linea|el servicio|seguir)", r"retirar(me)? (la|mi) linea"],
   [r"otro operador", r"otra operadora", r"otra compania", r"me quiero ir", r"\bportar\b"]),

 ("roaming", "Roaming / Du lịch", "Roaming / Viajes",
   [r"\broaming", r"fuera del pais", r"en el extranjero", r"viaje al exterior", r"viajar a"],
   [r"\bviaje", r"\bextranjero"]),
]

# Danh mục dự phòng khi không có tín hiệu nào
FALLBACK = ("general", "Hỏi đáp chung / Khác", "Consulta general / Otros")

# ---------------------------------------------------------------------------
# 4) Cờ cắt ngang (cross-cutting flags) - độc lập với danh mục chính
# ---------------------------------------------------------------------------
COMPETITOR_RX = re.compile(
    r"(de claro\b|a claro\b|con claro\b|tengo claro\b|estoy (con|en) claro|"
    r"claro me (ofrec|da|dio)|me ofrece claro|portarme a claro|irme a claro|"
    r"\bmovistar\b|\bentel\b|\bwin\b movil|la competencia)")
COMP_WHICH = [("Claro", r"claro"), ("Movistar", r"movistar"), ("Entel", r"entel")]

NEG_SENT_RX = re.compile(
    r"(reclam|\bqueja|quejar|molest|malestar|indignad|fastidi|incomod|"
    r"pesimo|mal servicio|terrible|horrible|malisimo|"
    r"estafa|engan(\b|ar|o)|engan|cobro indebido|cobrado de mas|"
    r"muy mal\b|pesima atencion|indignante|abuso|fraude)")

REPEAT_RX = re.compile(
    r"(ya (he )?llam|es la (segunda|tercera) vez|nuevamente (llamo|me comunico)|"
    r"otra vez (llamo|estoy llamando)|vuelvo a llamar|por enesima vez|"
    r"ya me comunique|llame (ayer|antes|la semana)|sigo (llamando|sin solucion))")

CSAT_RX = re.compile(r"(encuesta|calificar (la |nuestra )?atencion|del 1 al \d|puntaje|"
                     r"como calificaria)")

CHURN_DOWNGRADE_RX = re.compile(r"(plan menor|reducir (mi )?plan|bajar de plan|reduccion de plan|"
                                r"un plan mas barato|algo mas economico)")

# --- Churn theo tầng (tách ý định rời thật khỏi việc khóa máy do mất/trộm) ---
LOSS_RX = re.compile(r"(perdida|\brobo\b|me robaron|se me perdio|se me extravio|extravi|"
                     r"por robo|por perdida|hurto|me lo robaron|equipo robado)")
# HARD: rời mạng tự nguyện rõ ràng (portabilidad / sang đối thủ)
HARD_CHURN_RX = re.compile(r"(portabilidad|portarme|me porto|\bportar\b|"
                           r"irme a (otro|claro|movistar|entel)|"
                           r"cambiarme de (operador|compania|empresa)|otro operador|otra operadora)")
# Hủy/đóng line (chỉ tính churn khi KHÔNG phải mất/trộm)
CANCEL_LINE_RX = re.compile(r"(dar(me|se)? de baja|\bde baja\b|"
                            r"cancelar (mi |la |el )?(linea|servicio|plan|cuenta|contrato)|"
                            r"anular (mi |la |el )?(linea|servicio))")
# OUTBOUND rõ ràng (đổi sang nhà mạng khác) vs INBOUND (portabilidad VÀO Bitel - KHÔNG phải churn)
OUTBOUND_RX = re.compile(r"(otro operador|otra operadora|irme a (otro|claro|movistar|entel)|"
                         r"cambiarme de (operador|compania|empresa)|"
                         r"me quiero ir a (otro|claro|movistar|entel))")
INBOUND_RX = re.compile(r"(a bitel|que (ya )?(ha|he|hemos|habia) (realizado|hecho)|"
                        r"recien (hice|hizo|hicieron)|cumplir? .{0,20}a[nñ]o.{0,20}portab|"
                        r"vine de|me pase a bitel|portarme a bitel|portar a bitel)")
PORTAB_RX = re.compile(r"(portabilidad|portarme|me porto|\bportar\b)")

def is_customer_churn(cn):
    """Ý định rời mạng OUTBOUND, suy từ LỜI KHÁCH (đã loại mất/trộm & portabilidad-vào-Bitel)."""
    if not cn.strip():
        return False
    if OUTBOUND_RX.search(cn):
        return True
    if CANCEL_LINE_RX.search(cn) and not LOSS_RX.search(cn):
        return True
    if PORTAB_RX.search(cn) and not INBOUND_RX.search(cn):
        return True
    return False

# ---------------------------------------------------------------------------
# 5) Cho điểm danh mục (presence-based: thưởng bề rộng bằng chứng, không thiên vị cuộc dài)
# ---------------------------------------------------------------------------
def compile_cat(cat):
    key, vn, es, strong, weak = cat
    return (key, vn, es,
            [re.compile(p) for p in strong],
            [re.compile(p) for p in weak])

CCATS = [compile_cat(c) for c in CATEGORIES]

def classify(clean_norm):
    scores = {}
    matched = {}
    for key, vn, es, strong, weak in CCATS:
        s = 0; hit = 0
        for rx in strong:
            if rx.search(clean_norm): s += 3; hit += 1
        for rx in weak:
            if rx.search(clean_norm): s += 1; hit += 1
        if s > 0:
            scores[key] = s; matched[key] = hit
    if not scores:
        return FALLBACK[0], [], {}
    # primary = điểm cao nhất; hoà điểm -> ưu tiên theo thứ tự CATEGORIES (cụ thể trước)
    order = {c[0]: i for i, c in enumerate(CATEGORIES)}
    primary = max(scores, key=lambda k: (scores[k], -order[k]))
    # nhãn phụ: mọi danh mục có điểm >= 3 (ít nhất 1 từ khoá mạnh) trừ primary
    tags = [k for k in scores if scores[k] >= 3]
    return primary, tags, scores

# ---------------------------------------------------------------------------
# 6) Vòng lặp chính
# ---------------------------------------------------------------------------
LABELS = {c[0]: (c[1], c[2]) for c in CATEGORIES}
LABELS[FALLBACK[0]] = (FALLBACK[1], FALLBACK[2])

PERIOD_VN = lambda p: f"{p[4:6]}/{p[:4]}"  # 202511 -> 11/2025

def duration_bucket(sec):
    if sec < 120: return "0-2 phút"
    if sec < 300: return "2-5 phút"
    if sec < 600: return "5-10 phút"
    if sec < 1200: return "10-20 phút"
    return ">20 phút"

def conf_band(c):
    if c >= 0.85: return "Cao (≥0.85)"
    if c >= 0.70: return "TB (0.70-0.85)"
    if c >= 0.50: return "Thấp (0.50-0.70)"
    return "Rất thấp (<0.50)"

rows = []
# Gom file từ nhiều nguồn, ưu tiên stt_diar_out (vai thật) — dedup theo call_id
_seen = set(); files = []
for _dir in STT_DIRS:
    for f in sorted(glob.glob(os.path.join(_dir, "*.json"))):
        cid = os.path.splitext(os.path.basename(f))[0]
        if cid in _seen:
            continue
        _seen.add(cid); files.append(f)
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    m = d.get("metadata", {}) or {}
    t = d.get("transcript", {}) or {}
    raw = t.get("text") or ""
    cn, cd = clean_text(raw)
    # LÝ DO GỌI: phân loại trên CẢ hội thoại (trừ IVR) — vì từ khóa danh mục (số tiền, tên gói)
    # thường do tư vấn viên nói. Nếu chỉ dùng lời khách sẽ rơi nhầm vào "general".
    primary, tags, scores = classify(cn)

    # CHURN / CẢM XÚC / ĐỐI THỦ: chỉ xét LỜI KHÁCH (sau khi tách người nói).
    # Ưu tiên 'turns' vai THẬT từ audio (schema 2.0); nếu không có thì dùng bộ tách văn bản.
    turns = t.get("turns")
    if turns:
        cust_raw = " ".join(x.get("text","") for x in turns if x.get("speaker") == "CLIENTE")
    else:
        cust_raw = DZ.customer_text(raw)
    cust_cn, _ = clean_text(cust_raw)
    cli_chars = len(cust_raw)
    cli_pct = round(100*cli_chars/len(raw), 1) if raw else 0

    competitor = bool(COMPETITOR_RX.search(cust_cn))
    comps = [name for name, pat in COMP_WHICH if re.search(r"\b"+pat+r"\b", cust_cn)] if competitor else []
    # 'claro' chỉ tính là đối thủ khi có ngữ cảnh
    if "Claro" in comps and not re.search(r"(de claro\b|a claro\b|con claro\b|tengo claro\b|estoy (con|en) claro|claro me (ofrec|da|dio)|me ofrece claro|portarme a claro|irme a claro)", cust_cn):
        comps = [c for c in comps if c != "Claro"]
    neg = bool(NEG_SENT_RX.search(cust_cn))
    downgrade = bool(CHURN_DOWNGRADE_RX.search(cust_cn))
    repeat = bool(REPEAT_RX.search(cn))   # hành vi gọi lại — giữ trên cả hội thoại (recall)
    csat = bool(CSAT_RX.search(cn))       # khảo sát do tư vấn viên/hệ thống mời
    loss = bool(LOSS_RX.search(cn))       # ngữ cảnh mất/trộm (thông tin)
    # CHURN INTENT: ý định rời OUTBOUND do CHÍNH KHÁCH nói (loại portabilidad-vào-Bitel & mất/trộm)
    churn_intent = is_customer_churn(cust_cn)
    # RETENTION RISK (rộng): ý định rời + nhắc đối thủ + đòi hạ gói
    retention_risk = churn_intent or bool(comps) or downgrade

    dur = float(t.get("duration_sec") or 0)
    conf = float(t.get("avg_confidence") or 0)
    period = m.get("period") or "?"
    rows.append({
        "call_id": d.get("call_id", ""),
        "phone": m.get("customer_phone", ""),
        "period": period,
        "month_vn": PERIOD_VN(period) if period.isdigit() and len(period) == 6 else period,
        "duration_sec": round(dur, 1),
        "duration_min": round(dur/60, 2),
        "duration_bucket": duration_bucket(dur),
        "confidence": round(conf, 3),
        "conf_band": conf_band(conf),
        "primary": primary,
        "primary_vn": LABELS[primary][0],
        "primary_es": LABELS[primary][1],
        "tags": "|".join(tags),
        "n_topics": len(set([primary]+tags)) if primary != "general" else len(tags),
        "competitor": int(bool(comps)),
        "competitors": "|".join(comps),
        "churn_intent": int(churn_intent),
        "retention_risk": int(retention_risk),
        "neg_sentiment": int(neg),
        "repeat_call": int(repeat),
        "csat_offered": int(csat),
        "downgrade": int(downgrade),
        "loss_theft": int(loss),
        "cliente_pct": cli_pct,
        "empty": int(not raw.strip()),
        "n_chars": len(raw),
    })

print(f"Đã xử lý {len(rows)} cuộc gọi.")

# ---------------------------------------------------------------------------
# 7) Lưu per-call CSV
# ---------------------------------------------------------------------------
import csv
csv_path = os.path.join(OUT_DIR, "calls_classified.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("→", csv_path)

# ---------------------------------------------------------------------------
# 8) Tổng hợp KPI -> aggregates.json (cho dashboard HTML + Excel)
# ---------------------------------------------------------------------------
def agg():
    n = len(rows)
    valid_dur = [r["duration_sec"] for r in rows if r["duration_sec"] > 0]
    months = sorted(set(r["period"] for r in rows))
    A = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_calls": n,
        "total_talk_hours": round(sum(valid_dur)/3600, 1),
        "aht_sec": round(sum(valid_dur)/len(valid_dur), 1),
        "aht_min": round(sum(valid_dur)/len(valid_dur)/60, 2),
        "median_min": round(sorted(valid_dur)[len(valid_dur)//2]/60, 2),
        "avg_conf": round(sum(r["confidence"] for r in rows)/n, 3),
        "empty": sum(r["empty"] for r in rows),
        "churn_n": sum(r["churn_intent"] for r in rows),
        "retention_n": sum(r["retention_risk"] for r in rows),
        "neg_n": sum(r["neg_sentiment"] for r in rows),
        "comp_n": sum(r["competitor"] for r in rows),
        "repeat_n": sum(r["repeat_call"] for r in rows),
        "csat_n": sum(r["csat_offered"] for r in rows),
        "downgrade_n": sum(r["downgrade"] for r in rows),
        "loss_n": sum(r["loss_theft"] for r in rows),
        "months": months,
        "months_vn": [PERIOD_VN(p) if p.isdigit() else p for p in months],
        "labels": LABELS,
    }
    A["churn_pct"] = round(100*A["churn_n"]/n, 1)
    A["retention_pct"] = round(100*A["retention_n"]/n, 1)
    A["neg_pct"] = round(100*A["neg_n"]/n, 1)
    A["comp_pct"] = round(100*A["comp_n"]/n, 1)
    A["csat_pct"] = round(100*A["csat_n"]/n, 1)
    A["repeat_pct"] = round(100*A["repeat_n"]/n, 1)

    # phân bố lý do gọi (primary)
    pc = Counter(r["primary"] for r in rows)
    A["primary_dist"] = [{"key": k, "vn": LABELS[k][0], "es": LABELS[k][1],
                          "n": c, "pct": round(100*c/n, 1)}
                         for k, c in pc.most_common()]
    # đa nhãn: đếm mọi chủ đề xuất hiện (primary + tags)
    tc = Counter()
    for r in rows:
        topics = set([r["primary"]] + (r["tags"].split("|") if r["tags"] else []))
        topics.discard("");
        for t in topics: tc[t] += 1
    A["topic_dist"] = [{"key": k, "vn": LABELS.get(k,(k,k))[0], "es": LABELS.get(k,(k,k))[1],
                        "n": c, "pct": round(100*c/n, 1)} for k, c in tc.most_common()]

    # xu hướng theo tháng x danh mục chính
    by_mp = defaultdict(lambda: Counter())
    vol_m = Counter(); churn_m = Counter(); neg_m = Counter(); aht_m = defaultdict(list)
    for r in rows:
        by_mp[r["period"]][r["primary"]] += 1
        vol_m[r["period"]] += 1
        churn_m[r["period"]] += r["churn_intent"]
        neg_m[r["period"]] += r["neg_sentiment"]
        if r["duration_sec"]>0: aht_m[r["period"]].append(r["duration_sec"])
    A["trend"] = {
        "months": months,
        "months_vn": A["months_vn"],
        "volume": [vol_m[p] for p in months],
        "churn": [churn_m[p] for p in months],
        "churn_pct": [round(100*churn_m[p]/vol_m[p],1) if vol_m[p] else 0 for p in months],
        "neg": [neg_m[p] for p in months],
        "neg_pct": [round(100*neg_m[p]/vol_m[p],1) if vol_m[p] else 0 for p in months],
        "aht_min": [round(sum(aht_m[p])/len(aht_m[p])/60,1) if aht_m[p] else 0 for p in months],
        "by_primary": {k: [by_mp[p].get(k,0) for p in months] for k in [c[0] for c in CATEGORIES]+["general"]},
    }
    # phân bố thời lượng & độ tin cậy
    A["dur_dist"] = [{"bucket": b, "n": c} for b, c in
                     sorted(Counter(r["duration_bucket"] for r in rows).items(),
                            key=lambda x: ["0-2 phút","2-5 phút","5-10 phút","10-20 phút",">20 phút"].index(x[0]))]
    A["conf_dist"] = [{"band": b, "n": c} for b, c in
                      Counter(r["conf_band"] for r in rows).items()]
    # đối thủ
    cw = Counter()
    for r in rows:
        for c in (r["competitors"].split("|") if r["competitors"] else []):
            if c: cw[c]+=1
    A["competitor_dist"] = [{"name": k, "n": v} for k, v in cw.most_common()]

    # AHT theo danh mục
    aht_cat = defaultdict(list)
    for r in rows:
        if r["duration_sec"]>0: aht_cat[r["primary"]].append(r["duration_sec"])
    A["aht_by_cat"] = sorted(
        [{"key":k,"vn":LABELS[k][0],"es":LABELS[k][1],"aht_min":round(sum(v)/len(v)/60,1),"n":len(v)}
         for k,v in aht_cat.items()], key=lambda x:-x["aht_min"])

    # churn theo danh mục lý do gọi (lý do nào hay đi kèm churn nhất)
    churn_by_cat = Counter(); tot_by_cat = Counter()
    for r in rows:
        tot_by_cat[r["primary"]] += 1
        if r["churn_intent"]: churn_by_cat[r["primary"]] += 1
    A["churn_by_cat"] = sorted(
        [{"key":k,"vn":LABELS[k][0],"n":churn_by_cat[k],"tot":tot_by_cat[k],
          "pct":round(100*churn_by_cat[k]/tot_by_cat[k],1) if tot_by_cat[k] else 0}
         for k in tot_by_cat], key=lambda x:-x["n"])
    return A

A = agg()
json.dump(A, open(os.path.join(OUT_DIR, "aggregates.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("→", os.path.join(OUT_DIR, "aggregates.json"))

# tóm tắt nhanh ra console
print(f"\nTỔNG QUAN: {A['total_calls']} cuộc | {A['total_talk_hours']}h | AHT {A['aht_min']} phút")
print(f"Churn risk: {A['churn_n']} ({A['churn_pct']}%) | Tiêu cực: {A['neg_n']} ({A['neg_pct']}%) | Đối thủ: {A['comp_n']} ({A['comp_pct']}%)")
print("\nTOP LÝ DO GỌI (primary):")
for x in A["primary_dist"]:
    print(f"  {x['pct']:5.1f}%  {x['n']:5d}  {x['vn']}  /  {x['es']}")
