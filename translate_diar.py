# -*- coding: utf-8 -*-
"""Dịch transcript tách vai TBN→Việt bằng NLLB-200 (chạy GPU Metal nếu có).
Thêm 'text_vi' vào từng turn trong stt_diar_out/*.json (idempotent: bỏ qua turn đã dịch).
  python3 translate_diar.py            # dịch mọi file trong stt_diar_out/
  python3 translate_diar.py f1.json …  # dịch file cụ thể
"""
import os, sys, glob, json
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

DIR = "stt_diar_out"
MODEL = os.environ.get("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
BATCH = int(os.environ.get("NLLB_BATCH", "16"))

_M = {}
def load():
    if _M: return _M["tok"], _M["model"], _M["dev"], _M["vid"]
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(dev).eval()
    # id token tiếng Việt (tương thích nhiều phiên bản transformers)
    try:
        vid = tok.convert_tokens_to_ids("vie_Latn")
        if vid is None or vid == tok.unk_token_id:
            vid = tok.lang_code_to_id["vie_Latn"]
    except Exception:
        vid = tok.lang_code_to_id["vie_Latn"]
    _M.update(tok=tok, model=model, dev=dev, vid=vid)
    print(f"  [NLLB] {MODEL} trên {dev}")
    return tok, model, dev, vid

def translate(texts):
    """texts: list[str] tiếng TBN -> list[str] tiếng Việt."""
    import torch
    tok, model, dev, vid = load()
    tok.src_lang = "spa_Latn"
    out = []
    for i in range(0, len(texts), BATCH):
        chunk = [t if t.strip() else " " for t in texts[i:i+BATCH]]
        enc = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=400).to(dev)
        with torch.no_grad():
            gen = model.generate(**enc, forced_bos_token_id=vid, max_length=400, num_beams=2)
        out.extend(tok.batch_decode(gen, skip_special_tokens=True))
    return out

def process(path):
    d = json.load(open(path, encoding="utf-8"))
    turns = d.get("transcript", {}).get("turns", [])
    todo = [(i, t["text"]) for i, t in enumerate(turns) if t.get("text", "").strip() and "text_vi" not in t]
    if not todo:
        print(f"  bỏ qua (đã dịch): {os.path.basename(path)}"); return
    vis = translate([x[1] for x in todo])
    for (i, _), vi in zip(todo, vis):
        turns[i]["text_vi"] = vi
    d.setdefault("translation_meta", {})["model"] = MODEL
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  → {os.path.basename(path)}: dịch {len(todo)} turn")

def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(DIR, "*.json")))
    if not files:
        print(f"Không có file trong {DIR}/"); return
    print(f"Dịch TBN→Việt {len(files)} file…")
    for f in files:
        try: process(f)
        except Exception as e: print(f"  [LỖI] {os.path.basename(f)}: {e}")
    print("Xong.")

if __name__ == "__main__":
    main()
