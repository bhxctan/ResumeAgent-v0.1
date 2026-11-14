'use strict';
const $=s=>document.querySelector(s), clone=x=>JSON.parse(JSON.stringify(x));
let doc=null,base=null,history=[],projectToken=0;
const notify=s=>$('#status').textContent=s;
const txt=b=>b.runs.map(r=>r.text).join('');
function facts(d){return d.pages.flatMap(p=>p.blocks.filter(b=>b.kind!=='image').map(b=>({id:b.id,kind:b.kind,region:b.region,rowId:b.rowId,text:txt(b)})))}
function snapshot(){if(doc){history.push(clone(doc));if(history.length>25)history.shift()}}
async function api(path,payload){const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await res.json();if(!res.ok)throw new Error(data.error||'请求失败');return data}
async function readPdf(file,path,mode){if(!file||file.size>20*1024*1024)throw new Error('请选择不超过20MB的PDF');let data=await new Promise((resolve,reject)=>{let reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file)});return api(path,{name:file.name,data,mode})}
function styleRun(span,r){span.style.fontFamily=`"${String(r.font||'').replace(/["\\\n\r]/g,'')}", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`;span.style.fontSize=(Number(r.size)||10)+'pt';span.style.color=/^#[\da-f]{6}$/i.test(r.color)?r.color:'#000000';span.style.fontWeight=r.bold?'700':'400';span.style.fontStyle=r.italic?'italic':'normal';span.textContent=r.text}
function setText(b,text){const fallback=b.runs[0]||{font:'Microsoft YaHei',size:10,color:'#000000',bold:false,italic:false}; // Preserve unchanged prefix/suffix styling; new content inherits nearby run.
 const old=txt(b); if(old===text)return;let a=0,z=0;while(a<old.length&&a<text.length&&old[a]===text[a])a++;while(z<old.length-a&&z<text.length-a&&old[old.length-1-z]===text[text.length-1-z])z++;
 let pos=0,prefix=[],suffix=[];for(let r of b.runs){const end=pos+r.text.length;if(pos<a)prefix.push({...r,text:r.text.slice(0,Math.min(r.text.length,a-pos))});if(end>old.length-z)suffix.push({...r,text:r.text.slice(Math.max(0,old.length-z-pos))});pos=end}
 let middle=text.slice(a,text.length-z);b.runs=[...prefix,...(middle?[{...(prefix.at(-1)||fallback),text:middle}]:[]),...suffix];if(!b.runs.length)b.runs=[{...fallback,text:''}];}
const point=n=>`${Number(n)||0}pt`;
const element=(tag,cls,parent)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(parent)parent.append(e);return e};
function safeImage(src){return /^data:image\/(png|jpeg|webp|gif|bmp);base64,[A-Za-z0-9+/=]+$/.test(src||'')?src:''}
const isDate=b=>/^(?:\d{4}\s*[年./-].*(?:\d{4}|至今|Present))/i.test(txt(b).trim());
const measureContext=document.createElement('canvas').getContext('2d');
function naturalWidth(b){let w=0;for(const r of b.runs){const font=String(r.font||'').replace(/["\\\n\r]/g,'');measureContext.font=`${r.italic?'italic':'normal'} ${r.bold?'700':'400'} ${(Number(r.size)||10)*4/3}px "${font}", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`;w+=measureContext.measureText(r.text).width*3/4}return w+3;}
function rowLayout(row,members,width,region){
 const n=members.length;
 if(region==='header'){
  row.style.gridTemplateColumns=members.map((b,i)=>i===n-1?'minmax(0,1fr)':`minmax(0,${Math.min(width*.55,naturalWidth(b))}pt)`).join(' ');
 }else if(n===3){
  // Identical side tracks keep the middle cell centered on the page, independent of labels.
  const side=Math.min(width*.38,Math.max(naturalWidth(members[0]),naturalWidth(members[2])));
  row.style.gridTemplateColumns=`minmax(0,${side}pt) minmax(0,1fr) minmax(0,${side}pt)`;row.classList.toggle('date-fits',isDate(members[2])&&naturalWidth(members[2])<=side+.1);
 }else if(n===2){
  const side=Math.min(width*.55,naturalWidth(members[1]));
  row.style.gridTemplateColumns=`minmax(0,1fr) minmax(0,${side}pt)`;row.classList.toggle('date-fits',isDate(members[1])&&naturalWidth(members[1])<=side+.1);
 }else row.style.gridTemplateColumns=`repeat(${n},minmax(0,1fr))`;
}
// Optional project-scoped overrides. Unset fields preserve existing layout.
const layoutFields=[
 {key:'side',group:'page',label:'左右页边距',min:6,max:72,step:1,unit:'pt',fallback:28},
 {key:'top',group:'page',label:'上页边距',min:0,max:72,step:1,unit:'pt',fallback:24},
 {key:'bottom',group:'page',label:'下页边距',min:0,max:72,step:1,unit:'pt',fallback:24},
 {key:'bodyLine',group:'body',label:'正文行距',min:1,max:2,step:.05,unit:'倍',fallback:1.2},
 {key:'paragraph',group:'body',label:'段落间距',min:0,max:24,step:.5,unit:'pt',fallback:2},
 {key:'section',group:'body',label:'章节间距',min:0,max:36,step:.5,unit:'pt',fallback:6},
 {key:'headerLine',group:'header',label:'个人信息行距',min:1,max:1.8,step:.05,unit:'倍',fallback:1.12},
 {key:'headerGap',group:'header',label:'个人信息内部间距',min:0,max:24,step:.5,unit:'pt',fallback:2},
 {key:'headerShift',group:'header',label:'个人信息垂直位置（下移为正）',min:-36,max:36,step:.5,unit:'pt',fallback:0},
 {key:'headerBody',group:'body',label:'正文起始间距（整体移动正文）',min:0,max:36,step:.5,unit:'pt',fallback:4},
 {key:'photoScale',group:'photo',label:'照片大小',min:40,max:120,step:5,unit:'%',fallback:100},
 {key:'photoTop',group:'photo',label:'照片顶部偏移',min:0,max:36,step:.5,unit:'pt',fallback:0}
];
function layoutValue(key){const f=layoutFields.find(f=>f.key===key),v=doc?.layout?.[key];return typeof v==='number'&&Number.isFinite(v)?Math.max(f.min,Math.min(f.max,v)):null;}
function layoutOr(key,original){return layoutValue(key)??original;}
function layoutInitial(f){const p=doc?.pages?.[0];let v=f.fallback;if(p){if(f.key==='side')v=(p.width-p.bodyWidth)/2;else if(f.key==='top')v=p.top;else if(f.key==='photoTop'&&p.photo)v=Math.max(0,p.photo.bbox[1]-p.top);}return Math.min(f.max,Math.max(f.min,Math.round(v/f.step)*f.step));}
function refreshLayoutControls(){
 $('#layout-controls').disabled=!doc;$('#layout-reset').disabled=!doc;$('#layout-empty').hidden=!!doc;
 for(const f of layoutFields){const value=layoutValue(f.key),input=$('#layout-'+f.key);input.value=value??layoutInitial(f);$('#value-'+f.key).textContent=value===null?'原稿':`${Number(value.toFixed(2))} ${f.unit}`;$('#reset-'+f.key).disabled=!doc||value===null;}
 const hasPhoto=!!doc?.pages.some(p=>p.photo&&safeImage(p.photo.src));$('#photo-note').hidden=!hasPhoto;for(const key of ['photoScale','photoTop'])$('#field-'+key).hidden=!hasPhoto;
}
for(const f of layoutFields){const wrap=element('div','layout-field',$('#layout-'+f.group+'-controls'));wrap.id='field-'+f.key;const line=element('div','layout-label',wrap),label=element('label','',line);label.htmlFor='layout-'+f.key;label.textContent=f.label;const value=element('output','',line);value.id='value-'+f.key;value.setAttribute('for',label.htmlFor);const input=element('input','',wrap);input.type='range';input.id=label.htmlFor;input.min=f.min;input.max=f.max;input.step=f.step;const reset=element('button','layout-field-reset',wrap);reset.type='button';reset.id='reset-'+f.key;reset.textContent='恢复此项';let editing=false;
 input.addEventListener('input',()=>{if(!doc)return;if(!editing){snapshot();editing=true;}doc.layout={...doc.layout,[f.key]:Number(input.value)};render();});
 input.addEventListener('change',()=>{editing=false;});input.addEventListener('blur',()=>{editing=false;});
 reset.onclick=()=>{if(!doc)return;snapshot();delete doc.layout[f.key];render();};
}
$('#layout-reset').onclick=()=>{if(!doc)return;snapshot();delete doc.layout;render();};
refreshLayoutControls();
const portraitObservers=[];
function render(){
 if(!doc)return;
 portraitObservers.splice(0).forEach(o=>o.disconnect());
 $('#paper').replaceChildren();$('#reference').replaceChildren();$('#filename').textContent=doc.filename;
 for(const p of doc.pages){
  const sheet=element('article','sheet',$('#paper'));sheet.style.width=point(p.width);sheet.style.minHeight=point(p.height);sheet.style.paddingTop=point(layoutOr('top',p.top));sheet.style.paddingBottom=point(layoutOr('bottom',24));
  const mast=element('div','resume-mast',sheet),hd=element('div','resume-header',mast), body=element('div','resume-body',sheet), width=Math.min(p.width,Math.max(100,layoutValue('side')===null?p.bodyWidth:p.width-2*layoutValue('side')));
  mast.style.width=hd.style.width=body.style.width=point(width);let contentWidth=width;
  const first=p.blocks.find(b=>b.region==='body');
  const sharedHeading=first?.kind==='heading'&&(!first.rowId||p.blocks.filter(b=>b.region==='body'&&b.rowId===first.rowId).length===1);
  let photoPresent=false,seenBody=false,photoBottom=0,firstTitle=null,bodyStartGap=0,portrait=null;
  const photo=p.photo;
  if(photo&&safeImage(photo.src)){
   photoPresent=true;const img=element('img','resume-photo',mast);img.src=photo.src;img.alt='个人照片';const [x,y,x1,y1]=photo.bbox;
   // Portrait is positioned independently; the body title remains in body flow.
   const scale=Math.min(layoutOr('photoScale',100)/100,Math.max(0,width-54)/Math.max(1,x1-x));
   const pw=(x1-x)*scale,ph=(y1-y)*scale,ptop=layoutOr('photoTop',Math.max(0,y-p.top));
   // On manual width/size adjustment anchor photo to the header's right edge.
   const left=Math.max(0,Math.min(width-pw,layoutValue('side')!==null||layoutValue('photoScale')!==null?width-pw:x-(p.width-width)/2));
   img.style.left=point(left);img.style.top=point(ptop);img.style.width=point(pw);img.style.height=point(ph);
   portrait={img,left,pw,ph,ptop};photoBottom=ptop+ph;if(!sharedHeading)mast.style.minHeight=point(photoBottom+2);contentWidth=Math.max(48,left-6);hd.style.paddingRight=point(width-contentWidth);
  }
  const rowNodes=new Map();
  for(const b of p.blocks){
   let parent=b.region==='header'?hd:body;let grouped=false,members=[];
   // The first title may occupy the space beside the lower part of the portrait.
   const originalGap=Math.max(0,Number(b.gap)||0),firstBody=b.region==='body'&&!seenBody,hasHeader=hd.childElementCount>0;
   if(b.region==='body')seenBody=true;
   const besidePhoto=photoPresent&&firstBody&&sharedHeading;
   const gap=b.region==='header'?(hd.querySelector('.resume-block')?layoutOr('headerGap',originalGap):originalGap):firstBody&&hasHeader?layoutOr('headerBody',Math.min(4,originalGap)):b.kind==='heading'?layoutOr('section',originalGap):layoutOr('paragraph',originalGap);
   if(firstBody)bodyStartGap=gap;
   if(b.rowId){members=p.blocks.filter(c=>c.region===b.region&&c.rowId===b.rowId).sort((a,c)=>a.bbox[0]-c.bbox[0]);
    if(members.length>1){grouped=true;if(!rowNodes.has(b.rowId)){const row=element('div','resume-row '+(b.region==='header'?'header-row':'body-row'),parent);row.style.marginTop=point(gap);rowLayout(row,members,b.region==='header'?contentWidth:width,b.region);rowNodes.set(b.rowId,row)}parent=rowNodes.get(b.rowId);}
   }
   const box=element('div','resume-block '+b.kind,parent);box.dataset.id=b.id;box.style.marginTop=point(grouped?0:gap);
   // Full-width flow paragraphs; header keeps left alignment, metadata is aligned by its role.
   box.style.marginLeft='0pt';
   if(grouped){const i=members.indexOf(b);box.style.textAlign=b.region==='header'?'left':i===0?'left':i===members.length-1?'right':'center';if(b.region==='body'&&i===members.length-1&&isDate(b))box.classList.add('date-cell');}
   const lineRatio=layoutValue(b.region==='header'?'headerLine':'bodyLine');const fontSize=Math.max(1,...b.runs.map(r=>Number(r.size)||10));box.style.lineHeight=point(lineRatio===null?(b.lineHeight||12):fontSize*lineRatio);if(besidePhoto){firstTitle=box;box.classList.add('portrait-adjacent-heading');box.style.paddingRight=point(width-contentWidth);}if(b.rule)box.style.borderBottom=`1pt solid ${b.rule}`;
   if(b.kind==='image'){const im=element('img','',box);im.src=safeImage(b.src);im.style.width=point(b.bbox[2]-b.bbox[0]);im.alt='简历图片';continue}
   for(const r of b.runs)styleRun(element('span','',box),r);box.contentEditable='plaintext-only';box.spellcheck=false;let saved=txt(b);
   box.addEventListener('focus',()=>{saved=txt(b)});
   box.addEventListener('blur',()=>{const text=box.innerText.replace(/\r/g,'');if(text!==saved){snapshot();setText(b,text);box.replaceChildren();for(const r of b.runs)styleRun(element('span','',box),r);if(grouped)rowLayout(parent,members,b.region==='header'?contentWidth:width,b.region)}});
   box.addEventListener('paste',e=>{e.preventDefault();document.execCommand('insertText',false,(e.clipboardData||window.clipboardData).getData('text/plain'))});
  }
  // Relative positioning moves text only: the mast's flow height, body and photo do not move.
  // Clamp against the top page edge and the first body block to avoid overlap.
  if(hd.childElementCount){const shift=layoutOr('headerShift',0);hd.style.top=point(Math.max(-layoutOr('top',p.top),Math.min(bodyStartGap,shift)));}
  if(firstTitle&&portrait){
   // The heading and its underline are indivisible. Fit the portrait into the
   // space above the existing underline rather than adding blank title padding.
   const fitPortrait=()=>{
    const {img,left,pw,ph,ptop}=portrait;
    const st=getComputedStyle(firstTitle),border=parseFloat(st.borderBottomWidth)||0;
    // Rectangles include preview scaling; offset sizes are in unscaled CSS px.
    const available=Math.max(0,(firstTitle.offsetTop+firstTitle.offsetHeight-border-mast.offsetTop)*.75-2);
    // Prefer the requested top offset; clamp it if necessary to keep the photo visible.
    const top=Math.min(ptop,Math.max(0,available-Math.min(ph,available*.65)));
    const factor=ph>0?Math.min(1,Math.max(0,available-top)/ph):1;
    const actualW=pw*factor,actualH=ph*factor;
    // Keep the original right edge when the portrait must shrink.
    img.style.left=point(left+pw-actualW);img.style.top=point(top);
    img.style.width=point(actualW);img.style.height=point(actualH);
   };
   fitPortrait();const o=new ResizeObserver(fitPortrait);o.observe(hd);o.observe(firstTitle);portraitObservers.push(o);
  }
  if(safeImage(p.original)){const im=element('img','reference-page',$('#reference'));im.src=p.original;im.alt='原稿对照';im.style.width=point(p.originalWidth||p.width);im.style.height=point(p.originalHeight||p.height);}
 }
 refreshLayoutControls();
 updatePreviewScale();
}
function updatePreviewScale(){
 if(!doc)return;const work=$('.workbody'), compare=work.classList.contains('compare');const pane=$('#editor-pane');
 const pagePx=Math.max(...doc.pages.map(p=>Math.max(p.width,p.originalWidth||p.width)*4/3));const available=pane.clientWidth-24;
 const scale=compare?Math.min(1,Math.max(.20,available/pagePx)):1;
 work.style.setProperty('--preview-scale',String(scale));
}
new ResizeObserver(updatePreviewScale).observe($('.workbody'));
function flush(){if(document.activeElement instanceof HTMLElement)document.activeElement.blur()}
const resumeMode=()=>document.querySelector('input[name="resume-mode"]:checked').value;
function feedback(id,message,state='info'){const el=$(id);el.textContent=message;el.dataset.state=state;el.hidden=!message;}
for(const radio of document.querySelectorAll('input[name="resume-mode"]'))radio.onchange=()=>{$('#resume-mode-hint').textContent=resumeMode()==='local'?'本地规则识别：无需 API，PDF 不上传；要求原稿有文字层，复杂排版可能误识别。':'AI 视觉识别需要视觉 API，将整页图像及文字样式发送到模型服务。';feedback('#import-status','');};
$('#file').onchange=async e=>{let file=e.target.files[0];if(!file)return;const mode=resumeMode();if(mode==='vision'&&!visionConfigured){feedback('#import-status','请配置视觉模型后重新选择 PDF。','error');e.target.value='';await openSettings();return}if(mode==='vision'&&!confirm('AI 识别将向已配置的模型服务发送整页简历图像（含照片和个人信息）及文字样式，可能产生 API 费用。是否继续？')){e.target.value='';return}const busy=[e.target,$('#project'),...document.querySelectorAll('input[name="resume-mode"]')];busy.forEach(x=>x.disabled=true);feedback('#import-status',mode==='vision'?'视觉 AI 正在识别整页简历…':'正在本地解析 PDF…','pending');try{const d=await readPdf(file,'/api/import',mode);doc=d;base=clone(d);history=[];projectToken++;$('#analysis').replaceChildren();render();feedback('#import-status','识别完成。'+d.warnings.join('\n'),'success');notify('')}catch(err){feedback('#import-status',err.message,'error')}finally{e.target.value='';busy.forEach(x=>x.disabled=false)}};
$('#template').onchange=async e=>{let f=e.target.files[0];if(!f)return;if(!doc){notify('请先导入自己的简历');e.target.value='';return}const mode=resumeMode();if(mode==='vision'&&!visionConfigured){e.target.value='';await openSettings();return}if(mode==='vision'&&!confirm('将参考简历整页图像及文字样式发送至模型服务；请确认已获授权。是否继续？')){e.target.value='';return}flush();let token=projectToken;notify(mode==='vision'?'视觉 AI 正在学习模板…':'正在本地提取模板…');try{let t=await readPdf(f,'/api/template',mode);if(token!==projectToken)throw new Error('简历已更换，请重新选择模板');snapshot();for(const p of doc.pages){let ratio=t.width/p.width;p.width=t.width;p.height=t.height;p.top=t.top;p.bodyWidth=t.bodyWidth;for(const b of p.blocks){b.indent*=ratio;const s=t.styles[b.region==='header'?'header':b.kind];if(!s||!b.runs.length)continue;b.runs=b.runs.map(r=>({...r,...s.run,bold:b.kind==='heading'?s.run.bold:r.bold,text:r.text}));b.lineHeight=s.lineHeight;b.gap=s.gap;if(b.kind==='heading'){if(s.rule)b.rule=s.rule;else delete b.rule}}if(p.photo){p.photo.bbox=t.photoBox||p.photo.bbox.map(v=>v*ratio)}}render();notify('已迁移参考模板的字体、颜色、字号、行距和页面宽度；请对照原稿并检查标题、照片与分页。')}catch(err){notify(err.message)}finally{e.target.value=''}};
$('#original').onclick=()=>{if(!doc)return;const compare=!$('.workbody').classList.contains('compare');$('.workbody').classList.toggle('compare',compare);document.body.classList.toggle('compare-mode',compare);$('#reference-pane').hidden=!compare;$('#original').textContent=compare?'关闭原稿对照':'原稿对照';updatePreviewScale()};$('#undo').onclick=()=>{flush();if(history.length){doc=history.pop();render();notify('已撤销最后一次编辑')}};$('#reset').onclick=()=>{if(base&&confirm('恢复至首次导入的简历？')){snapshot();doc=clone(base);render()}};
$('#add').onclick=()=>{if(!doc)return;flush();snapshot();let p=doc.pages.at(-1),b=p.blocks.filter(b=>b.region==='body'&&b.kind==='paragraph').at(-1),run=b?.runs[0]||{font:'Microsoft YaHei',size:10,color:'#000000',bold:false,italic:false};p.blocks.push({id:crypto.randomUUID(),kind:'paragraph',region:'body',runs:[{...run,text:'双击编辑新增段落'}],indent:0,gap:4,lineHeight:b?.lineHeight||14,bbox:[0,0,0,0]});render()};
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));let a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function stem(){return doc.filename.replace(/\.[^.]+$/,'')}
$('#save').onclick=()=>{if(!doc)return;flush();download(stem()+'.resume.json',JSON.stringify({doc,base}),'application/json')};$('#project').onchange=async e=>{let f=e.target.files[0];if(!f)return;try{let data=JSON.parse(await f.text());if(!Array.isArray(data.doc?.pages)||!Array.isArray(data.base?.pages))throw new Error('项目格式不正确');doc=data.doc;base=data.base;history=[];projectToken++;$('#analysis').replaceChildren();render();notify('已打开项目')}catch(err){notify(err.message)}finally{e.target.value=''}};
$('#export').onclick=async()=>{if(!doc)return;flush();const copy=$('#paper').cloneNode(true);copy.querySelectorAll('[contenteditable]').forEach(el=>{el.setAttribute('contenteditable','plaintext-only');el.setAttribute('spellcheck','false')});let css=await (await fetch('/style.css')).text();download(stem()+'.html','<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>Resume</title><style>'+css+'body{padding:20px}.paper-area{width:max-content;margin:0 auto}@media print{body{padding:0}}</style></head><body>'+copy.outerHTML+'</body></html>','text/html;charset=utf-8')};$('#print').onclick=()=>{if(doc){flush();window.print()}};
function section(parent,title,text){let h=element('h3','',parent);h.textContent=title;let p=element('p','',parent);p.textContent=Array.isArray(text)?text.join('\n'):String(text||'')}
function findBlock(id){for(let p of doc.pages){let i=p.blocks.findIndex(b=>b.id===id);if(i>=0)return {p,i,b:p.blocks[i]}}}
$('#analyze').onclick=async()=>{if(!doc){notify('请先导入简历');return}flush();let jd=$('#jd').value.trim();if(!jd){notify('请粘贴 JD 或识别截图文字');return}if(!jdConfigured){await openSettings();return}let token=projectToken;let button=$('#analyze');button.disabled=true;notify('正在获取岗位分析与改写建议…');try{let result=await api('/api/jd',{jd,original:facts(base),current:facts(doc)});if(token!==projectToken)throw new Error('简历已更换，请重新分析');let panel=$('#analysis');panel.replaceChildren();let summary=element('div','analysis-summary',panel);section(summary,'岗位性质',result.role);section(summary,'JD 原词',result.keywords);section(summary,'硬性要求',result.requirements);section(summary,'真实经历匹配',result.match);section(summary,'缺口',result.gaps);section(summary,'开头竞争力建议',result.summary);for(let e of result.edits){let card=element('div','proposal',panel);element('b','',card).textContent=e.action==='delete'?'建议删除':'建议改写';section(card,'原文',e.before);if(e.action==='rewrite'){let ta=element('textarea','',card);ta.value=e.text;ta.setAttribute('aria-label','改写建议')}section(card,'原因',e.reason);section(card,'原始事实证据',e.evidence);if(e.flags.length)element('p','warning',card).textContent=e.flags.join('；');let apply=element('button','',card);apply.textContent='接受';let reject=element('button','',card);reject.textContent='保留原文';let status=element('p','done',card);apply.onclick=()=>{flush();let found=findBlock(e.id);if(!found||txt(found.b)!==e.before){status.textContent='原文已变更，请重新分析。';return}if(e.flags.length&&!confirm('存在事实或结构风险，已人工核对？'))return;snapshot();if(e.action==='delete')found.p.blocks.splice(found.i,1);else setText(found.b,card.querySelector('textarea').value);render();apply.disabled=reject.disabled=true;status.textContent='已应用'};reject.onclick=()=>{apply.disabled=reject.disabled=true;status.textContent='已保留原文'}}notify(`生成 ${result.edits.length} 条建议。注意：模型可能误判，必须人工核对。`)}catch(err){notify(err.message)}finally{button.disabled=false}};

let jdConfigured=false,visionConfigured=false;
const providers={
 openai:{base:'https://api.openai.com/v1',jd:['gpt-6-luna','gpt-6.1-sol','gpt-6.1-terra','gpt-6-astra','gpt-4o-mini','gpt-4o'],vision:['gpt-6.1-terra','gpt-6.1-sol','gpt-6-astra','gpt-6-luna','gpt-4o','gpt-4o-mini'],hint:'使用 OpenAI API 密钥，API 与 ChatGPT 订阅独立计费。预设不保证账户权限或旧型号仍可用。'},
 deepseek:{base:'https://api.deepseek.com',jd:['deepseek-flash','deepseek-v4-pro'],vision:['deepseek-flash'],hint:'视觉任务请选支持图片输入的 deepseek-flash，并通过连接测试。'},
 qwen:{base:'https://dashscope.aliyuncs.com/compatible-mode/v1',jd:['qwen-plus','qwen-max'],vision:['qwen-vl-max','qwen-vl-plus'],hint:'默认中国站旧兼容域名；如使用工作空间专属域名或其他区域，请按控制台修改地址。'},
 siliconflow:{base:'https://api.siliconflow.cn/v1',jd:['Qwen/Qwen3-8B','Qwen/Qwen3-VL-32B-Instruct'],vision:['Qwen/Qwen3-VL-32B-Instruct'],hint:'示例模型可编辑，实际可用模型以硅基流动模型广场为准。'},
 custom:{base:'',jd:[],vision:[],hint:'填写兼容 Chat Completions 的可信接口，必须支持 JSON 输出；视觉接口还须支持图片输入。'}
};
const savedSlots={};
const modelChoices={};
function renderOptions(slot){const sel=$('#'+slot+'-models'),model=$('#'+slot+'-model').value,query=$('#'+slot+'-search').value.trim().toLowerCase();const all=(modelChoices[slot]||[]).filter(v=>v.toLowerCase().includes(query));sel.replaceChildren(new Option('选择模型（或下方手动输入）',''),...all.map(v=>new Option(v,v)));sel.value=all.includes(model)?model:'';}
function updateOptions(slot,provider){const p=providers[provider];modelChoices[slot]=[...p[slot]];$('#'+slot+'-search').value='';renderOptions(slot);$('#'+slot+'-hint').textContent=p.hint;}

function inferProvider(base){return Object.keys(providers).find(k=>k!=='custom'&&providers[k].base===base)||(base.includes('.maas.aliyuncs.com/')?'qwen':'custom')}
function showConfig(c){jdConfigured=c.jd.configured;visionConfigured=c.vision.configured;$('#api-state').textContent=`视觉：${visionConfigured?'已配置':'未配置'} · JD：${jdConfigured?'已配置':'未配置'}`;for(const slot of ['jd','vision']){const v=c[slot];savedSlots[slot]=v;const provider=inferProvider(v.base);$('#'+slot+'-provider').value=provider;updateOptions(slot,provider);$('#'+slot+'-base').value=v.base;$('#'+slot+'-model').value=v.model;renderOptions(slot);$('#'+slot+'-key').value='';$('#'+slot+'-key').placeholder=v.configured?'已配置，留空保留现有密钥':'输入 API Key';}}
async function getConfig(){const r=await fetch('/api/settings',{cache:'no-store'});if(!r.ok)throw new Error('无法读取设置');showConfig(await r.json());}
function showSidebar(which){if($('.workbody').classList.contains('compare'))$('#original').click();for(const [name,id] of [['workflow','workflow-panel'],['layout','layout-panel'],['settings','settings-dialog']]){ $('#'+id).hidden=name!==which;$('#'+name+'-open').setAttribute('aria-pressed',String(name===which)); }$('.sidebar-nav').scrollIntoView({block:'nearest'});}
async function openSettings(){showSidebar('settings');if(!savedSlots.jd){try{await getConfig()}catch(e){setModelStatus('settings',e.message,'error')}}}
function openWorkflow(){showSidebar('workflow')}
$('#layout-open').onclick=()=>showSidebar('layout');
function configInput(){const out={};for(const slot of ['jd','vision'])out[slot]={base:$('#'+slot+'-base').value.trim(),model:$('#'+slot+'-model').value.trim(),key:$('#'+slot+'-key').value.trim()};return out}
function clearInputs(){for(const slot of ['jd','vision'])$('#'+slot+'-key').value=''}
$('#settings-open').onclick=$('#settings-inline').onclick=openSettings;
$('#settings-close').onclick=$('#workflow-open').onclick=openWorkflow;
function setModelStatus(slot,message,state='info'){
 const status=$('#'+slot+'-status');status.textContent=message;status.dataset.state=state;status.hidden=!message;
}
async function settingsAction(path,body,onSuccess,slot='settings',pending='处理中…'){
 const controls=[...$('#settings-form').querySelectorAll('button,input,select')];
 const oldDisabled=controls.map(b=>b.disabled);controls.forEach(b=>b.disabled=true);
 setModelStatus(slot,pending,'pending');
 try{const data=await api(path,body);setModelStatus(slot,onSuccess(data),'success');}
 catch(e){setModelStatus(slot,e.message,'error');}
 finally{controls.forEach((b,i)=>b.disabled=oldDisabled[i]);}
}
$('#settings-form').onsubmit=e=>{e.preventDefault();settingsAction('/api/settings',configInput(),c=>{showConfig(c);for(const slot of ['jd','vision'])setModelStatus(slot,'');return '已保存到本次运行会话。';},'settings','正在保存设置…')};
for(const slot of ['jd','vision']){
 const key=$('#'+slot+'-key'),base=$('#'+slot+'-base');
 $('#'+slot+'-provider').onchange=e=>{const p=providers[e.target.value];setModelStatus(slot,'');updateOptions(slot,e.target.value);base.value=p.base;$('#'+slot+'-model').value=p[slot][0]||'';renderOptions(slot);key.value='';key.placeholder=(savedSlots[slot]?.configured&&savedSlots[slot]?.base===p.base)?'已配置，留空保留现有密钥':'请输入该服务商密钥';};
 base.oninput=()=>{setModelStatus(slot,'');modelChoices[slot]=[];renderOptions(slot);key.value='';key.placeholder=(savedSlots[slot]?.configured&&savedSlots[slot]?.base===base.value.trim().replace(/\/$/,''))?'已配置，留空保留现有密钥':'服务地址已修改，请重新输入密钥';};
 $('#'+slot+'-search').oninput=()=>renderOptions(slot);
 $('#'+slot+'-models').onchange=e=>{if(e.target.value){$('#'+slot+'-model').value=e.target.value;setModelStatus(slot,'');}};
 $('#'+slot+'-model').oninput=()=>{renderOptions(slot);setModelStatus(slot,'');};
 key.oninput=()=>setModelStatus(slot,'');
 $('#'+slot+'-fetch').onclick=()=>settingsAction('/api/settings/models',{slot,[slot]:configInput()[slot]},data=>{modelChoices[slot]=data.models;$('#'+slot+'-search').value='';renderOptions(slot);return `获取 ${data.models.length} 个账户模型。列表不代表图片或 JSON 能力，请选择后测试连接。`;},slot,'正在获取账户模型…');
 $('#'+slot+'-test').onclick=()=>settingsAction(slot==='jd'?'/api/settings/test':'/api/settings/test-vision',configInput(),()=>(slot==='jd'?'连接成功：JD JSON 输出正常':'连接成功：视觉模型成功读取合成图')+'。测试不会自动保存设置。',slot,'正在测试连接…');
 $('#'+slot+'-clear').onclick=()=>settingsAction('/api/settings/clear',{slot},c=>{savedSlots[slot]=c[slot];jdConfigured=c.jd.configured;visionConfigured=c.vision.configured;$('#api-state').textContent=`视觉：${visionConfigured?'已配置':'未配置'} · JD：${jdConfigured?'已配置':'未配置'}`;key.value='';key.placeholder='输入 API Key';return '已清除所选模型密钥。';},slot,'正在清除密钥…');
}
getConfig().catch(()=>{$('#api-state').textContent='无法读取 API 配置'});

let jdImage=null,jdImageURL=null;
for(const radio of document.querySelectorAll('input[name="jd-mode"]'))radio.onchange=()=>{$('#jd-image-panel').hidden=document.querySelector('input[name="jd-mode"]:checked').value!=='image';};
$('#jd-image').onchange=e=>{if(jdImageURL)URL.revokeObjectURL(jdImageURL);jdImageURL=null;jdImage=null;$('#jd-image-preview').hidden=true;$('#jd-image-preview').removeAttribute('src');$('#jd-ocr').disabled=true;feedback('#ocr-status','');const f=e.target.files[0];if(!f)return;if(f.size>10*1024*1024||!(/\.(png|jpe?g)$/i.test(f.name))){feedback('#ocr-status','请选择不超过 10MB 的 PNG/JPG 图片。','error');e.target.value='';return}jdImage=f;jdImageURL=URL.createObjectURL(f);$('#jd-image-preview').src=jdImageURL;$('#jd-image-preview').hidden=false;$('#jd-ocr').disabled=false;};
$('#jd-ocr').onclick=async()=>{if(!jdImage||$('#analyze').disabled)return;if(!visionConfigured){feedback('#ocr-status','请先配置支持图片输入的视觉模型。','error');await openSettings();return}if(!confirm('将所选岗位截图发送到视觉模型服务，可能产生 API 费用。是否继续？'))return;const f=jdImage,button=$('#jd-ocr'),file=$('#jd-image'),analyze=$('#analyze');button.disabled=file.disabled=analyze.disabled=true;feedback('#ocr-status','正在识别截图文字…','pending');try{const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f)});const out=await api('/api/jd/ocr',{data});const jd=$('#jd');jd.value=jd.value.trim()?jd.value.trimEnd()+'\n\n'+out.text:out.text;feedback('#ocr-status','文字已追加到下方 JD 输入框，请核对后再分析。','success');}catch(e){feedback('#ocr-status',e.message,'error')}finally{file.disabled=analyze.disabled=false;button.disabled=false;}};
