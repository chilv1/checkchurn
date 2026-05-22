# checkchurn — Pipeline phân tích Churn & Thu cước · Bitel Perú

Hệ thống phân tích call center: từ transcript STT (tiếng Tây Ban Nha) hoặc audio cuộc gọi → phân loại lý do, đo ý định rời mạng (churn), dựng dashboard HTML / Excel / báo cáo Word.

> **Lưu ý quyền riêng tư:** repo này CHỈ chứa CODE. Dữ liệu khách hàng (ghi âm, transcript có SĐT, dashboard, token) **đã được loại** qua `.gitignore` để tránh lộ PII. Xem mục [Bảo mật](#bảo-mật--quyền-riêng-tư).

---

## Tính năng

- **Phân loại lý do gọi** đa nhãn (12 danh mục tiếng TBN) trên transcript.
- **Đo ý định rời mạng (churn)** quy về **lời khách** sau khi tách vai — loại bỏ false positive do tư vấn viên đọc thủ tục và "portabilidad vào Bitel".
- **Pipeline audio chạy GPU** trên Apple Silicon: `mlx-whisper` ASR (~27× thời gian thực) + `pyannote.audio` tách vai.
- **Dịch TBN → Việt** từng lượt thoại bằng NLLB-200 (chạy GPU cục bộ, không cần API).
- **Sản phẩm**: dashboard HTML tương tác, file Excel KPI, báo cáo .docx, danh sách Top 100 thuê bao rủi ro, audit nguyên văn có tô màu trigger.

---

## Yêu cầu hệ thống

- **Khuyến nghị:** macOS Apple Silicon (M1/M2/M3/M4) — bật được GPU Metal.
- Cũng chạy trên Linux/Intel (chỉ CPU, chậm hơn ~18× cho ASR).
- Python ≥ 3.10 · Node.js ≥ 18 · ffmpeg · ~6 GB ổ đĩa cho model.

---

## Cài đặt máy mới

### 1. Clone repo

```bash
git clone git@github.com:chilv1/checkchurn.git
cd checkchurn
```

### 2. Cài công cụ hệ thống

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install -y ffmpeg
```

### 3. Cài Python deps

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Trên máy không phải Apple Silicon, dòng `mlx-whisper` trong requirements.txt sẽ tự bỏ qua (sẽ dùng `faster-whisper` chạy CPU).

### 4. Cài Node deps (cho báo cáo .docx)

```bash
npm install
```

### 5. *(Tùy chọn — chỉ cần nếu xử lý audio MONO)* — HuggingFace token cho pyannote

Pyannote dùng model có kiểm soát truy cập, cần token + đồng ý điều khoản:

1. Đăng ký tài khoản miễn phí: https://huggingface.co/join
2. Tạo Access Token (loại **Read**): https://huggingface.co/settings/tokens
3. Mở 3 trang sau, đăng nhập, bấm **"Agree and access repository"**:
   - https://huggingface.co/pyannote/segmentation-3.0
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/speaker-diarization-community-1
4. Lưu token vào file local (đã được `.gitignore`):
   ```bash
   echo "hf_..." > .hf_token
   chmod 600 .hf_token
   ```

> Nếu audio stereo 2 kênh tách sẵn (agent / khách riêng kênh) thì **không cần** token — pipeline tự dò và tách kênh.

---

## Đặt dữ liệu

Repo không chứa dữ liệu khách hàng. Sau khi clone, tự đặt:

| Thư mục | Nội dung |
|---|---|
| `audio_in/` | File audio `.mp3`/`.wav` cuộc gọi |
| `stt_out/` | Transcript JSON cũ (schema 1.0) — nếu có |

Pipeline tự tạo các thư mục output: `stt_diar_out/`, `output/`.

---

## Cách dùng

### Quy trình A — Từ transcript có sẵn

```bash
python3 analyze_calls.py          # phân loại + tính KPI -> output/calls_classified.csv, aggregates.json
python3 generate_charts.py        # biểu đồ matplotlib
python3 build_dashboard.py        # dashboard HTML tổng -> output/dashboard.html
python3 build_excel.py            # Excel 6 sheet -> output/dashboard_churn_bitel.xlsx
python3 build_top100_billing.py   # Top 100 thuê bao rủi ro
python3 build_audit_html.py       # Audit nguyên văn + bôi vàng trigger
node    build_report.js           # Báo cáo .docx phân tích hành vi
```

### Quy trình B — Từ audio (mới)

```bash
export HF_TOKEN=$(cat .hf_token)        # nếu là mono

# 1) ASR + tách vai (GPU Metal trên Apple Silicon, CPU trên máy khác)
python3 transcribe_diarize.py

# 2) Dịch TBN → Việt từng lượt thoại
python3 translate_diar.py

# 3) Phân tích (tự đọc cả stt_diar_out/ và stt_out/)
python3 analyze_calls.py
python3 audio_report_data.py            # gom dữ liệu cho báo cáo audio
python3 build_audio_dashboard.py        # dashboard riêng cho nhóm audio (song ngữ ES/VI)
node    build_audio_report.js           # báo cáo .docx riêng cho nhóm audio
```

### Biến môi trường

| Biến | Mặc định | Mục đích |
|---|---|---|
| `WHISPER_ENGINE` | `mlx` | `mlx` = GPU (Apple Silicon), `faster` = CPU |
| `PYANNOTE_DEVICE` | `mps` | `mps` = GPU Metal, `cpu` = ép CPU |
| `HF_TOKEN` | (lấy từ `.hf_token`) | Cần cho pyannote |
| `MLX_WHISPER_MODEL` | `mlx-community/whisper-large-v3-turbo` | Model ASR GPU |
| `WHISPER_MODEL` | `large-v3-turbo` | Model ASR CPU |
| `NLLB_MODEL` | `facebook/nllb-200-distilled-600M` | Model dịch |
| `NLLB_BATCH` | `16` | Batch size dịch |

Ví dụ chạy CPU-only (không Apple Silicon):
```bash
WHISPER_ENGINE=faster PYANNOTE_DEVICE=cpu python3 transcribe_diarize.py
```

---

## Output

| File | Mô tả |
|---|---|
| `output/dashboard.html` | Dashboard chính (tổng) — phân tích inbound (khách gọi vào) |
| `output/audio_dashboard.html` | Dashboard nhóm audio — chiến dịch gọi RA thu cước |
| `output/BaoCao_HanhVi_KhachHang_Bitel.docx` | Báo cáo Word phân tích hành vi |
| `output/BaoCao_ThuCuoc_Audio_Pilot.docx` | Báo cáo Word nhóm audio |
| `output/dashboard_churn_bitel.xlsx` | Excel 6 sheet KPI + dữ liệu |
| `output/Top100_HoaDon_NguyCoRoiMang.xlsx` | Top 100 thuê bao hóa đơn rủi ro |
| `output/Audit_Top100_NguyenVan.html` | Audit nguyên văn + bôi vàng trigger |
| `stt_diar_out/<call_id>.json` | Transcript đã tách vai (schema 2.0) |

---

## Kiến trúc

```
        audio_in/*.mp3                stt_out/*.json (transcript cũ)
              │                              │
              ▼                              │
    transcribe_diarize.py                    │
       (mlx-whisper GPU                      │
        + pyannote tách vai)                 │
              │                              │
              ▼                              │
    stt_diar_out/*.json                      │
       (turns có vai thật)                   │
              │                              │
              ├── translate_diar.py          │
              │   (NLLB ES→VI)               │
              │                              │
              └──────────────┬───────────────┘
                             ▼
                      analyze_calls.py
                  (phân loại + churn intent)
                             │
                ┌────────────┼────────────┬────────────┬─────────────┐
                ▼            ▼            ▼            ▼             ▼
        build_dashboard  build_excel  build_top100  build_audit  build_report
                          (xlsxwriter) _billing      _html         (docx-js)
                                                                  ▲
                                              audio_report_data → build_audio_*
```

---

## Bảo mật & quyền riêng tư

`.gitignore` bảo vệ:

- **Bí mật:** `.hf_token`, `.phone_map.local.json`
- **PII khách hàng:** `audio_in/`, `stt_out/`, `stt_diar_out/`, `output/`, `reports/`
- **File lớn / tái tạo được:** `node_modules/`, `models/`, `__pycache__/`

20 số điện thoại khách hàng trong `build_audio_dashboard.py` và `audio_report_data.py` đã được ẩn danh thành `CALL_01…CALL_20` trước khi push. Mapping SĐT thật được giữ ở `.phone_map.local.json` (local, gitignored).

Khi commit mới, **luôn kiểm tra `git status` trước** để chắc không lọt file PII / secret.

---

## Phương pháp tóm tắt

- **ASR (chuyển thoại → văn bản):** `faster-whisper` (CPU) hoặc `mlx-whisper` (GPU Apple Silicon), model `large-v3-turbo`, ngôn ngữ `es` (Tây Ban Nha).
- **Tách vai:** `pyannote/speaker-diarization-community-1` cho audio mono. Stereo tách kênh tự động.
- **Phân loại lý do gọi:** quy tắc từ khóa tiếng TBN, đa nhãn, lọc câu IVR.
- **Churn (ý định rời mạng):** chỉ tính trên lời KHÁCH; loại trừ "portabilidad VÀO Bitel" và khóa máy do mất/trộm.
- **Dịch TBN→Việt:** `facebook/nllb-200-distilled-600M`, batch trên GPU.

---

## Khắc phục sự cố

| Lỗi | Cách xử lý |
|---|---|
| `ffmpeg not found` | `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux) |
| `403 Client Error` khi load pyannote | Chưa đồng ý điều khoản 3 model HuggingFace — xem bước 5 cài đặt |
| Segfault (exit 139) khi chạy pyannote | Đã có fix trong `transcribe_diarize.py` (KMP_DUPLICATE_LIB_OK). Nếu vẫn lỗi, đặt `PYANNOTE_DEVICE=cpu` |
| `mlx-whisper` install lỗi | Chỉ cài được trên Apple Silicon. Trên máy khác đặt `WHISPER_ENGINE=faster` (CPU) |
| Drill-down dashboard hiện `CALL_xx` thay vì SĐT | Đúng, đó là phiên bản ẩn danh để push GitHub. SĐT thật ở `.phone_map.local.json` |

---

## Tác giả

Bitel Perú · Customer Care Analytics  
Đối chiếu nghiệp vụ trước khi ra quyết định — đây là ước lượng tự động.
