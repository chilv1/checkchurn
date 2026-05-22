// Báo cáo .docx — Chiến dịch gọi RA thu cước (nhóm audio pilot, tách vai pyannote)
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        ImageRun, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
        WidthType, ShadingType, PageNumber, Header, Footer, VerticalAlign } = require("docx");

const A = JSON.parse(fs.readFileSync("output/audio_report_data.json","utf8"));
const INK="0F172A",AMBER="FDC700",RED="E11D48",SLATE="475569",GRAY="F1F5F9",DARK="1F2937",LBLUE="EFF6FF",LAMBER="FFFBEB";

const P=(t,o={})=>new Paragraph({spacing:{after:o.after??120,line:276},alignment:o.align,
  children:[new TextRun({text:t,bold:o.bold,italics:o.italics,size:o.size??22,color:o.color??INK,font:"Arial"})]});
const H1=(n,t)=>new Paragraph({heading:HeadingLevel.HEADING_1,
  children:[new TextRun({text:(n?n+". ":"")+t,bold:true,size:30,color:INK,font:"Arial"})],
  spacing:{before:320,after:150},border:{bottom:{style:BorderStyle.SINGLE,size:10,color:AMBER,space:6}}});
const H2=(t)=>new Paragraph({heading:HeadingLevel.HEADING_2,
  children:[new TextRun({text:t,bold:true,size:24,color:DARK,font:"Arial"})],spacing:{before:200,after:100}});
const bullet=(arr,ref="bullets")=>new Paragraph({numbering:{reference:ref,level:0},spacing:{after:80,line:270},
  children:Array.isArray(arr)?arr.map(r=>new TextRun({text:r.t,bold:r.b,italics:r.i,color:r.c??INK,size:22,font:"Arial"}))
                            :[new TextRun({text:arr,size:22,color:INK,font:"Arial"})]});
function img(path,w,h,t){return new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:80,after:60},
  children:[new ImageRun({type:"png",data:fs.readFileSync(path),transformation:{width:w,height:h},
    altText:{title:t,description:t,name:t}})]});}
const cap=(t)=>new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:150},
  children:[new TextRun({text:t,italics:true,size:18,color:SLATE,font:"Arial"})]});
const border={style:BorderStyle.SINGLE,size:1,color:"D9DEE6"};
const borders={top:border,bottom:border,left:border,right:border,insideHorizontal:border,insideVertical:border};
function cell(text,w,o={}){
  const lines=Array.isArray(text)?text:[{t:text}];
  return new TableCell({width:{size:w,type:WidthType.DXA},borders,
    shading:o.fill?{fill:o.fill,type:ShadingType.CLEAR}:undefined,
    margins:{top:50,bottom:50,left:90,right:90},verticalAlign:VerticalAlign.CENTER,
    children:lines.map(l=>new Paragraph({spacing:{after:0,line:248},alignment:o.align,
      children:[new TextRun({text:l.t,bold:l.b||o.bold,italics:l.i||o.italics,color:l.c||o.color||INK,size:o.size??18,font:"Arial"})]}))});
}
function table(widths,header,rows,o={}){
  const tr=[new TableRow({tableHeader:true,children:header.map((h,i)=>cell(h,widths[i],{bold:true,color:"FFFFFF",fill:DARK,align:i===0?AlignmentType.LEFT:AlignmentType.CENTER}))})];
  rows.forEach((r,ri)=>tr.push(new TableRow({children:r.map((c,i)=>{
    const ob=typeof c==="object"&&!Array.isArray(c);
    return cell(ob?(c.lines||c.t):c,widths[i],{fill:ri%2?GRAY:undefined,align:i===0?AlignmentType.LEFT:AlignmentType.CENTER,bold:ob?c.b:false,color:ob?c.c:undefined,size:o.size??18});
  })})));
  return new Table({width:{size:widths.reduce((a,b)=>a+b,0),type:WidthType.DXA},columnWidths:widths,borders,rows:tr});
}
function callout(title,lines,fill,bar){
  const kids=[new Paragraph({spacing:{after:60},children:[new TextRun({text:title,bold:true,size:22,color:INK,font:"Arial"})]})];
  lines.forEach(l=>kids.push(new Paragraph({spacing:{after:40,line:264},children:[new TextRun({text:l,size:21,color:INK,font:"Arial"})]})));
  return new Table({width:{size:9360,type:WidthType.DXA},columnWidths:[9360],
    borders:{left:{style:BorderStyle.SINGLE,size:24,color:bar},top:{style:BorderStyle.SINGLE,size:2,color:fill},bottom:{style:BorderStyle.SINGLE,size:2,color:fill},right:{style:BorderStyle.SINGLE,size:2,color:fill}},
    rows:[new TableRow({children:[new TableCell({width:{size:9360,type:WidthType.DXA},shading:{fill,type:ShadingType.CLEAR},margins:{top:130,bottom:130,left:180,right:180},children:kids})]})]});
}

const ch=[];
// Title
ch.push(new Paragraph({spacing:{after:40},children:[new TextRun({text:"BITEL PERÚ · CHIẾN DỊCH GỌI RA THU CƯỚC (PILOT)",bold:true,size:20,color:"B45309",font:"Arial"})]}));
ch.push(new Paragraph({spacing:{after:60},children:[new TextRun({text:"Báo cáo Phân tích Cuộc gọi Thu cước qua Audio",bold:true,size:38,color:INK,font:"Arial"})]}));
ch.push(new Paragraph({spacing:{after:40},children:[new TextRun({text:"Análisis de campaña de cobranza saliente — transcripción + diarización (pyannote)",italics:true,size:21,color:SLATE,font:"Arial"})]}));
ch.push(new Paragraph({border:{bottom:{style:BorderStyle.SINGLE,size:14,color:AMBER,space:8}},spacing:{after:160},children:[]}));
ch.push(new Paragraph({spacing:{after:60},children:[
  new TextRun({text:"Nguồn: ",bold:true,size:22,font:"Arial"}),new TextRun({text:`${A.N} cuộc gọi audio (~${A.minutes} phút), tách vai Tư vấn viên/Khách bằng pyannote. `,size:22,font:"Arial"}),
  new TextRun({text:"Loại: ",bold:true,size:22,font:"Arial"}),new TextRun({text:"cuộc gọi RA (outbound) — Bitel chủ động gọi khách nhắc/thu cước (“cpc”).",size:22,font:"Arial"})]}));

// 1. Exec summary
ch.push(H1("1","Tóm tắt điều hành"));
ch.push(P(`Báo cáo phân tích ${A.N} cuộc gọi thu cước (mẫu pilot) được chuyển văn bản và TÁCH VAI từ audio thật. Khác với khiếu nại gọi vào, đây là cuộc gọi RA: tư vấn viên chủ động gọi khách để nhắc/thu cước, nên phân tích tập trung vào PHẢN HỒI của khách.`,{after:140}));
ch.push(callout("Phát hiện chính:",[
  `1.  ${A.paid_pct}% khách phản hồi “tôi ĐÃ thanh toán rồi” (${A.paid}/${A.N}) — kể cả trường hợp trả 2 lần. Chiến dịch đang gọi nhắc nợ nhiều người ĐÃ trả → nghi độ trễ đồng bộ/phản ánh thanh toán. Cần đối soát dữ liệu trước khi gọi.`,
  `2.  Gốc rễ lớn nhất là “phản ánh & xử lý thanh toán”: trả rồi chưa mở line, trả trùng/nhầm số, app bên thứ 3 (B-Pay/Yape) chưa cập nhật.`,
  `3.  “Khuyến mãi & giá không nhất quán”: KM không được áp (27→39,90/79 soles), giá tăng bất thường, khách phải gọi xác minh SMS ưu đãi → mất niềm tin.`,
  `4.  Tư vấn viên nói ${A.avg_ase}%, khách chỉ ${A.avg_cli}% — đặc thù gọi RA. Vì vậy phải TÁCH VAI để không tính nhầm lời tư vấn viên thành “vấn đề của khách”.`,
],LAMBER,AMBER));

// 2. Method
ch.push(H1("2","Bối cảnh & phương pháp"));
ch.push(bullet([{t:"Quy trình: ",b:true},{t:"audio (.mp3 mono) → chuyển văn bản bằng mlx-whisper (chạy GPU Metal M4, model large-v3-turbo) → tách vai bằng pyannote.audio 4.x → phân loại trên lời KHÁCH."}]));
ch.push(bullet([{t:"Phân loại phản hồi: ",b:true},{t:"theo bộ từ khóa tiếng Tây Ban Nha trên lời khách; chi nhánh con & chủ đề gốc rễ được tổng hợp thủ công từ nội dung từng cuộc."}]));
ch.push(callout("Lưu ý quan trọng (đọc trước khi dùng):",[
  `• N=${A.N} là mẫu PILOT — mọi tỷ lệ chỉ mang tính tham khảo, cần thêm mẫu để kết luận thống kê.`,
  "• Đây là cuộc gọi RA thu cước, KHÁC với phân tích khiếu nại gọi vào (Hóa đơn 35%, Internet 32% — xem báo cáo hành vi khách hàng riêng).",
  "• STT/diarization tự động — nên nghe lại ghi âm gốc (qua số thuê bao) trước khi ra quyết định với từng ca.",
],LBLUE,"2563EB"));

// 3. Customer response
ch.push(H1("3","Phản hồi của khách khi được gọi thu cước"));
ch.push(img("output/charts/audio_response.png",560,252,"Phản hồi khách"));
ch.push(cap("Hình 1 — Phân loại phản hồi của khách (từ lời khách đã tách vai)."));
ch.push(table([4600,1300,3460],["Phản hồi","Số cuộc","Ý nghĩa"],
  A.resp_dist.map(([k,v])=>[{t:k,b:true},String(v),{
    "Đã thanh toán rồi (tranh luận)":"Khách khẳng định đã trả — gọi có thể nhầm",
    "Khác / xác nhận thông tin":"Xác nhận danh tính / hỏi đáp ngắn / nhiễu",
    "Thắc mắc nợ / hóa đơn":"Không rõ khoản nợ hoặc xác minh ưu đãi",
    "Số tiền sai / cao bất thường":"Số tiền cao hơn thường lệ",
    "Không phải của tôi / người thân":"Line/gói của người thân",
    "Không trả được / xin khất":"Xin gia hạn vì lý do cá nhân",
    "Muốn đổi / giảm gói":"Nhân dịp hỏi hạ gói",
  }[k]||""])));

// 4. Drill-down
ch.push(H1("4","Chi nhánh lý do chi tiết (drill-down)"));
ch.push(P("Bóc tách lý do con bên trong các nhóm phản hồi lớn (đọc từng cuộc). Cột SĐT để truy ngược ghi âm.",{after:120}));
const order=A.resp_dist.map(([k])=>k);
for(const cat of order){
  const br=A.drill[cat]; if(!br||br.length<2) continue;  // chỉ nhóm có nhiều nhánh
  ch.push(H2(`${cat}`));
  ch.push(table([3400,900,3360,1700],["Nhánh con","Số cuộc","Mô tả","SĐT"],
    br.map(([lab,desc,phs])=>[{t:lab,b:true},String(phs.length),desc,phs.join(", ")])));
  ch.push(new Paragraph({spacing:{after:80},children:[]}));
}
// nhóm 1-nhánh gộp ngắn
const singles=order.filter(k=>A.drill[k]&&A.drill[k].length===1);
if(singles.length){
  ch.push(H2("Các nhóm còn lại (1 cuộc/nhóm)"));
  singles.forEach(k=>ch.push(bullet([{t:k+": ",b:true},{t:`${A.drill[k][0][1]} (${A.drill[k][0][2].join(", ")})`}])));
}

// 5. Root-cause themes
ch.push(H1("5","Chủ đề gốc rễ (cắt ngang các phản hồi)"));
ch.push(img("output/charts/audio_themes.png",560,196,"Chủ đề gốc rễ"));
ch.push(cap("Hình 2 — Bốn nhóm gốc rễ tổng hợp từ nội dung cuộc gọi (một cuộc có thể thuộc nhiều chủ đề)."));
ch.push(table([3000,1100,5260],["Chủ đề gốc rễ","Số cuộc","Mô tả & hàm ý"],
  A.themes.map(([n,d,c])=>[{t:n,b:true,c:RED},`~${c}`,d])));

// 6. Recommendations
ch.push(H1("6","Khuyến nghị hành động"));
ch.push(bullet([{t:"Ưu tiên 1 — Đối soát thanh toán trước khi gọi: ",b:true},{t:"đồng bộ dữ liệu thu cước (kể cả kênh bên thứ 3 B-Pay/Yape) sát thời điểm gọi để không gọi nhắc nợ người đã trả (40% mẫu này)."}],"numbers"));
ch.push(bullet([{t:"Ưu tiên 2 — Rút ngắn độ trễ kích hoạt sau thanh toán: ",b:true},{t:"khách trả rồi nhưng line còn khóa nhiều giờ → cần mở/khôi phục nhanh hơn, hoặc thông báo thời gian xử lý rõ ràng."}],"numbers"));
ch.push(bullet([{t:"Ưu tiên 3 — Minh bạch khuyến mãi & giá: ",b:true},{t:"đảm bảo KM đã đăng ký được áp đúng (tránh 27→39,90/79); chuẩn hóa nội dung SMS ưu đãi để khách không phải gọi xác minh."}],"numbers"));
ch.push(bullet([{t:"Ưu tiên 4 — Quy trình xử lý trả trùng/nhầm số: ",b:true},{t:"hướng dẫn hoàn tiền/cấn trừ rõ ràng cho ca trả 2 lần hoặc trả nhầm sang số người thân."}],"numbers"));
ch.push(bullet([{t:"Ưu tiên 5 — Xử lý thuê bao của người thân: ",b:true},{t:"kịch bản xác minh chủ thể & chu kỳ cước khi người gọi trả hộ line của người khác."}],"numbers"));

// 7. Limitations
ch.push(H1("7","Hạn chế & bước tiếp theo"));
ch.push(bullet(`Mẫu pilot N=${A.N} — cần gom thêm audio để tỷ lệ & các nhánh đủ tin cậy thống kê.`));
ch.push(bullet("Phân nhánh con/chủ đề tổng hợp thủ công — có thể điều chỉnh khi có thêm dữ liệu."));
ch.push(bullet("Đề xuất: chạy mẻ lớn (hàng trăm/nghìn cuộc) trên GPU — pipeline đã sẵn (mlx-whisper + pyannote, ~18x nhanh hơn CPU)."));

// 8. Appendix per-call
ch.push(H1("","Phụ lục — Chi tiết 20 cuộc gọi"));
ch.push(table([1500,1300,900,2600,3060],
  ["SĐT","Tư vấn viên","Th.lượng","Phản hồi","Trích lời khách (TBN)"],
  A.calls.map(c=>[c.phone,c.agent,c.dur+"s",c.resp,{t:c.quote,i:true,size:16}]),{size:16}));
ch.push(P("— Hết báo cáo —",{align:AlignmentType.CENTER,italics:true,color:SLATE,size:20,before:200}));

const doc=new Document({creator:"Bitel Customer Care Analytics",title:"Báo cáo Chiến dịch Thu cước (Audio Pilot)",
  styles:{default:{document:{run:{font:"Arial",size:22,color:INK}}},
    paragraphStyles:[
      {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:30,bold:true,font:"Arial",color:INK},paragraph:{spacing:{before:320,after:150},outlineLevel:0}},
      {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:24,bold:true,font:"Arial",color:DARK},paragraph:{spacing:{before:200,after:100},outlineLevel:1}},
    ]},
  numbering:{config:[
    {reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:560,hanging:280}}}}]},
    {reference:"numbers",levels:[{level:0,format:LevelFormat.DECIMAL,text:"%1.",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:560,hanging:280}}}}]},
  ]},
  sections:[{properties:{page:{size:{width:12240,height:15840},margin:{top:1440,right:1440,bottom:1440,left:1440}}},
    headers:{default:new Header({children:[new Paragraph({border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"D9DEE6",space:4}},
      tabStops:[{type:"right",position:9360}],
      children:[new TextRun({text:"Bitel Perú · Chiến dịch thu cước (audio pilot)",size:16,color:SLATE,font:"Arial"}),
                new TextRun({text:`\t${A.N} cuộc · ${A.minutes} phút`,size:16,color:SLATE,font:"Arial"})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,
      children:[new TextRun({text:"Trang ",size:16,color:SLATE,font:"Arial"}),new TextRun({children:[PageNumber.CURRENT],size:16,color:SLATE,font:"Arial"}),
                new TextRun({text:" / ",size:16,color:SLATE,font:"Arial"}),new TextRun({children:[PageNumber.TOTAL_PAGES],size:16,color:SLATE,font:"Arial"})]})]})},
    children:ch}]});
Packer.toBuffer(doc).then(buf=>{fs.writeFileSync("output/BaoCao_ThuCuoc_Audio_Pilot.docx",buf);
  console.log("→ output/BaoCao_ThuCuoc_Audio_Pilot.docx ("+(buf.length/1024).toFixed(0)+" KB)");});
