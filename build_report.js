// Báo cáo Phân tích Hành vi Khách hàng qua Tổng đài — Bitel Perú
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        ImageRun, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
        WidthType, ShadingType, PageNumber, Header, Footer, VerticalAlign } = require("docx");

const A = JSON.parse(fs.readFileSync("output/aggregates.json", "utf8"));
const INK="0F172A", AMBER="FDC700", RED="E11D48", SLATE="475569", GRAY="F1F5F9",
      DARK="1F2937", LBLUE="EFF6FF", LAMBER="FFFBEB", LRED="FFF1F2";

// ---------- helpers ----------
const P = (text, opt={}) => new Paragraph({
  spacing: { after: opt.after ?? 120, before: opt.before ?? 0, line: 276 },
  alignment: opt.align,
  children: [new TextRun({ text, bold: opt.bold, italics: opt.italics,
    size: opt.size ?? 22, color: opt.color ?? INK, font: "Arial" })],
  ...(opt.pPr||{})
});
const runs = (arr, opt={}) => new Paragraph({
  spacing: { after: opt.after ?? 120, line: 276 },
  children: arr.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i,
    color: r.c ?? INK, size: r.s ?? 22, font: "Arial" }))
});
const H1 = (n, t) => new Paragraph({ heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: (n?n+". ":"")+t, bold: true, size: 30, color: INK, font: "Arial" })],
  spacing: { before: 320, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: AMBER, space: 6 } } });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text: t, bold: true, size: 25, color: DARK, font: "Arial" })],
  spacing: { before: 220, after: 110 } });
const bullet = (text, ref="bullets") => new Paragraph({
  numbering: { reference: ref, level: 0 }, spacing: { after: 80, line: 270 },
  children: Array.isArray(text) ? text.map(r=>new TextRun({text:r.t,bold:r.b,italics:r.i,color:r.c??INK,size:22,font:"Arial"}))
                                : [new TextRun({ text, size: 22, color: INK, font: "Arial" })] });

function img(path, w) {
  const buf = fs.readFileSync(path);
  // ratio derived from known figure sizes; pass explicit h
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing:{before:80, after:120},
    children: [new ImageRun({ type: "png", data: buf,
      transformation: { width: w.w, height: w.h },
      altText: { title: w.t, description: w.t, name: w.t } })] });
}
const caption = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:160},
  children:[new TextRun({text:t, italics:true, size:18, color:SLATE, font:"Arial"})] });

// table builder
const border = { style: BorderStyle.SINGLE, size: 1, color: "D9DEE6" };
const borders = { top:border, bottom:border, left:border, right:border,
  insideHorizontal:border, insideVertical:border };
function cell(text, w, opt={}) {
  const children = Array.isArray(text)
    ? text.map(line => new Paragraph({ spacing:{after:20,line:250},
        alignment: opt.align,
        children:[new TextRun({ text: line.t, bold: line.b||opt.bold, italics:line.i,
          color: line.c||opt.color||INK, size: opt.size??19, font:"Arial" })] }))
    : [new Paragraph({ spacing:{after:0,line:250}, alignment: opt.align,
        children:[new TextRun({ text, bold: opt.bold, italics:opt.italics,
          color: opt.color??INK, size: opt.size??19, font:"Arial" })] })];
  return new TableCell({ width:{size:w,type:WidthType.DXA}, borders,
    shading: opt.fill?{fill:opt.fill,type:ShadingType.CLEAR}:undefined,
    margins:{top:60,bottom:60,left:110,right:110},
    verticalAlign: VerticalAlign.CENTER, children });
}
function table(widths, headerRow, dataRows, opt={}) {
  const total = widths.reduce((a,b)=>a+b,0);
  const rows = [];
  rows.push(new TableRow({ tableHeader:true, children: headerRow.map((h,i)=>
    cell(h, widths[i], {bold:true,color:"FFFFFF",fill:DARK,align: i===0?AlignmentType.LEFT:AlignmentType.CENTER,size:19})) }));
  dataRows.forEach((r,ri)=>{
    rows.push(new TableRow({ children: r.map((c,i)=>{
      const isObj = typeof c === "object" && !Array.isArray(c);
      const val = isObj ? c.t : c;
      return cell(val, widths[i], { fill: ri%2?GRAY:undefined,
        align: i===0?AlignmentType.LEFT:AlignmentType.CENTER,
        bold: isObj?c.b:false, color: isObj?c.c:undefined, size: 19 }); }) }));
  });
  return new Table({ width:{size:total,type:WidthType.DXA}, columnWidths:widths, borders, rows });
}
function calloutBox(title, lines, fill, bar) {
  // a one-cell table acting as a colored callout
  const kids = [ new Paragraph({ spacing:{after:60}, children:[new TextRun({text:title,bold:true,size:22,color:INK,font:"Arial"})] }) ];
  lines.forEach(l=>kids.push(new Paragraph({ spacing:{after:40,line:264},
    children:[new TextRun({text:l,size:21,color:INK,font:"Arial"})] })));
  return new Table({ width:{size:9360,type:WidthType.DXA}, columnWidths:[9360],
    borders:{ left:{style:BorderStyle.SINGLE,size:24,color:bar},
      top:{style:BorderStyle.SINGLE,size:2,color:fill}, bottom:{style:BorderStyle.SINGLE,size:2,color:fill},
      right:{style:BorderStyle.SINGLE,size:2,color:fill} },
    rows:[ new TableRow({ children:[ new TableCell({ width:{size:9360,type:WidthType.DXA},
      shading:{fill:fill,type:ShadingType.CLEAR}, margins:{top:140,bottom:140,left:200,right:200},
      children: kids }) ]}) ] });
}
const fmt = n => n.toLocaleString("vi-VN");
const vn = n => String(n).replace(".", ",");  // thập phân kiểu Việt (dấu phẩy)

// ===================== CONTENT =====================
const children = [];

// --- Title block ---
children.push(new Paragraph({ spacing:{after:40},
  children:[new TextRun({text:"BITEL PERÚ · PHÂN TÍCH HÀNH VI KHÁCH HÀNG", bold:true, size:20, color:"B45309", font:"Arial"})] }));
children.push(new Paragraph({ spacing:{after:60},
  children:[new TextRun({text:"Báo cáo Phân tích Hành vi Khách hàng qua Tổng đài", bold:true, size:40, color:INK, font:"Arial"})] }));
children.push(new Paragraph({ spacing:{after:40},
  children:[new TextRun({text:"Análisis del comportamiento del cliente — Centro de Atención", italics:true, size:22, color:SLATE, font:"Arial"})] }));
children.push(new Paragraph({ border:{bottom:{style:BorderStyle.SINGLE,size:14,color:AMBER,space:8}}, spacing:{after:160}, children:[] }));
children.push(runs([
  {t:"Nguồn dữ liệu: ",b:true}, {t:`${fmt(A.total_calls)} transcript cuộc gọi (STT) · `},
  {t:"Kỳ: ",b:true}, {t:`${A.months_vn[0]} – ${A.months_vn[A.months_vn.length-1]} · `},
  {t:"Tạo lúc: ",b:true}, {t:`${A.generated_at}`},
], {after:60, }));
children.push(P("Người thực hiện: Bộ phận Phân tích Chăm sóc Khách hàng (Customer Care Analytics).",
  {italics:true, color:SLATE, size:20, after:200}));

// --- 1. Executive summary ---
children.push(H1("1","Tóm tắt điều hành"));
children.push(P("Phân tích "+fmt(A.total_calls)+" cuộc gọi tổng đài trong 6 tháng cho thấy hành vi liên hệ của khách hàng tập trung vào hai nhóm nhu cầu chính: xử lý hóa đơn/thanh toán và khắc phục chất lượng dịch vụ dữ liệu. Quan trọng hơn về mặt hành vi, tỷ lệ cuộc gọi bộc lộ ý định rời mạng đang tăng nhanh và liên tục — đây là tín hiệu cảnh báo sớm cần hành động ngay.", {after:140}));
children.push(calloutBox("Năm phát hiện hành vi cốt lõi:", [
  "1.  Ý định rời mạng TĂNG đều từ 11,2% (11/2025) lên 23,5% (04/2026) — gấp đôi sau 6 tháng; tốc độ chuyển hóa từ bất mãn sang rời bỏ đang nhanh dần, dù sản lượng cuộc gọi đã giảm trong 2 tháng cuối.",
  "2.  Việc khách HỎI/SO SÁNH với đối thủ là dự báo rời mạng mạnh nhất: 40,6% nhóm này có ý định rời (gấp 2,5 lần nền chung 16,4%).",
  "3.  Hành vi 'so giá' (đòi hạ gói, hỏi khuyến mãi) gắn churn rất cao — gói Khuyến mãi 28,0%, Đổi gói 21,4%; nhóm đòi hạ gói có churn 30,9% (gấp 1,9 lần).",
  "4.  Phần lớn khách rời mạng một cách 'lặng lẽ' vì lý do thương mại: chỉ 25,5% cuộc churn có biểu hiện cảm xúc tiêu cực — không phải ai bực tức mới rời đi.",
  "5.  Đối thủ tạo áp lực rõ rệt: Movistar bị nhắc nhiều nhất (43% lượt nhắc), kế đến Claro (35%) và Entel (22%).",
], LAMBER, AMBER));

// --- 2. Data & method ---
children.push(H1("2","Dữ liệu & phương pháp"));
children.push(P("Báo cáo dựa trên "+fmt(A.total_calls)+" bản ghi âm cuộc gọi đã chuyển văn bản (speech-to-text, tiếng Tây Ban Nha), tổng "+vn(A.total_talk_hours)+" giờ đàm thoại, trải đều 6 kỳ từ "+A.months_vn[0]+" đến "+A.months_vn[A.months_vn.length-1]+". Thời lượng trung bình mỗi cuộc (AHT) là "+vn(A.aht_min)+" phút (trung vị "+vn(A.median_min)+" phút). Độ tin cậy trung bình của STT là "+vn(A.avg_conf)+"; "+A.empty+" transcript rỗng được loại."));
children.push(H2("Cách phân loại hành vi"));
children.push(bullet([{t:"Lọc nhiễu trước: ",b:true},{t:"loại bỏ các câu IVR/giữ máy, quảng cáo app MiBitel, lời mời khảo sát và thu thập danh tính — chỉ giữ nội dung phản ánh nhu cầu thật của khách."}]));
children.push(bullet([{t:"Gán lý do gọi (đa nhãn): ",b:true},{t:"mỗi cuộc có 1 'lý do chính' và có thể kèm nhiều chủ đề phụ, theo bộ từ khóa nghiệp vụ tiếng Tây Ban Nha."}]));
children.push(bullet([{t:"Tách người nói (Asesor/Cliente): ",b:true},{t:"phân từng câu thành tư vấn viên / khách / IVR bằng dấu hiệu ngôn ngữ. Churn, cảm xúc tiêu cực và nhắc đối thủ CHỈ tính trên lời KHÁCH — tránh đếm nhầm lời tư vấn viên (vd giải thích thủ tục). Riêng lý do gọi vẫn xét cả hội thoại vì từ khóa danh mục thường do tư vấn viên nói."}]));
children.push(bullet([{t:"Đo ý định rời mạng theo 2 tầng: ",b:true},{t:"(a) Ý định rời mạng — khách muốn chuyển sang nhà mạng khác (outbound) hoặc hủy line, đã loại trừ khóa máy do mất/trộm VÀ 'portabilidad vào Bitel' (khách mới chuyển đến); (b) Nguy cơ cần giữ chân — rộng hơn, gồm cả nhắc đối thủ và đòi hạ gói."}]));
children.push(calloutBox("Lưu ý phương pháp (đọc kỹ trước khi ra quyết định):", [
  "• Đây là ước lượng tự động bằng quy tắc từ khóa, không thay thế thẩm định nghiệp vụ.",
  "• Bộ tách người nói dựa trên dấu hiệu ngôn ngữ (không có audio để tách theo âm thanh). Việc tách giúp loại ~28% cờ churn sai (lời tư vấn viên hoặc portabilidad-vào-Bitel) — đưa churn từ 22,8% xuống 16,4% — nhưng một số câu khách ngắn có thể bị gán nhầm.",
  "• Trong tiếng Tây Ban Nha Peru, 'cancelar' thường nghĩa là 'thanh toán', và 'portabilidad' thường là chiều VÀO Bitel — đều đã xử lý riêng để không tính nhầm thành rời mạng.",
  "• Mỗi số điện thoại chỉ xuất hiện một lần trong tập dữ liệu này, nên chưa thể đo hành vi gọi lặp lại liên kết theo khách hàng (xem mục Bước tiếp theo).",
], LBLUE, "2563EB"));

// --- 3. Contact demand map ---
children.push(H1("3","Bản đồ nhu cầu liên hệ — vì sao khách gọi?"));
children.push(P("Nhìn dưới góc độ hành vi, mỗi cuộc gọi là một 'điểm ma sát' (friction point) khiến khách phải bỏ công liên hệ. Cấu trúc nhu cầu cho thấy ba khối hành vi lớn:", {after:120}));
children.push(img("output/charts/reason_dist.png", {w:580,h:319,t:"Phân bố lý do gọi"}));
children.push(caption("Hình 1 — Lý do chính khiến khách gọi tổng đài (% trên tổng cuộc gọi)."));
children.push(bullet([{t:"Khối 'vận hành tài khoản' — Hóa đơn & Thanh toán (35,2%): ",b:true},{t:"khối lớn nhất, phản ánh ma sát quanh hiểu/đối soát hóa đơn, nợ cước, ngày thanh toán. Đây là nhu cầu mang tính giao dịch, lặp lại hàng tháng."}]));
children.push(bullet([{t:"Khối 'chất lượng dịch vụ' — Internet/Tốc độ (32,0%) + Phủ sóng (3,3%): ",b:true},{t:"chiếm hơn 1/3 cuộc gọi, là ma sát mang tính chức năng (sản phẩm không đáp ứng kỳ vọng). Đây cũng là khối tốn công xử lý nhất."}]));
children.push(bullet([{t:"Khối 'thương mại' — Đổi gói (9,9%) + Khuyến mãi (3,3%): ",b:true},{t:"khách chủ động đánh giá lại giá trị nhận được. Khối này tuy nhỏ về sản lượng nhưng có ý nghĩa lớn về churn (xem Mục 5)."}]));
children.push(P("Lưu ý: nếu tính đa nhãn (mọi chủ đề được nhắc trong cuộc), Hóa đơn xuất hiện ở 60,2% cuộc và Internet ở 53,3% — cho thấy hai nhu cầu này thường đan xen nhau trong cùng một cuộc gọi.", {italics:true, color:SLATE, size:20}));

// --- 4. Churn funnel + lift ---
children.push(H1("4","Phễu hành vi rời mạng & tín hiệu dự báo"));
children.push(P("Hành vi rời mạng không xảy ra đột ngột mà đi theo một phễu: bất mãn → so sánh với đối thủ → hình thành ý định rời. Đo trên toàn tập:", {after:120}));
children.push(table([3300,1700,4360],
  ["Bậc phễu hành vi","% tổng cuộc","Diễn giải"],
  [
   [{t:"Bộc lộ cảm xúc tiêu cực / khiếu nại",b:true}, vn(A.neg_pct)+"%", "Bất mãn về dịch vụ, cước, thái độ (reclamo, molesto, estafa…)"],
   [{t:"So sánh / nhắc đối thủ",b:true}, vn(A.comp_pct)+"%", "Đang cân nhắc phương án thay thế (Movistar, Claro, Entel)"],
   [{t:"Ý định rời mạng (đáy phễu)",b:true,c:RED}, {t:vn(A.churn_pct)+"%",b:true,c:RED}, "Đòi portabilidad / hủy line — ranh giới mất thuê bao"],
  ]));
children.push(P("Điểm mấu chốt về mặt hành vi: ý định rời (16,4%) vẫn CAO HƠN tỷ lệ nhắc đối thủ (7,8%). Nghĩa là phần lớn khách rời đi không phải vì bị đối thủ lôi kéo, mà vì tự quyết định dừng dịch vụ — thường sau trải nghiệm hóa đơn hoặc chất lượng mạng không như ý.", {before:60, after:140}));
children.push(H2("Tín hiệu nào dự báo rời mạng mạnh nhất?"));
children.push(img("output/charts/churn_lift.png", {w:580,h:305,t:"Lift churn theo tín hiệu"}));
children.push(caption("Hình 2 — Xác suất có ý định rời mạng theo từng tín hiệu hành vi, so với nền chung 16,4%."));
children.push(runs([
  {t:"Khi khách chủ động nhắc đối thủ, xác suất rời mạng nhảy lên 40,6% — gấp 2,5 lần nền chung. ",b:true},
  {t:"Đây là 'tín hiệu nóng' cần ưu tiên cao nhất: một khi khách đã so giá với Movistar/Claro, gần một nửa đã có ý định đi. Kế đến, đòi hạ gói (30,9%, x1,9), gọi lại nhiều lần (25,0%, x1,5) và cảm xúc tiêu cực (24,7%, x1,5) cho thấy ma sát giá và sự việc chưa được giải quyết là các động lực churn rõ rệt."},
]));
children.push(P("Cuộc gọi có ý định rời mạng cũng kéo dài hơn (8,4 phút so với 7,4 phút) — phản ánh sự giằng co/thuyết phục, tức tư vấn viên đang phải 'cứu' khách ngay trên điện thoại.", {italics:true, color:SLATE, size:20}));

// --- 5. Leak points ---
children.push(H1("5","Điểm rò rỉ thuê bao theo lý do gọi"));
children.push(P("Cùng một lý do gọi nhưng 'độ rủi ro rời mạng' rất khác nhau. Biểu đồ dưới đo tỷ lệ khách có ý định rời trong từng loại cuộc gọi:", {after:120}));
children.push(img("output/charts/churn_by_reason.png", {w:580,h:290,t:"Churn theo lý do"}));
children.push(caption("Hình 3 — Tỷ lệ ý định rời mạng theo lý do gọi (loại nhóm 'Hủy/Rời mạng' vì hiển nhiên 100%)."));
children.push(bullet([{t:"Khuyến mãi & Đổi gói là điểm rò rỉ nguy hiểm nhất (28,0% và 21,4%): ",b:true},{t:"khách gọi về giá/ưu đãi thực chất đang ở 'ngã ba quyết định' — nếu không nhận được giá trị thuyết phục, họ chuyển sang đối thủ."}]));
children.push(bullet([{t:"Hóa đơn tuy churn 'chỉ' 19,2% nhưng là điểm rò rỉ LỚN NHẤT về số lượng tuyệt đối: ",b:true},{t:"357 thuê bao có nguy cơ — vì đây là khối cuộc gọi đông nhất. Cải thiện trải nghiệm hóa đơn có dư địa giữ chân lớn nhất."}]));
children.push(bullet([{t:"Internet/Phủ sóng có churn theo tỷ lệ thấp hơn (11,6% / 7,4%) ",b:true},{t:"nhưng tốn nhiều công xử lý nhất (AHT 8,6–8,7 phút) — rủi ro nằm ở sự bào mòn niềm tin tích lũy nếu lỗi lặp lại."}]));

// --- 6. Behavioral segments ---
children.push(H1("6","Phân khúc khách hàng theo hành vi"));
children.push(P("Từ dữ liệu, có thể nhóm khách thành 5 phân khúc hành vi, mỗi nhóm cần một cách tiếp cận giữ chân khác nhau:", {after:130}));
children.push(table([2550,1150,1500,4160],
  ["Phân khúc hành vi","Quy mô","Mức churn","Đặc điểm & hàm ý"],
  [
   [{t:"Khách áp lực hóa đơn (Billing-stressed)",b:true},"35,2%","19,2%","Ma sát giao dịch lặp lại; cần minh bạch hóa đơn & nhắc cước chủ động."],
   [{t:"Bất mãn chất lượng mạng (Network-frustrated)",b:true},"35,3%","~11%","Ma sát chức năng; AHT dài nhất; cần triage kỹ thuật & theo dõi vùng lỗi."],
   [{t:"Người so giá thương mại (Commercial shoppers)",b:true,c:RED},{t:"13,2%",b:true},{t:"21–28%",b:true,c:RED},"Đang đánh giá lại giá trị; churn cao nhất; cần ưu đãi giữ chân đúng thời điểm."],
   [{t:"Người đang rời mạng (Active switchers)",b:true,c:RED},"~1,5%+","rất cao","Đã đòi portabilidad/hủy; cần 'bàn cứu khách' (save desk) chuyên trách."],
   [{t:"Khách dịch vụ/hành chính (Service & admin)",b:true},"~12,8%","7–13%","Tạm ngưng, SIM/thiết bị, đổi chủ TB; cơ hội phục hồi dịch vụ & tự phục vụ."],
  ]));
children.push(P("Hai phân khúc 'Người so giá' và 'Người đang rời mạng' tuy chỉ chiếm ~15% sản lượng nhưng tạo phần lớn rủi ro mất thuê bao thực tế — đây là nơi nên đặt nguồn lực giữ chân tinh nhuệ nhất.", {before:60, italics:true, color:SLATE, size:20}));

// --- 7. Emotion & competition ---
children.push(H1("7","Tín hiệu cảm xúc & áp lực cạnh tranh"));
children.push(P(vn(A.neg_pct)+"% cuộc gọi có khách bộc lộ cảm xúc tiêu cực hoặc khiếu nại rõ rệt ("+fmt(A.neg_n)+" cuộc, chỉ tính lời khách). Trong khi tỷ lệ này tương đối ổn định, ý định rời mạng lại tăng vọt — củng cố nhận định rằng churn hiện nay phần nhiều mang động cơ thương mại/lý trí, không chỉ do tức giận. (Chỉ 25,5% cuộc churn có cảm xúc tiêu cực.)", {after:130}));
children.push(img("output/charts/competitor.png", {w:330,h:266,t:"Đối thủ"}));
children.push(caption("Hình 4 — Cơ cấu lượt nhắc đối thủ ("+fmt(A.comp_n)+" cuộc gọi có nhắc đối thủ)."));
children.push(P("Movistar là cái tên xuất hiện thường xuyên nhất trong các cuộc 'so giá', cho thấy đây là đối thủ tạo áp lực cạnh tranh trực tiếp lớn nhất lên tệp khách Bitel trong kỳ. Cần theo dõi sát các gói/ưu đãi của Movistar để phản ứng kịp thời.", {after:100}));

// --- 8. Trend ---
children.push(H1("8","Diễn biến theo thời gian — vì sao đáng lo?"));
children.push(img("output/charts/churn_trend.png", {w:580,h:305,t:"Diễn biến churn"}));
children.push(caption("Hình 5 — Sản lượng cuộc gọi và tỷ lệ ý định rời mạng theo tháng."));
children.push(P("Đây là biểu đồ quan trọng nhất của báo cáo. Sản lượng cuộc gọi đã đạt đỉnh vào 02/2026 rồi giảm, NHƯNG tỷ lệ ý định rời mạng vẫn tăng không ngừng, đạt 23,5% vào 04/2026 — cao gấp đôi so với 11,2% đầu kỳ (số đã hiệu chỉnh chỉ tính lời khách). Về mặt hành vi, điều này nghĩa là: trong số những khách còn gọi lên, ngày càng nhiều người đã đi đến quyết định rời bỏ. Rào cản chuyển mạng đang yếu đi và/hoặc sức hút từ đối thủ đang mạnh lên. Nếu xu hướng này tiếp diễn, áp lực mất thuê bao trong các quý tới sẽ rất lớn.", {after:80}));

// --- 9. Recommendations ---
children.push(H1("9","Khuyến nghị hành động (theo phân khúc)"));
children.push(P("Các khuyến nghị được sắp theo thứ tự ưu tiên dựa trên mức độ rủi ro churn và khả năng tác động:", {after:120}));
children.push(bullet([{t:"Ưu tiên 1 — Lập 'bàn cứu khách' cho tín hiệu nóng: ",b:true},{t:"khi khách nhắc đối thủ hoặc đòi portabilidad (outbound), định tuyến ngay tới nhóm giữ chân chuyên trách với quyền chào ưu đãi linh hoạt (41% nhóm nhắc đối thủ có ý định rời — gấp 2,5 lần nền chung)."}], "numbers"));
children.push(bullet([{t:"Ưu tiên 2 — Phản công nhóm 'so giá': ",b:true},{t:"xây kịch bản giữ chân riêng cho cuộc gọi về Khuyến mãi/Đổi gói (churn 21–28%), đặc biệt khi khách đòi hạ gói (churn 30,9%) — chủ động đề xuất giá trị tương đương thay vì để khách tự đi tìm đối thủ."}], "numbers"));
children.push(bullet([{t:"Ưu tiên 3 — Giảm ma sát hóa đơn (dư địa lớn nhất): ",b:true},{t:"minh bạch hóa hóa đơn, thông báo cước & ngày thanh toán chủ động qua app/SMS; đây là khối churn lớn nhất về số tuyệt đối nên cải thiện nhỏ cũng giữ được nhiều thuê bao."}], "numbers"));
children.push(bullet([{t:"Ưu tiên 4 — Triage chất lượng mạng: ",b:true},{t:"với cuộc gọi Internet/Phủ sóng (AHT dài nhất), trang bị công cụ chẩn đoán nhanh cho tư vấn viên và quy trình theo dõi vùng lỗi để chặn bào mòn niềm tin."}], "numbers"));
children.push(bullet([{t:"Ưu tiên 5 — Đẩy mạnh tự phục vụ: ",b:true},{t:"chuyển các tác vụ hành chính lặp lại (tra cứu cước, tạm ngưng, đổi gói cơ bản) sang app MiBitel để giải phóng nguồn lực cho các cuộc giữ chân giá trị cao."}], "numbers"));
children.push(bullet([{t:"Ưu tiên 6 — Cảnh báo sớm theo xu hướng: ",b:true},{t:"theo dõi tỷ lệ ý định rời mạng hàng tháng như một chỉ số sức khỏe (health metric); thiết lập ngưỡng cảnh báo và đối chiếu với động thái giá của Movistar."}], "numbers"));

// --- 10. Limitations ---
children.push(H1("10","Hạn chế & bước tiếp theo"));
children.push(bullet("Phân loại dựa trên từ khóa và STT (không tách người nói) — nên hiệu chỉnh bằng chọn mẫu kiểm tra thủ công định kỳ."));
children.push(bullet("Tập dữ liệu mỗi số điện thoại chỉ có 1 cuộc — chưa đo được hành vi gọi lặp lại theo khách hàng. Đề xuất liên kết với dữ liệu khiếu nại (complain_cc.xls) để dựng hành trình khách hàng đầy đủ và xác định nhóm 'gọi nhiều lần chưa được giải quyết'."));
children.push(bullet("Nên bổ sung dữ liệu kết quả (khách có thực sự rời mạng sau cuộc gọi không) để chuyển từ 'ý định' sang 'churn thực tế' và hiệu chỉnh mô hình dự báo."));
children.push(bullet("Bước tiếp theo gợi ý: thử nghiệm A/B kịch bản 'bàn cứu khách' cho nhóm tín hiệu nóng và đo tỷ lệ giữ chân."));

// --- Appendix ---
children.push(H1("","Phụ lục — Định nghĩa & quy tắc"));
children.push(H2("Định nghĩa 'Ý định rời mạng' (churn intent)"));
children.push(bullet([{t:"Tính churn khi: ",b:true},{t:"khách muốn chuyển mạng (portabilidad, portarme, irse a otro operador, cambiarse de operador) HOẶC hủy/đóng line (dar de baja, cancelar la línea/servicio/plan, anular la línea)."}]));
children.push(bullet([{t:"Loại trừ: ",b:true},{t:"khóa máy do mất/trộm (pérdida, robo) không tính là rời mạng tự nguyện."}]));
children.push(bullet([{t:"'Nguy cơ cần giữ chân' (retention risk = "+vn(A.retention_pct)+"%): ",b:true},{t:"rộng hơn, gồm ý định rời + nhắc đối thủ + đòi hạ gói."}]));
children.push(H2("Các chỉ số nền"));
children.push(table([3120,3120,3120],
  ["Chỉ số","Giá trị","Ghi chú"],
  [
   ["Tổng cuộc gọi", fmt(A.total_calls), vn(A.total_talk_hours)+" giờ đàm thoại"],
   ["AHT trung bình", vn(A.aht_min)+" phút", "Trung vị "+vn(A.median_min)+" phút"],
   ["Ý định rời mạng", vn(A.churn_pct)+"%", fmt(A.churn_n)+" cuộc"],
   ["Nguy cơ cần giữ chân", vn(A.retention_pct)+"%", fmt(A.retention_n)+" cuộc"],
   ["Cảm xúc tiêu cực", vn(A.neg_pct)+"%", fmt(A.neg_n)+" cuộc"],
   ["Nhắc đối thủ", vn(A.comp_pct)+"%", fmt(A.comp_n)+" cuộc"],
   ["Độ tin cậy STT", vn(A.avg_conf)+"", A.empty+" transcript rỗng"],
  ]));
children.push(P("— Hết báo cáo —", {align:AlignmentType.CENTER, italics:true, color:SLATE, size:20, before:200}));

// ===================== DOCUMENT =====================
const doc = new Document({
  creator: "Bitel Customer Care Analytics",
  title: "Báo cáo Phân tích Hành vi Khách hàng qua Tổng đài",
  styles: { default: { document: { run: { font: "Arial", size: 22, color: INK } } },
    paragraphStyles: [
      { id:"Heading1", name:"Heading 1", basedOn:"Normal", next:"Normal", quickFormat:true,
        run:{ size:30, bold:true, font:"Arial", color:INK },
        paragraph:{ spacing:{before:320,after:160}, outlineLevel:0 } },
      { id:"Heading2", name:"Heading 2", basedOn:"Normal", next:"Normal", quickFormat:true,
        run:{ size:25, bold:true, font:"Arial", color:DARK },
        paragraph:{ spacing:{before:220,after:110}, outlineLevel:1 } },
    ] },
  numbering: { config: [
    { reference:"bullets", levels:[{ level:0, format:LevelFormat.BULLET, text:"•",
      alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{left:560,hanging:280} } } }] },
    { reference:"numbers", levels:[{ level:0, format:LevelFormat.DECIMAL, text:"%1.",
      alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{left:560,hanging:280} } } }] },
  ] },
  sections: [{
    properties:{ page:{ size:{width:12240,height:15840}, margin:{top:1440,right:1440,bottom:1440,left:1440} } },
    headers:{ default: new Header({ children:[ new Paragraph({
      border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"D9DEE6",space:4}},
      tabStops:[{type:"right",position:9360}],
      children:[ new TextRun({text:"Bitel Perú · Phân tích Hành vi Khách hàng", size:16, color:SLATE, font:"Arial"}),
                 new TextRun({text:"\tKỳ "+A.months_vn[0]+"–"+A.months_vn[A.months_vn.length-1], size:16, color:SLATE, font:"Arial"}) ] }) ] }) },
    footers:{ default: new Footer({ children:[ new Paragraph({ alignment:AlignmentType.CENTER,
      children:[ new TextRun({text:"Trang ", size:16, color:SLATE, font:"Arial"}),
                 new TextRun({ children:[PageNumber.CURRENT], size:16, color:SLATE, font:"Arial"}),
                 new TextRun({text:" / ", size:16, color:SLATE, font:"Arial"}),
                 new TextRun({ children:[PageNumber.TOTAL_PAGES], size:16, color:SLATE, font:"Arial"}) ] }) ] }) },
    children
  }]
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync("output/BaoCao_HanhVi_KhachHang_Bitel.docx", buf);
  console.log("→ output/BaoCao_HanhVi_KhachHang_Bitel.docx ("+(buf.length/1024).toFixed(0)+" KB)"); });
