# -*- coding: utf-8 -*-
"""Vẽ biểu đồ chất lượng báo cáo (matplotlib) để nhúng vào .docx. Nhãn tiếng Việt."""
import json, csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from collections import Counter

os.makedirs("output/charts", exist_ok=True)
A = json.load(open("output/aggregates.json", encoding="utf-8"))
rows = list(csv.DictReader(open("output/calls_classified.csv", encoding="utf-8-sig")))
N = len(rows)
def b(r, k): return r[k] == "1"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#94a3b8", "axes.labelcolor": "#0f172a",
    "text.color": "#0f172a", "xtick.color": "#475569", "ytick.color": "#475569",
    "figure.dpi": 150,
})
AMBER="#FDC700"; INK="#0f172a"; RED="#e11d48"; BLU="#2563eb"; ORG="#ea580c"; GRN="#059669"; SLATE="#64748b"
PAL=["#FDC700","#2563eb","#059669","#e11d48","#7c3aed","#ea580c","#0891b2","#db2777","#65a30d","#9333ea"]

def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"output/charts/{name}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("→ charts/"+name+".png")

# 1) Bản đồ nhu cầu liên hệ — lý do gọi
d = [x for x in A["primary_dist"] if x["pct"] >= 0.5][::-1]
fig, ax = plt.subplots(figsize=(8, 4.4))
bars = ax.barh([x["vn"] for x in d], [x["pct"] for x in d],
               color=[PAL[i % len(PAL)] for i in range(len(d))][::-1])
for x, bar in zip(d, bars):
    ax.text(bar.get_width()+0.4, bar.get_y()+bar.get_height()/2, f"{x['pct']}%",
            va="center", fontsize=9.5, fontweight="bold")
ax.set_xlabel("% trên tổng cuộc gọi"); ax.set_xlim(0, max(x["pct"] for x in d)*1.15)
ax.set_title("Lý do khách hàng gọi tổng đài (nhãn chính)", fontweight="bold", fontsize=13, pad=12)
save(fig, "reason_dist")

# 2) Diễn biến churn theo tháng (cột volume + đường churn%)
m = A["trend"]["months_vn"]; vol = A["trend"]["volume"]; ch = A["trend"]["churn_pct"]
fig, ax1 = plt.subplots(figsize=(8, 4.2))
ax1.bar(m, vol, color="#cbd5e1", width=0.6, label="Số cuộc gọi")
ax1.set_ylabel("Số cuộc gọi", color=SLATE)
ax1.set_ylim(0, max(vol)*1.25)
for i, v in enumerate(vol): ax1.text(i, v+20, f"{v:,}".replace(",", "."), ha="center", fontsize=9, color=SLATE)
ax2 = ax1.twinx(); ax2.spines["top"].set_visible(False)
ax2.plot(m, ch, color=RED, marker="o", linewidth=2.6, markersize=7, label="% ý định rời mạng")
ax2.set_ylabel("% ý định rời mạng (churn)", color=RED)
ax2.set_ylim(0, max(ch)*1.3); ax2.tick_params(axis="y", colors=RED)
for i, v in enumerate(ch): ax2.text(i, v+1.1, f"{v}%", ha="center", fontsize=9.5, fontweight="bold", color=RED)
ax1.set_title("Sản lượng cuộc gọi giảm nhưng tỷ lệ ý định rời mạng TĂNG đều",
              fontweight="bold", fontsize=12.5, pad=12)
save(fig, "churn_trend")

# 3) Lift — xác suất churn theo tín hiệu hành vi
base = round(100*sum(1 for r in rows if b(r, "churn_intent"))/N, 1)
sigs = [("Nhắc đối thủ", "competitor"), ("Đòi hạ gói", "downgrade"),
        ("Gọi lại nhiều lần", "repeat_call"), ("Cảm xúc tiêu cực", "neg_sentiment")]
labs = ["Nền chung\n(tất cả cuộc gọi)"]; vals = [base]; cols = [SLATE]
for lab, k in sigs:
    sub = [r for r in rows if b(r, k)]
    cr = round(100*sum(1 for r in sub if b(r, "churn_intent"))/len(sub), 1)
    labs.append(f"{lab}\n(n={len(sub)})"); vals.append(cr)
    cols.append(RED if cr >= 45 else (ORG if cr >= 35 else AMBER))
fig, ax = plt.subplots(figsize=(8, 4.2))
bars = ax.bar(labs, vals, color=cols, width=0.62)
for bar, v in zip(bars, vals):
    ax.text(bar.get_x()+bar.get_width()/2, v+1, f"{v}%", ha="center", fontweight="bold", fontsize=10.5)
ax.axhline(base, color=SLATE, ls="--", lw=1)
ax.text(len(labs)-0.5, base+0.5, f"nền {base}%", ha="right", color=SLATE, fontsize=8.5)
ax.set_ylabel("% có ý định rời mạng"); ax.set_ylim(0, max(vals)*1.2)
ax.set_title("Tín hiệu hành vi nào dự báo rời mạng mạnh nhất?", fontweight="bold", fontsize=13, pad=12)
save(fig, "churn_lift")

# 4) Churn theo lý do gọi (điểm rò rỉ)
cc = sorted([d for d in A["churn_by_cat"] if d["tot"] >= 40 and d["key"] not in ("cancel_churn", "general")],
            key=lambda x: x["pct"])
fig, ax = plt.subplots(figsize=(8, 4))
cols = [RED if x["pct"] >= 30 else (ORG if x["pct"] >= 20 else AMBER) for x in cc]
bars = ax.barh([x["vn"] for x in cc], [x["pct"] for x in cc], color=cols)
for x, bar in zip(cc, bars):
    ax.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
            f"{x['pct']}%  ({x['n']}/{x['tot']})", va="center", fontsize=9)
ax.set_xlabel("% cuộc gọi loại này có ý định rời mạng")
ax.set_xlim(0, max(x["pct"] for x in cc)*1.25)
ax.set_title("Lý do gọi nào làm khách rời mạng nhiều nhất?", fontweight="bold", fontsize=13, pad=12)
save(fig, "churn_by_reason")

# 5) Đối thủ
comp = A["competitor_dist"]
fig, ax = plt.subplots(figsize=(5.2, 4.2))
w, _, at = ax.pie([c["n"] for c in comp], labels=[c["name"] for c in comp],
                  autopct=lambda p: f"{p:.0f}%", colors=[RED, BLU, GRN, "#7c3aed"][:len(comp)],
                  startangle=90, wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
                  textprops=dict(fontsize=11, fontweight="bold"))
for t in at: t.set_color("white"); t.set_fontsize(11)
ax.text(0, 0, f"{sum(c['n'] for c in comp)}\nlượt nhắc", ha="center", va="center", fontsize=12, fontweight="bold")
ax.set_title("Đối thủ được nhắc đến trong cuộc gọi", fontweight="bold", fontsize=12.5, pad=10)
save(fig, "competitor")

print("DONE")
