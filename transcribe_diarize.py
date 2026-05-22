# -*- coding: utf-8 -*-
"""
Bitel — Pipeline AUDIO → Transcribe (faster-whisper) + Tách vai → JSON.
Tự dò:
  • Stereo 2 kênh tách sẵn (call center)  → tách kênh, transcribe từng kênh (chính xác nhất, không cần token).
  • Mono / stereo trộn                     → pyannote.audio tách vai (cần HF token).
Gán vai ASESOR (tư vấn viên) / CLIENTE (khách) bằng dấu hiệu câu chào/script.
Lưu stt_diar_out/<id>.json — schema 2.0, tương thích analyze_calls.py + có 'turns' vai thật.

Dùng:
  python3 transcribe_diarize.py                 # xử lý mọi file trong audio_in/
  python3 transcribe_diarize.py path/to/file.mp3  # 1 file
"""
import os, sys, re, glob, json, subprocess, unicodedata, shutil
# Chống segfault do xung đột OpenMP (conda ↔ torch) trên macOS — phải đặt TRƯỚC khi import numpy/torch
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
from datetime import datetime, timezone

AUDIO_IN  = "audio_in"
OUT_DIR   = "stt_diar_out"
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "large-v3-turbo")  # khớp STT gốc; fallback large-v3
LANG = "es"
STEREO_CORR_THRESHOLD = 0.95   # >ngưỡng = 2 kênh giống nhau (mono nhân đôi) -> coi là mono
os.makedirs(OUT_DIR, exist_ok=True)

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

# ---------------------------------------------------------------------------
# Audio I/O (ffmpeg decode → PCM float32, giữ số kênh)
# ---------------------------------------------------------------------------
def ffprobe_streams(path):
    try:
        out = subprocess.run(["ffprobe","-v","quiet","-print_format","json","-show_streams",path],
                             capture_output=True, text=True).stdout
        return json.loads(out).get("streams", [])
    except Exception:
        return []

def load_audio(path, sr=16000):
    """Trả về (samples float32 [n, ch], sr, n_channels). Dùng ffmpeg để giải mã mọi định dạng."""
    import numpy as np
    # số kênh gốc
    ch = 1
    for s in ffprobe_streams(path):
        if s.get("codec_type") == "audio":
            ch = int(s.get("channels", 1)); break
    cmd = ["ffmpeg","-v","quiet","-i",path,"-f","f32le","-acodec","pcm_f32le","-ar",str(sr),"-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    if ch > 1:
        a = a.reshape(-1, ch)
    else:
        a = a.reshape(-1, 1)
    return a, sr, ch

def detect_separation(a):
    """a: [n, ch]. Trả 'stereo-split' nếu 2 kênh nội dung KHÁC nhau, ngược lại 'mono'."""
    import numpy as np
    if a.shape[1] < 2:
        return "mono"
    L, R = a[:,0], a[:,1]
    n = min(len(L), len(R))
    if n == 0: return "mono"
    L, R = L[:n], R[:n]
    # tương quan chuẩn hóa
    Ls, Rs = L - L.mean(), R - R.mean()
    denom = (np.sqrt((Ls**2).sum()) * np.sqrt((Rs**2).sum())) or 1e-9
    corr = float((Ls*Rs).sum() / denom)
    # cũng kiểm tra mỗi kênh có năng lượng riêng (không phải 1 kênh câm)
    eL, eR = float((L**2).mean()), float((R**2).mean())
    if eL < 1e-7 or eR < 1e-7:
        return "mono"   # 1 kênh câm -> coi như mono
    return "mono" if corr > STEREO_CORR_THRESHOLD else "stereo-split"

# ---------------------------------------------------------------------------
# ASR — 2 engine: mlx-whisper (GPU Metal M4, MẶC ĐỊNH) | faster-whisper (CPU, fallback)
# ---------------------------------------------------------------------------
WHISPER_ENGINE = os.environ.get("WHISPER_ENGINE", "mlx")   # 'mlx' = GPU; 'faster' = CPU
MLX_MODEL = os.environ.get("MLX_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")

_MODEL = None
def get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        try:
            _MODEL = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        except Exception:
            _MODEL = WhisperModel("large-v3", device="cpu", compute_type="int8")
    return _MODEL

def asr_segments(samples_mono, want_words=False):
    """samples_mono float32 1-D @16k → list segment {start,end,text,conf[,words]}.
    Chạy GPU qua mlx-whisper nếu WHISPER_ENGINE=mlx, ngược lại faster-whisper CPU."""
    import numpy as np
    audio = np.ascontiguousarray(samples_mono.astype(np.float32))
    if WHISPER_ENGINE == "mlx":
        import mlx_whisper
        r = mlx_whisper.transcribe(audio, path_or_hf_repo=MLX_MODEL, language=LANG,
                                   word_timestamps=want_words, verbose=False)
        out = []
        for s in r.get("segments", []):
            seg = {"start": round(float(s["start"]), 2), "end": round(float(s["end"]), 2),
                   "text": (s.get("text") or "").strip(),
                   "conf": round(float(np.exp(s.get("avg_logprob", -0.5))), 3)}
            if want_words:
                seg["words"] = [{"start": float(w["start"]), "end": float(w["end"]),
                                 "word": w["word"]} for w in s.get("words", []) if w.get("start") is not None]
            out.append(seg)
        return out
    # faster-whisper (CPU)
    model = get_model()
    segs, _info = model.transcribe(audio, language=LANG, vad_filter=True,
                                   word_timestamps=want_words, beam_size=5)
    out = []
    for s in segs:
        seg = {"start": round(s.start, 2), "end": round(s.end, 2),
               "text": s.text.strip(), "conf": round(float(np.exp(s.avg_logprob)), 3)}
        if want_words:
            seg["words"] = [{"start": w.start, "end": w.end, "word": w.word} for w in (s.words or [])]
        out.append(seg)
    return out

def transcribe_array(samples_mono):
    return asr_segments(samples_mono, want_words=False)

# ---------------------------------------------------------------------------
# Tách vai
# ---------------------------------------------------------------------------
# dấu hiệu TƯ VẤN VIÊN (mở rộng — bắt cả lối nói lịch sự/nghiệp vụ phổ biến)
AGENT_CUES = re.compile(r"(bienvenid|mi nombre es|le saluda|les saluda|"
                        r"(en que|como) (le |te )?(puedo|podemos) ayudar|puedo ayudarl|"
                        r"con quien tengo el gusto|requiere (la )?atencion|gracias por comunicarse|"
                        r"el numero del cual|le comento|le informo|le recuerdo|coment[ae]me|"
                        r"verificar en el sistema|en el sistema|permitame|un momento por favor|"
                        r"le puedo ofrecer|su (plan|recibo|linea) (es|tiene|cuenta)|vamos a (verificar|validar|revisar)|"
                        r"se encuentra en linea|brindeme|indiqueme)")
# dấu hiệu KHÁCH (nhu cầu ngôi thứ nhất)
CLIENT_CUES = re.compile(r"(quiero|quisiera|necesito|lo que pasa es|mi recibo|mi linea|mi plan|"
                         r"me sale|me cobr|no me funciona|quer[ií]a saber|por que (me|tengo)|una consulta)")

def assign_roles(seg_by_spk):
    """seg_by_spk: {spk_id: [segments]}. Trả map spk_id -> 'ASESOR'|'CLIENTE'|'IVR'.
    ASESOR = cụm có nhiều dấu hiệu nghiệp vụ nhất (đếm trên TOÀN BỘ câu). Bỏ qua 'IVR'."""
    spk_real = [s for s in seg_by_spk if s != "IVR"]
    if not spk_real:
        return {s: "IVR" for s in seg_by_spk}
    if len(spk_real) == 1:
        return {spk_real[0]: "ASESOR", "IVR": "IVR"} if "IVR" in seg_by_spk else {spk_real[0]: "ASESOR"}
    net = {}; first_start = {}
    for spk in spk_real:
        txt = strip_accents(" ".join(s["text"] for s in seg_by_spk[spk]).lower())
        net[spk] = len(AGENT_CUES.findall(txt)) - len(CLIENT_CUES.findall(txt))  # thiên agent
        first_start[spk] = min((s["start"] for s in seg_by_spk[spk]), default=1e9)
    # ASESOR = điểm thiên-agent cao nhất; hoà -> người nói TRƯỚC (agent thường chào đầu tiên)
    agent = max(spk_real, key=lambda s: (net[s], -first_start[s]))
    roles = {spk: ("ASESOR" if spk == agent else "CLIENTE") for spk in spk_real}
    roles["IVR"] = "IVR"
    return roles

def stereo_pipeline(a, sr):
    """Tách kênh: mỗi kênh = 1 người. Transcribe riêng."""
    seg_by_spk = {}
    for ch in range(min(a.shape[1], 2)):
        segs = transcribe_array(a[:, ch])
        for s in segs: s["spk"] = f"CH{ch}"
        seg_by_spk[f"CH{ch}"] = segs
    return seg_by_spk, "stereo-split"

_ENCODER = None
def get_encoder():
    """SpeechBrain ECAPA-TDNN — embedding giọng nói (model công khai, KHÔNG cần token)."""
    global _ENCODER
    if _ENCODER is None:
        from speechbrain.inference.speaker import EncoderClassifier
        _ENCODER = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="models/ecapa")
    return _ENCODER

def _ivr_text(txt):
    import diarize as DZ
    return DZ.is_ivr(DZ.nkl(txt))

def embed_pipeline(a, sr):
    """MONO không-token: chia cửa sổ MỊN theo từ → loại IVR → nhúng ECAPA → phân cụm 2 người."""
    import numpy as np, torch
    from sklearn.cluster import AgglomerativeClustering
    mono = (a.mean(axis=1) if a.ndim > 1 else a).astype("float32")
    segs0 = asr_segments(mono, want_words=True)
    # chia mỗi segment thành cửa sổ ~tối đa 6s, ngắt tại khoảng lặng >0.6s -> sub đồng nhất 1 người hơn
    subs = []
    for seg in segs0:
        words = seg.get("words") or []
        if not words:
            subs.append({"start": seg["start"], "end": seg["end"], "text": seg["text"], "conf": seg.get("conf",0.9)}); continue
        cur = []
        for w in words:
            if cur and (w["start"] - cur[-1]["end"] > 0.6 or w["end"] - cur[0]["start"] > 6.0):
                subs.append({"start": cur[0]["start"], "end": cur[-1]["end"],
                             "text": "".join(x["word"] for x in cur).strip(), "conf": 0.9})
                cur = []
            cur.append(w)
        if cur:
            subs.append({"start": cur[0]["start"], "end": cur[-1]["end"],
                         "text": "".join(x["word"] for x in cur).strip(), "conf": 0.9})
    if not subs:
        return {"S0": []}, "embed-cluster"
    # đánh dấu IVR (không đưa vào phân cụm để không lấn cụm)
    for s in subs:
        s["ivr"] = _ivr_text(s["text"])
    enc = get_encoder(); embs = {}
    for i, s in enumerate(subs):
        if s["ivr"]:
            continue
        clip = mono[int(s["start"]*sr):int(s["end"]*sr)]
        if len(clip) < int(0.8*sr):
            continue
        with torch.no_grad():
            embs[i] = enc.encode_batch(torch.tensor(clip).unsqueeze(0).float()).squeeze().cpu().numpy()
    if len(embs) >= 2:
        idx = sorted(embs); X = np.stack([embs[i] for i in idx])
        X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
        lab = AgglomerativeClustering(n_clusters=2, metric="cosine", linkage="average").fit_predict(X)
        labmap = {idx[k]: f"S{int(lab[k])}" for k in range(len(idx))}
    else:
        labmap = {i: "S0" for i in embs}
    # gán nhãn: IVR -> 'IVR'; có embedding -> cụm; còn lại -> nhãn (không IVR) gần nhất trước
    seg_by_spk = {}; last = "S0"
    for i, s in enumerate(subs):
        if s["ivr"]:
            spk = "IVR"
        elif i in labmap:
            spk = labmap[i]; last = spk
        else:
            spk = last
        s["spk"] = spk
        seg_by_spk.setdefault(spk, []).append(s)
    return seg_by_spk, "embed-cluster"

def mono_pipeline(a, sr, path):
    """Mono: transcribe toàn bộ + pyannote diarization, gán segment theo overlap."""
    mono = a.mean(axis=1)
    segs = transcribe_array(mono)
    # pyannote
    try:
        from pyannote.audio import Pipeline
        import torch, numpy as np
        hf = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        model_id = os.environ.get("PYANNOTE_MODEL", "pyannote/speaker-diarization-community-1")
        try:
            pipe = Pipeline.from_pretrained(model_id, token=hf)        # pyannote 4.x
        except TypeError:
            pipe = Pipeline.from_pretrained(model_id, use_auth_token=hf)  # pyannote 3.x
        dev = os.environ.get("PYANNOTE_DEVICE", "mps")  # GPU Metal (nhanh ~18x); đặt cpu nếu gặp lỗi
        if dev == "mps" and torch.backends.mps.is_available():
            pipe.to(torch.device("mps"))
        # Truyền waveform đã giải mã (tránh pyannote tự đọc file -> xung đột lib av/ffmpeg gây segfault)
        wav = torch.from_numpy(np.ascontiguousarray(mono)).unsqueeze(0).float()  # [1, T] @ sr
        dia = pipe({"waveform": wav, "sample_rate": sr}, num_speakers=2)
        # pyannote 4.x trả về DiarizeOutput (có .exclusive_speaker_diarization không chồng tiếng);
        # v3 trả về Annotation trực tiếp.
        ann = getattr(dia, "exclusive_speaker_diarization", None)
        if ann is None: ann = getattr(dia, "speaker_diarization", None)
        if ann is None: ann = dia
        turns = [(seg.start, seg.end, spk) for seg, _, spk in ann.itertracks(yield_label=True)]
    except Exception as e:
        print(f"  [!] pyannote không chạy được ({e}). Gán tất cả về 1 speaker — cần HF token + cài pyannote.")
        for s in segs: s["spk"] = "SPK0"
        return {"SPK0": segs}, "mono-nodiar"
    # gán mỗi segment cho speaker overlap nhiều nhất
    def overlap_spk(s):
        best, bov = "SPK0", 0
        for st, en, spk in turns:
            ov = max(0, min(s["end"], en) - max(s["start"], st))
            if ov > bov: bov, best = ov, spk
        return best
    seg_by_spk = {}
    for s in segs:
        s["spk"] = overlap_spk(s)
        seg_by_spk.setdefault(s["spk"], []).append(s)
    return seg_by_spk, "pyannote"

# ---------------------------------------------------------------------------
# Xử lý 1 file
# ---------------------------------------------------------------------------
def parse_meta(fname):
    base = os.path.basename(fname)
    stem = re.sub(r"\.(mp3|wav|m4a|ogg|flac)$", "", base, flags=re.I)
    mp = re.match(r"(\d{6,})", base)
    phone = mp.group(1) if mp else ""
    mper = re.match(r"\d+_(\d{6})\b", base)
    period = mper.group(1) if mper else ""
    # tên tư vấn viên: token chữ đầu tiên (bỏ qua mã 'cpc'/'vtp'…), vd 'enriquear'
    agent = ""
    for tk in stem.split("_")[1:]:
        if re.search(r"[a-zA-Z]", tk) and tk.lower() not in ("cpc", "vtp", "vt", "in", "out", "rec"):
            agent = tk; break
    return phone, period, agent, stem

def process(path, method="auto", out_dir=OUT_DIR):
    import numpy as np
    phone, period, agent, stem = parse_meta(path)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, stem + ".json")
    if os.path.exists(out_path):
        print(f"  bỏ qua (đã có): {os.path.basename(path)}"); return out_path
    a, sr, ch = load_audio(path)
    dur = round(a.shape[0]/sr, 2)
    mode = detect_separation(a)
    print(f"  {os.path.basename(path)} | {ch} kênh | {dur}s | chế độ: {mode} | pp: {method}")
    if mode == "stereo-split":
        seg_by_spk, method = stereo_pipeline(a, sr)
    elif method == "pyannote":
        seg_by_spk, method = mono_pipeline(a, sr, path)
    else:
        seg_by_spk, method = embed_pipeline(a, sr)
    roles = assign_roles(seg_by_spk)
    # gộp tất cả segment theo thời gian, gán vai
    allsegs = []
    for spk, segs in seg_by_spk.items():
        for s in segs:
            allsegs.append({**s, "speaker": roles.get(spk, "CLIENTE")})
    allsegs.sort(key=lambda s: s["start"])
    # gắn nhãn IVR cho câu boilerplate (khảo sát/giữ máy/quảng cáo) — đồng nhất mọi phương pháp
    import diarize as _DZ
    for s in allsegs:
        if _DZ.is_ivr(_DZ.nkl(s.get("text", ""))):
            s["speaker"] = "IVR"
    # gộp segment liên tiếp cùng vai -> turns
    turns = []
    for s in allsegs:
        if turns and turns[-1]["speaker"] == s["speaker"]:
            turns[-1]["text"] += " " + s["text"]; turns[-1]["end"] = s["end"]
        else:
            turns.append({"speaker": s["speaker"], "start": s["start"], "end": s["end"], "text": s["text"]})
    full_text = " ".join(s["text"] for s in allsegs)
    # lọc nan/inf để avg_confidence không bị nan
    confs = [c for c in (s.get("conf") for s in allsegs)
             if isinstance(c, (int, float)) and c == c and abs(c) != float("inf")]
    doc = {
        "schema_version": "2.0",
        "call_id": stem,
        "file_name": os.path.basename(path),
        "metadata": {"period": period, "customer_phone": phone, "agent_code": agent},
        "transcript": {
            "text": full_text,
            "language": LANG,
            "duration_sec": dur,
            "avg_confidence": round(sum(confs)/len(confs), 3) if confs else None,
            "turns": [{"speaker": t["speaker"], "start": t["start"], "end": t["end"], "text": t["text"]} for t in turns],
        },
        "diar_meta": {"method": method, "channels": ch,
                      "n_speakers": len(set(roles.values())),
                      "asesor_turns": sum(1 for t in turns if t["speaker"]=="ASESOR"),
                      "cliente_turns": sum(1 for t in turns if t["speaker"]=="CLIENTE")},
        "stt_meta": {"model": MODEL_SIZE, "engine": "faster-whisper",
                     "transcribed_at": datetime.now(timezone.utc).isoformat()},
    }
    json.dump(doc, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"    → {out_path} | {len(turns)} turns ({doc['diar_meta']['asesor_turns']} asesor / {doc['diar_meta']['cliente_turns']} cliente)")
    return out_path

def main():
    if not shutil.which("ffmpeg"):
        print("LỖI: chưa có ffmpeg. Cài: brew install ffmpeg"); sys.exit(1)
    argv = sys.argv[1:]
    method = "auto"; out_dir = OUT_DIR; rest = []
    i = 0
    while i < len(argv):
        if argv[i] == "--method": method = argv[i+1]; i += 2
        elif argv[i] == "--out": out_dir = argv[i+1]; i += 2
        else: rest.append(argv[i]); i += 1
    if rest:
        files = rest
    else:
        os.makedirs(AUDIO_IN, exist_ok=True)
        files = sorted(sum([glob.glob(os.path.join(AUDIO_IN, "*."+e)) for e in ("mp3","wav","m4a","ogg","flac","MP3","WAV")], []))
    if not files:
        print(f"Không thấy file audio. Thả .mp3/.wav vào thư mục {AUDIO_IN}/ rồi chạy lại."); return
    print(f"Xử lý {len(files)} file audio | model={MODEL_SIZE} | pp={method} | out={out_dir}")
    for f in files:
        try: process(f, method=method, out_dir=out_dir)
        except Exception as e:
            print(f"  [LỖI] {os.path.basename(f)}: {e}")
    print("Xong.")

if __name__ == "__main__":
    main()
