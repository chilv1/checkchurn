# -*- coding: utf-8 -*-
"""Bộ tách vai Asesor (tư vấn viên) / Cliente (khách) bằng quy tắc ngôn ngữ TBN.
Không cần audio. Phân từng câu -> IVR / ASESOR / CLIENTE, rồi smoothing theo chuỗi.
Dùng chung cho mọi script phân tích sau khi tách."""
import re, unicodedata

def nkl(s):  # chuẩn hóa giữ độ dài (á->a) để khớp vị trí trên bản gốc
    return s.lower().translate(str.maketrans("áéíóúüñàèìòù", "aeiouunaeiou"))

# ---- IVR / hệ thống (không phải người thật) ----
IVR = [nkl(x) for x in [
 "asesores se encuentran ocupados","en breve lo atenderemos","horario de atencion de esta central",
 "lunes a domingo","seis de la manana","media noche","medianoche","realiza tus tramites de manera rapida",
 "app mibitel","con la app mibitel","descarga e ingresa","actualizar tus datos","reactivar tu linea y otras funciones",
 "sin salir de tu casa","con un solo clic","estes donde estes","este donde estes",
 "puedes visualizar informacion de tu linea","canal exclusivo de migraciones","disposiciones emitidas por",
 "estado de emergencia","planes de estudiante","no se mantendra los saldos","misma sim card",
 "cambio de plan no tiene costo","reintegro del costo del equipo","su opinion es importante",
 "invitamos a responder","breve encuesta","recibira una llamada","calificar la atencion","calificar nuestra atencion",
 "podras solicitar y ejecutar tramites","area de migraciones y cancelaciones","suspension temporal podras",
 "marque 1","marque uno","marque dos","si usted es titular","si usted no es titular",
 "la linea debe de encontrarse activa","no debe estar suspendida o bloqueada","manten tu linea activa",
 "para su atencion","no tiene dni","no se puede realizar las migraciones","por favor espere",
 "espere un momento por favor para ser atendido","sera atendido por uno de nuestros",
 "este es el canal exclusivo","mencionarle que por este medio",
]]

# ---- dấu hiệu ASESOR (tư vấn viên/Bitel) ----
ASESOR = [
 r"bienvenid[oa]", r"le saluda", r"les saluda", r"mi nombre es", r"me estoy comunicando con",
 r"con qui[eé]n (tengo|teng) el gusto", r"en qu[eé] (le )?(puedo|podemos) ayudar", r"puedo ayudarl[oa]",
 r"el n[uú]mero del cual (se comunica|llama|nos llama)", r"requiere (la )?atenci[oó]n",
 r"usted es (el|la) titular", r"es usted el titular", r"me (indica|brinda|confirma|facilita)",
 r"ind[ií]queme", r"br[ií]ndeme", r"perm[ií]tame", r"un momento por favor", r"mant[eé]ngase en (espera|l[ií]nea)",
 r"le comento", r"le informo", r"le recuerdo", r"le (puedo|podr[ií]a) ofrecer", r"contamos con",
 r"tenemos (el|la|un|los|este)", r"le (asignaron|asignamos)", r"actualmente (usted )?(cuenta|tiene)",
 r"vamos a (validar|verificar|proceder|revisar)", r"le (voy a|estoy) transfir", r"algo m[aá]s en que",
 r"gracias por comunicarse", r"validar (sus|los) datos", r"corrobor", r"cu[aá]l (ser[ií]a|es) su consulta",
 r"de acuerdo estimad", r"estimad[oa]", r"le confirmo", r"procedo a", r"verifico", r"déjeme",
 r"dejeme", r"para brindarle", r"su l[ií]nea (cuenta|tiene|presenta)", r"observo que", r"visualizo",
 r"seg[uú]n (el sistema|lo que)", r"le menciono", r"comprendo", r"entiendo su",
]

# ---- dấu hiệu CLIENTE (khách hàng) ----
CLIENTE = [
 r"\bquiero\b", r"quisiera", r"\bnecesito\b", r"\bdeseo\b", r"me gustar[ií]a", r"quer[ií]a saber",
 r"tengo un problema", r"no me funciona", r"\bno tengo\b", r"no me lleg", r"\bmi recibo\b", r"\bmi l[ií]nea\b",
 r"\bmi internet\b", r"\bmi plan\b", r"\bmi equipo\b", r"\bmi n[uú]mero\b", r"me cobr", r"\bno puedo\b",
 r"quiero saber", r"una consulta", r"lo que pasa es que", r"resulta que", r"me aparece", r"no me deja",
 r"sigo sin", r"llamo porque", r"estoy llamando", r"\bse[nñ]orita\b", r"\bjoven\b", r"\bp[oó]rque me\b",
 r"no me han", r"me dijeron", r"hace (unos )?(d[ií]as|tiempo|una semana|un mes)", r"\byo pago\b",
 r"\byo pagu", r"a m[ií] me", r"es que (yo|no|me)", r"por mi parte", r"quiero (cancelar|migrar|portar|dar de baja)",
 r"me quiero", r"\bno entiendo\b", r"o sea", r"\bdisculpe\b", r"\bayer\b",
]

A_RX = [re.compile(p) for p in ASESOR]
C_RX = [re.compile(p) for p in CLIENTE]

def is_ivr(snk): return any(b in snk for b in IVR)

def score(snk):
    a = sum(1 for rx in A_RX if rx.search(snk))
    c = sum(1 for rx in C_RX if rx.search(snk))
    return a, c

def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.?!])\s+', text or "") if s.strip()]

def diarize(text):
    """Trả về list turn: [{'speaker':'ASESOR|CLIENTE|IVR','text':...}]"""
    sents = split_sentences(text)
    labels = []
    for s in sents:
        snk = nkl(s)
        if is_ivr(snk):
            labels.append("IVR"); continue
        a, c = score(snk)
        if a > c: labels.append("ASESOR")
        elif c > a: labels.append("CLIENTE")
        else: labels.append("?")
    # mở đầu: câu chào đầu tiên thường là ASESOR
    # smoothing: điền '?' bằng người nói gần nhất đã biết (turn thường nhiều câu)
    last = "ASESOR"
    for i, l in enumerate(labels):
        if l == "?":
            # nếu câu rất ngắn (backchannel) và câu trước là ASESOR dài -> có thể là CLIENTE,
            # nhưng để an toàn: nối tiếp người nói trước (trừ IVR)
            labels[i] = last
        elif l != "IVR":
            last = l
    # gộp câu liên tiếp cùng speaker thành turn
    turns = []
    for s, l in zip(sents, labels):
        if turns and turns[-1]["speaker"] == l:
            turns[-1]["text"] += " " + s
        else:
            turns.append({"speaker": l, "text": s})
    return turns

def customer_text(text):
    """Chỉ ghép lời CLIENTE (để phân tích churn/vấn đề chính xác hơn)."""
    return " ".join(t["text"] for t in diarize(text) if t["speaker"] == "CLIENTE")

def stats(text):
    turns = diarize(text)
    from collections import Counter
    c = Counter(t["speaker"] for t in turns)
    chars = {k: 0 for k in ("ASESOR", "CLIENTE", "IVR", "?")}
    for t in turns: chars[t["speaker"]] = chars.get(t["speaker"], 0) + len(t["text"])
    return c, chars
