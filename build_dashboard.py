# -*- coding: utf-8 -*-
"""Sinh dashboard HTML tự chứa (inline SVG, không cần internet) từ aggregates.json."""
import json, os
A = json.load(open("output/aggregates.json", encoding="utf-8"))
DATA = json.dumps(A, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Bitel Perú · Dashboard Khiếu nại Call Center</title>
<style>
  :root{
    --amber:#FDC700; --amber-d:#E0A800; --ink:#0f172a; --slate:#475569;
    --mut:#94a3b8; --line:#e2e8f0; --bg:#f1f5f9; --card:#ffffff;
    --red:#e11d48; --red-bg:#fff1f2; --grn:#059669; --blu:#2563eb; --vio:#7c3aed; --org:#ea580c;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       background:var(--bg);color:var(--ink);line-height:1.45}
  .wrap{max-width:1280px;margin:0 auto;padding:22px 20px 60px}
  header.top{background:linear-gradient(110deg,#111827,#1f2937);color:#fff;border-radius:16px;
       padding:24px 28px;display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap;
       box-shadow:0 10px 30px rgba(2,6,23,.18)}
  header.top .badge{display:inline-block;background:var(--amber);color:#1a1a1a;font-weight:800;
       padding:3px 10px;border-radius:6px;font-size:12px;letter-spacing:.5px;margin-bottom:10px}
  header.top h1{margin:0;font-size:25px;font-weight:800;letter-spacing:-.3px}
  header.top h1 span{color:var(--amber)}
  header.top .sub{color:#cbd5e1;font-size:13px;margin-top:6px}
  header.top .meta{text-align:right;font-size:12px;color:#cbd5e1}
  header.top .meta b{color:#fff;font-size:15px}

  .controls{display:flex;align-items:center;gap:10px;margin:18px 0 6px;flex-wrap:wrap}
  .controls label{font-size:13px;color:var(--slate);font-weight:600}
  .controls select{padding:8px 12px;border:1px solid var(--line);border-radius:9px;background:#fff;
       font-size:14px;color:var(--ink);font-weight:600;cursor:pointer}
  .controls .note{font-size:12px;color:var(--mut)}

  .grid{display:grid;gap:16px}
  .kpis{grid-template-columns:repeat(4,1fr);margin-top:14px}
  @media(max-width:960px){.kpis{grid-template-columns:repeat(2,1fr)}}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;
       position:relative;overflow:hidden}
  .kpi .lab{font-size:12.5px;color:var(--slate);font-weight:600}
  .kpi .lab .es{color:var(--mut);font-weight:500;font-style:italic}
  .kpi .val{font-size:30px;font-weight:800;margin-top:6px;letter-spacing:-.5px}
  .kpi .sub{font-size:12px;color:var(--mut);margin-top:2px}
  .kpi .bar{position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--amber)}
  .kpi.red .bar{background:var(--red)} .kpi.red .val{color:var(--red)}
  .kpi.blu .bar{background:var(--blu)} .kpi.grn .bar{background:var(--grn)} .kpi.grn .val{color:var(--grn)}
  .kpi.vio .bar{background:var(--vio)} .kpi.org .bar{background:var(--org)}

  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-top:16px}
  .card h2{margin:0 0 2px;font-size:16.5px;font-weight:800}
  .card .h-es{font-size:12.5px;color:var(--mut);font-style:italic;margin-bottom:14px}
  .row2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .row3{display:grid;grid-template-columns:1.3fr 1fr;gap:16px}
  @media(max-width:900px){.row2,.row3{grid-template-columns:1fr}}

  .legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--slate);margin-top:8px}
  .legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
  .tip{position:fixed;pointer-events:none;background:#0f172a;color:#fff;font-size:12px;padding:7px 10px;
       border-radius:8px;opacity:0;transition:opacity .1s;z-index:99;box-shadow:0 6px 18px rgba(0,0,0,.25);max-width:240px}
  svg{display:block;width:100%;height:auto;overflow:visible}
  .bar-row:hover rect.b, .seg:hover{opacity:.82;cursor:default}

  table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
  th,td{text-align:left;padding:8px 8px;border-bottom:1px solid var(--line)}
  th{color:var(--slate);font-weight:700;font-size:12px}
  td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
  .pillbar{display:inline-block;height:8px;border-radius:4px;background:var(--amber);vertical-align:middle}

  .findings{background:linear-gradient(180deg,#fffbeb,#fff);border:1px solid #fde68a}
  .findings ul{margin:8px 0 0;padding-left:20px}
  .findings li{margin:7px 0;font-size:14px}
  .findings b{color:var(--org)}
  .tag{display:inline-block;background:#fef3c7;color:#92400e;font-size:11px;font-weight:700;
       padding:2px 8px;border-radius:20px;margin-left:6px}
  .foot{color:var(--mut);font-size:11.5px;margin-top:26px;text-align:center;line-height:1.7}
  .sec-title{font-size:13px;font-weight:800;color:var(--amber-d);letter-spacing:1px;
       text-transform:uppercase;margin:30px 4px 2px}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <span class="badge">BITEL PERÚ · CHURN ANALYTICS</span>
      <h1>Dashboard Khiếu nại & Lý do gọi <span>Call Center</span></h1>
      <div class="sub">Phân tích __N__ cuộc gọi (STT) · <i>Análisis de __N__ llamadas del centro de atención</i></div>
    </div>
    <div class="meta">
      Kỳ dữ liệu / <i>Periodo</i><br><b id="m-range">—</b><br>
      <span style="color:#94a3b8">Tạo lúc / generado: __GEN__</span>
    </div>
  </header>

  <div class="controls">
    <label for="msel">Lọc theo tháng / <i>Filtrar por mes</i>:</label>
    <select id="msel"><option value="ALL">Tất cả các kỳ / Todos</option></select>
    <span class="note">· Bộ lọc cập nhật các thẻ KPI và biểu đồ "Lý do gọi". <i>Actualiza KPIs y motivos.</i></span>
  </div>

  <div class="grid kpis" id="kpis"></div>

  <div class="sec-title">① Lý do khách hàng gọi / Motivos de contacto</div>
  <div class="card">
    <h2>Phân bố lý do gọi (nhãn chính)</h2>
    <div class="h-es">Distribución de motivos de llamada — categoría principal por llamada</div>
    <div id="reason"></div>
    <div class="legend"><span>📌 Mỗi cuộc gán 1 lý do chính. Một cuộc có thể chạm nhiều chủ đề (xem bảng đa nhãn bên dưới).</span></div>
  </div>

  <div class="row2">
    <div class="card">
      <h2>Đa nhãn: chủ đề xuất hiện trong cuộc gọi</h2>
      <div class="h-es">Temas mencionados (multi-etiqueta) — % trên tổng cuộc gọi</div>
      <div id="topics"></div>
    </div>
    <div class="card">
      <h2>Thời lượng & Chất lượng STT</h2>
      <div class="h-es">Duración de llamadas y confianza de transcripción</div>
      <div id="dur"></div>
      <div style="height:10px"></div>
      <div id="conf"></div>
    </div>
  </div>

  <div class="sec-title">② Xu hướng theo tháng / Tendencias mensuales</div>
  <div class="card">
    <h2>Sản lượng cuộc gọi & Tỷ lệ ý định rời mạng theo tháng</h2>
    <div class="h-es">Volumen de llamadas y % de intención de cancelación (churn) por mes</div>
    <div id="trend"></div>
    <div class="legend">
      <span><i style="background:#cbd5e1"></i>Số cuộc gọi / Volumen</span>
      <span><i style="background:var(--red)"></i>% ý định rời mạng / % churn</span>
      <span><i style="background:var(--blu)"></i>AHT (phút) / minutos</span>
    </div>
  </div>

  <div class="sec-title">③ Phân tích Churn / Análisis de cancelación</div>
  <div class="row3">
    <div class="card">
      <h2>Lý do gọi nào dẫn tới rời mạng nhiều nhất?</h2>
      <div class="h-es">Tasa de churn por motivo de llamada (% de llamadas con intención de irse)</div>
      <div id="churncat"></div>
    </div>
    <div class="card">
      <h2>Đối thủ được nhắc đến</h2>
      <div class="h-es">Operadores competidores mencionados</div>
      <div id="comp"></div>
      <div class="legend" style="margin-top:14px"><span id="comp-note"></span></div>
    </div>
  </div>

  <div class="sec-title">④ Vận hành / Operación</div>
  <div class="card">
    <h2>Thời lượng xử lý trung bình (AHT) theo lý do gọi</h2>
    <div class="h-es">Tiempo medio de atención (AHT) por motivo — phút / minutos</div>
    <div id="ahtcat"></div>
  </div>

  <div class="card findings">
    <h2>🔑 Phát hiện chính & Khuyến nghị / Hallazgos clave</h2>
    <div class="h-es">Đọc tự động từ dữ liệu — cần đối chiếu nghiệp vụ trước khi ra quyết định</div>
    <ul id="findings"></ul>
  </div>

  <div class="foot">
    Phương pháp / <i>Metodología</i>: phân loại theo từ khóa tiếng Tây Ban Nha trên transcript STT, sau khi lọc câu IVR/giữ máy/khảo sát.
    "Ý định rời mạng" = portabilidad/đổi nhà mạng hoặc hủy line (loại trừ khóa máy do mất/trộm).
    Đây là <b>ước lượng tự động</b>, không thay thế thẩm định nghiệp vụ.<br>
    Bitel Perú · Customer Care Analytics · dữ liệu __N__ cuộc gọi, kỳ __M0__–__M1__.
  </div>
</div>

<div class="tip" id="tip"></div>
<script>
const A = __DATA__;
const PALETTE = ["#FDC700","#2563eb","#059669","#e11d48","#7c3aed","#ea580c","#0891b2","#db2777","#65a30d","#9333ea","#0d9488","#64748b"];
const $ = s=>document.querySelector(s);
const tip = $("#tip");
function showTip(e,html){tip.innerHTML=html;tip.style.opacity=1;moveTip(e);}
function moveTip(e){tip.style.left=(e.clientX+14)+"px";tip.style.top=(e.clientY+14)+"px";}
function hideTip(){tip.style.opacity=0;}
const fmt = n=>n.toLocaleString("es-PE");
const SVGNS="http://www.w3.org/2000/svg";
function el(tag,attrs,txt){const e=document.createElementNS(SVGNS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(txt!=null)e.textContent=txt;return e;}

/* ---------- Horizontal bar chart ---------- */
function hbar(sel, items, opt){
  opt=opt||{};
  const W=opt.w||640, rh=opt.rh||30, pl=opt.pl||230, pr=46, top=6;
  const H=top+items.length*rh+6;
  const max=Math.max(...items.map(d=>d.v),0.0001);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img"});
  items.forEach((d,i)=>{
    const y=top+i*rh, bw=(W-pl-pr)*(d.v/max), col=d.col||"var(--amber)";
    const g=el("g",{class:"bar-row"});
    g.appendChild(el("text",{x:pl-10,y:y+rh/2+1,"text-anchor":"end","font-size":12.5,"font-weight":600,fill:"#334155"},d.l));
    if(d.l2) g.appendChild(el("text",{x:pl-10,y:y+rh/2+13,"text-anchor":"end","font-size":10.5,"font-style":"italic",fill:"#94a3b8"},d.l2));
    g.appendChild(el("rect",{x:pl,y:y+5,width:Math.max(bw,2),height:rh-13,rx:5,class:"b",fill:col}));
    g.appendChild(el("text",{x:pl+Math.max(bw,2)+8,y:y+rh/2+1,"font-size":12,"font-weight":700,fill:"#0f172a"},d.t!=null?d.t:fmt(d.v)));
    g.addEventListener("mousemove",e=>showTip(e,d.tip||`<b>${d.l}</b><br>${fmt(d.v)}`));
    g.addEventListener("mouseleave",hideTip);
    svg.appendChild(g);
  });
  const box=$(sel); box.innerHTML=""; box.appendChild(svg);
}

/* ---------- Combo: volume bars + churn% line + aht line ---------- */
function trendChart(sel){
  const m=A.trend.months_vn, vol=A.trend.volume, ch=A.trend.churn_pct, aht=A.trend.aht_min;
  const W=980,H=320,pl=52,pr=52,pt=20,pb=46;
  const iw=W-pl-pr, ih=H-pt-pb, n=m.length;
  const maxV=Math.max(...vol)*1.15, maxP=Math.max(...ch,...aht)*1.25;
  const xc=i=>pl+iw*(i+0.5)/n;
  const yV=v=>pt+ih*(1-v/maxV), yP=v=>pt+ih*(1-v/maxP);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`});
  // gridlines
  for(let g=0;g<=4;g++){const y=pt+ih*g/4;svg.appendChild(el("line",{x1:pl,y1:y,x2:W-pr,y2:y,stroke:"#eef2f7"}));}
  // volume bars
  const bw=iw/n*0.5;
  vol.forEach((v,i)=>{
    const x=xc(i)-bw/2,y=yV(v);
    const r=el("rect",{x:x,y:y,width:bw,height:pt+ih-y,rx:5,fill:"#cbd5e1",class:"seg"});
    r.addEventListener("mousemove",e=>showTip(e,`<b>${m[i]}</b><br>Cuộc gọi / Llamadas: ${fmt(v)}<br>Churn: ${ch[i]}% · AHT: ${aht[i]}'`));
    r.addEventListener("mouseleave",hideTip); svg.appendChild(r);
    svg.appendChild(el("text",{x:xc(i),y:H-pb+18,"text-anchor":"middle","font-size":12,fill:"#475569","font-weight":600},m[i]));
    svg.appendChild(el("text",{x:xc(i),y:y-6,"text-anchor":"middle","font-size":11,fill:"#64748b"},fmt(v)));
  });
  // line helper
  function line(arr,yf,col,lab){
    let dpath="";
    arr.forEach((v,i)=>{dpath+=(i?"L":"M")+xc(i)+" "+yf(v)+" ";});
    svg.appendChild(el("path",{d:dpath,fill:"none",stroke:col,"stroke-width":3,"stroke-linejoin":"round"}));
    arr.forEach((v,i)=>{
      const c=el("circle",{cx:xc(i),cy:yf(v),r:4.5,fill:"#fff",stroke:col,"stroke-width":2.5});
      c.addEventListener("mousemove",e=>showTip(e,`<b>${m[i]}</b><br>${lab}: ${v}${lab.includes("%")?"":""}`));
      c.addEventListener("mouseleave",hideTip); svg.appendChild(c);
      if(yf===yP) svg.appendChild(el("text",{x:xc(i),y:yf(v)-10,"text-anchor":"middle","font-size":11,"font-weight":700,fill:col},v+(lab.includes("Churn")?"%":"")));
    });
  }
  line(ch,yP,"#e11d48","% Churn");
  line(aht,yP,"#2563eb","AHT (phút)");
  $(sel).innerHTML=""; $(sel).appendChild(svg);
}

/* ---------- Donut ---------- */
function donut(sel, items){
  const W=300,H=210,cx=110,cy=H/2,r=78,ir=46;
  const tot=items.reduce((s,d)=>s+d.v,0)||1;
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`});
  let a0=-Math.PI/2;
  items.forEach((d,i)=>{
    const a1=a0+2*Math.PI*d.v/tot;
    const x0=cx+r*Math.cos(a0),y0=cy+r*Math.sin(a0),x1=cx+r*Math.cos(a1),y1=cy+r*Math.sin(a1);
    const xi0=cx+ir*Math.cos(a0),yi0=cy+ir*Math.sin(a0),xi1=cx+ir*Math.cos(a1),yi1=cy+ir*Math.sin(a1);
    const big=(a1-a0)>Math.PI?1:0, col=d.col||PALETTE[i%PALETTE.length];
    const p=el("path",{d:`M${x0} ${y0} A${r} ${r} 0 ${big} 1 ${x1} ${y1} L${xi1} ${yi1} A${ir} ${ir} 0 ${big} 0 ${xi0} ${yi0} Z`,fill:col,class:"seg"});
    p.addEventListener("mousemove",e=>showTip(e,`<b>${d.l}</b><br>${fmt(d.v)} (${(100*d.v/tot).toFixed(1)}%)`));
    p.addEventListener("mouseleave",hideTip); svg.appendChild(p);
    // legend
    const ly=24+i*26;
    svg.appendChild(el("rect",{x:212,y:ly-9,width:11,height:11,rx:3,fill:col}));
    svg.appendChild(el("text",{x:228,y:ly,"font-size":12.5,"font-weight":600,fill:"#334155"},`${d.l}`));
    svg.appendChild(el("text",{x:228,y:ly+13,"font-size":11,fill:"#94a3b8"},`${fmt(d.v)} · ${(100*d.v/tot).toFixed(0)}%`));
    a0=a1;
  });
  svg.appendChild(el("text",{x:cx,y:cy-4,"text-anchor":"middle","font-size":22,"font-weight":800,fill:"#0f172a"},fmt(tot)));
  svg.appendChild(el("text",{x:cx,y:cy+14,"text-anchor":"middle","font-size":10.5,fill:"#94a3b8"},"lượt nhắc"));
  $(sel).innerHTML=""; $(sel).appendChild(svg);
}

/* ---------- KPI cards ---------- */
function renderKPIs(month){
  let vol,churnP,negP,aht,churnLab;
  if(month==="ALL"){
    vol=A.total_calls; churnP=A.churn_pct; negP=A.neg_pct; aht=A.aht_min;
  }else{
    const i=A.trend.months.indexOf(month);
    vol=A.trend.volume[i]; churnP=A.trend.churn_pct[i]; negP=A.trend.neg_pct[i]; aht=A.trend.aht_min[i];
  }
  const cards=[
    {c:"",  lab:"Tổng cuộc gọi", es:"Total llamadas", val:fmt(vol), sub:(month==="ALL"?(A.total_talk_hours+" giờ đàm thoại / horas"):"trong tháng / en el mes")},
    {c:"blu",lab:"AHT trung bình", es:"Tiempo medio", val:aht+"′", sub:"Trung vị / mediana: "+A.median_min+"′"},
    {c:"red",lab:"Ý định rời mạng", es:"Intención de churn", val:churnP+"%", sub:(month==="ALL"?fmt(A.churn_n)+" cuộc · portabilidad/hủy line":"% cuộc trong tháng")},
    {c:"org",lab:"Nguy cơ cần giữ chân", es:"Riesgo de retención", val:A.retention_pct+"%", sub:fmt(A.retention_n)+" cuộc (churn+đối thủ+hạ gói)"},
    {c:"vio",lab:"Cảm xúc tiêu cực / Khiếu nại", es:"Sentimiento negativo", val:negP+"%", sub:(month==="ALL"?fmt(A.neg_n)+" cuộc · reclamo/molesto/estafa":"% trong tháng")},
    {c:"",  lab:"Nhắc đối thủ", es:"Menciona competencia", val:A.comp_pct+"%", sub:fmt(A.comp_n)+" cuộc · Movistar/Claro/Entel"},
    {c:"grn",lab:"Được mời khảo sát CSAT", es:"Encuesta ofrecida", val:A.csat_pct+"%", sub:fmt(A.csat_n)+" cuộc"},
    {c:"",  lab:"Chất lượng STT (tin cậy TB)", es:"Confianza STT", val:A.avg_conf, sub:A.empty+" transcript rỗng / vacíos"},
  ];
  $("#kpis").innerHTML = cards.map(k=>`
    <div class="kpi ${k.c}"><div class="bar"></div>
      <div class="lab">${k.lab} <span class="es">${k.es}</span></div>
      <div class="val">${k.val}</div><div class="sub">${k.sub}</div></div>`).join("");
}

/* ---------- Reason distribution (month-aware) ---------- */
function renderReason(month){
  let items;
  if(month==="ALL"){
    items=A.primary_dist.map((d,i)=>({l:d.vn,l2:d.es,v:d.n,t:d.pct+"%",col:PALETTE[i%PALETTE.length],
      tip:`<b>${d.vn}</b><br><i>${d.es}</i><br>${fmt(d.n)} cuộc · ${d.pct}%`}));
  }else{
    const i=A.trend.months.indexOf(month);
    const arr=Object.keys(A.trend.by_primary).map(k=>({k,n:A.trend.by_primary[k][i]}))
              .filter(x=>x.n>0).sort((a,b)=>b.n-a.n);
    const tot=arr.reduce((s,x)=>s+x.n,0)||1;
    items=arr.map((x,j)=>({l:A.labels[x.k][0],l2:A.labels[x.k][1],v:x.n,t:(100*x.n/tot).toFixed(1)+"%",
      col:PALETTE[j%PALETTE.length],tip:`<b>${A.labels[x.k][0]}</b><br>${fmt(x.n)} cuộc · ${(100*x.n/tot).toFixed(1)}%`}));
  }
  hbar("#reason",items,{rh:34});
}

/* ---------- static charts ---------- */
function renderStatics(){
  hbar("#topics", A.topic_dist.filter(d=>d.key!=="general").map((d,i)=>({
    l:d.vn,v:d.n,t:d.pct+"%",col:PALETTE[i%PALETTE.length],
    tip:`<b>${d.vn}</b><br><i>${d.es}</i><br>${fmt(d.n)} cuộc · ${d.pct}% tổng`})),{pl:170,rh:25,w:560});

  const durCol=["#bae6fd","#7dd3fc","#38bdf8","#0ea5e9","#0369a1"];
  hbar("#dur", A.dur_dist.map((d,i)=>({l:d.bucket,v:d.n,t:fmt(d.n),col:durCol[i],
    tip:`<b>${d.bucket}</b><br>${fmt(d.n)} cuộc`})),{pl:90,rh:24,w:520});

  const cOrder={"Cao (≥0.85)":"#059669","TB (0.70-0.85)":"#f59e0b","Thấp (0.50-0.70)":"#f97316","Rất thấp (<0.50)":"#dc2626"};
  const cd=A.conf_dist.slice().sort((a,b)=>b.n-a.n);
  hbar("#conf", cd.map(d=>({l:d.band,v:d.n,t:fmt(d.n),col:cOrder[d.band]||"#94a3b8",
    tip:`<b>${d.band}</b><br>${fmt(d.n)} cuộc`})),{pl:140,rh:24,w:520});

  // loại 'cancel_churn' (định nghĩa = 100% churn, không phải insight) và 'general'
  hbar("#churncat", A.churn_by_cat.filter(d=>d.tot>=40 && d.key!=="cancel_churn" && d.key!=="general")
       .slice().sort((a,b)=>b.pct-a.pct).slice(0,8).map(d=>({
    l:d.vn,v:d.pct,t:d.pct+"%",col:d.pct>=30?"#e11d48":(d.pct>=20?"#f97316":"#f59e0b"),
    tip:`<b>${d.vn}</b><br>${d.pct}% có ý định rời mạng<br>${fmt(d.n)} / ${fmt(d.tot)} cuộc gọi loại này`})),{pl:200,rh:30,w:560});

  donut("#comp", A.competitor_dist.map((d,i)=>({l:d.name,v:d.n,col:["#e11d48","#2563eb","#059669","#7c3aed"][i%4]})));
  const ct=A.competitor_dist.reduce((s,d)=>s+d.n,0);
  $("#comp-note").innerHTML=`Tổng ${fmt(ct)} lượt nhắc đối thủ trong ${fmt(A.comp_n)} cuộc gọi. <i>Menciones de la competencia.</i>`;

  hbar("#ahtcat", A.aht_by_cat.filter(d=>d.n>=20).map(d=>({
    l:d.vn,v:d.aht_min,t:d.aht_min+"′",col:"#2563eb",
    tip:`<b>${d.vn}</b><br>AHT ${d.aht_min} phút<br>${fmt(d.n)} cuộc`})),{pl:200,rh:28,w:560});
}

/* ---------- findings ---------- */
function renderFindings(){
  const pd=A.primary_dist, top1=pd[0], top2=pd[1];
  const ch=A.trend.churn_pct, m=A.trend.months_vn;
  const rise=(ch[ch.length-1]-ch[0]).toFixed(1);
  const topChurn=A.churn_by_cat.filter(d=>d.tot>=40 && d.key!=="cancel_churn" && d.key!=="general").slice().sort((a,b)=>b.pct-a.pct)[0];
  const peakIdx=A.trend.volume.indexOf(Math.max(...A.trend.volume));
  const comp=A.competitor_dist[0];
  const longAht=A.aht_by_cat[0];
  const items=[
    `<b>Hai lý do gọi lớn nhất</b>: <b>${top1.vn}</b> (${top1.pct}%) và <b>${top2.vn}</b> (${top2.pct}%) — chiếm ${(top1.pct+top2.pct).toFixed(1)}% tổng cuộc gọi. <span class="tag">ưu tiên xử lý gốc</span>`,
    `<b>Tỷ lệ ý định rời mạng đang tăng</b>: từ ${ch[0]}% (${m[0]}) lên ${ch[ch.length-1]}% (${m[m.length-1]}), tăng <b>${rise} điểm %</b>. Cần cảnh báo sớm & chương trình giữ chân.`,
    `<b>Lý do gọi gắn với churn cao nhất</b>: "<b>${topChurn.vn}</b>" — ${topChurn.pct}% số cuộc loại này có ý định rời mạng. Đây là điểm rò rỉ thuê bao cần can thiệp.`,
    `<b>Đối thủ bị nhắc nhiều nhất</b>: <b>${comp.name}</b> (${fmt(comp.n)} lượt) — theo dõi ưu đãi cạnh tranh của họ.`,
    `<b>Khó xử lý nhất (AHT dài nhất)</b>: "<b>${longAht.vn}</b>" ~${longAht.aht_min} phút/cuộc — xem lại quy trình & công cụ hỗ trợ tư vấn viên.`,
    `<b>Khiếu nại/cảm xúc tiêu cực</b>: ${A.neg_pct}% cuộc gọi (${fmt(A.neg_n)}). Tự phục vụ qua app MiBitel có thể giảm tải các vấn đề lặp lại.`,
  ];
  $("#findings").innerHTML=items.map(t=>`<li>${t}</li>`).join("");
}

/* ---------- init ---------- */
(function(){
  $("#m-range").textContent = A.months_vn[0]+" – "+A.months_vn[A.months_vn.length-1];
  const sel=$("#msel");
  A.months.forEach((p,i)=>{const o=document.createElement("option");o.value=p;o.textContent=A.months_vn[i];sel.appendChild(o);});
  sel.addEventListener("change",()=>{renderKPIs(sel.value);renderReason(sel.value);});
  renderKPIs("ALL"); renderReason("ALL"); renderStatics(); trendChart("#trend"); renderFindings();
  window.addEventListener("scroll",hideTip,{passive:true});
})();
</script>
</body>
</html>"""

out = HTML.replace("__DATA__", DATA)\
          .replace("__N__", f"{A['total_calls']:,}".replace(",", "."))\
          .replace("__GEN__", A["generated_at"])\
          .replace("__M0__", A["months_vn"][0])\
          .replace("__M1__", A["months_vn"][-1])

path = "output/dashboard.html"
open(path, "w", encoding="utf-8").write(out)
print("→", path, f"({len(out)//1024} KB)")
