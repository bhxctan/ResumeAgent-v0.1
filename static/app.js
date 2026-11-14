'use strict';
const $=s=>document.querySelector(s), clone=x=>JSON.parse(JSON.stringify(x));
let doc=null,base=null,history=[],projectToken=0;
const notify=s=>$('#status').textContent=s;
const txt=b=>b.runs.map(r=>r.text).join('');
function facts(d){return d.pages.flatMap(p=>p.blocks.filter(b=>b.kind!=='image').map(b=>({id:b.id,kind:b.kind,region:b.region,text:txt(b)})))}
function snapshot(){if(doc){history.push(clone(doc));if(history.length>25)history.shift()}}
async function api(path,payload){const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await res.json();if(!res.ok)throw new Error(data.error||'请求失败');return data}
async function readPdf(file,path){if(!file||file.size>20*1024*1024)throw new Error('请选择不超过20MB的PDF');let data=await new Promise((resolve,reject)=>{let reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file)});return api(path,{name:file.name,data})}
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
function render(){
 if(!doc)return;
 $('#paper').replaceChildren();$('#reference').replaceChildren();$('#filename').textContent=doc.filename;
 for(const p of doc.pages){
  const sheet=element('article','sheet',$('#paper'));sheet.style.width=point(p.width);sheet.style.minHeight=point(p.height);sheet.style.paddingTop=point(p.top);sheet.style.paddingBottom='24pt';
  const hd=element('div','resume-header',sheet), body=element('div','resume-body',sheet), width=Math.min(p.width,Math.max(100,p.bodyWidth));
  hd.style.width=body.style.width=point(width);let contentWidth=width;
  const photo=p.photo;
  if(photo&&safeImage(photo.src)){
   const img=element('img','resume-photo',hd);img.src=photo.src;img.alt='个人照片';const [x,y,x1,y1]=photo.bbox;
   // Reserve photo space without imposing a fixed height on editable text.
   const left=Math.max(0,Math.min(width-(x1-x),x-(p.width-width)/2));
   img.style.left=point(left);img.style.top=point(Math.max(0,y-p.top));img.style.width=point(x1-x);img.style.height=point(y1-y);
   hd.style.minHeight=point(Math.max(0,y1-p.top));contentWidth=Math.max(48,left-6);hd.style.paddingRight=point(width-contentWidth);
  }
  const rowNodes=new Map();
  for(const b of p.blocks){
   let parent=b.region==='header'?hd:body;let grouped=false,members=[];
   if(b.rowId){members=p.blocks.filter(c=>c.region===b.region&&c.rowId===b.rowId).sort((a,c)=>a.bbox[0]-c.bbox[0]);
    if(members.length>1){grouped=true;if(!rowNodes.has(b.rowId)){const row=element('div','resume-row '+(b.region==='header'?'header-row':'body-row'),parent);row.style.marginTop=point(b.gap);rowLayout(row,members,b.region==='header'?contentWidth:width,b.region);rowNodes.set(b.rowId,row)}parent=rowNodes.get(b.rowId);}
   }
   const box=element('div','resume-block '+b.kind,parent);box.dataset.id=b.id;box.style.marginTop=point(grouped?0:b.gap);
   // Full-width flow paragraphs; header keeps left alignment, metadata is aligned by its role.
   box.style.marginLeft='0pt';
   if(grouped){const i=members.indexOf(b);box.style.textAlign=b.region==='header'?'left':i===0?'left':i===members.length-1?'right':'center';if(b.region==='body'&&i===members.length-1&&isDate(b))box.classList.add('date-cell');}
   box.style.lineHeight=point(b.lineHeight||12);if(b.rule)box.style.borderBottom=`1pt solid ${b.rule}`;
   if(b.kind==='image'){const im=element('img','',box);im.src=safeImage(b.src);im.style.width=point(b.bbox[2]-b.bbox[0]);im.alt='简历图片';continue}
   for(const r of b.runs)styleRun(element('span','',box),r);box.contentEditable='plaintext-only';box.spellcheck=false;let saved=txt(b);
   box.addEventListener('focus',()=>{saved=txt(b)});
   box.addEventListener('blur',()=>{const text=box.innerText.replace(/\r/g,'');if(text!==saved){snapshot();setText(b,text);box.replaceChildren();for(const r of b.runs)styleRun(element('span','',box),r);if(grouped)rowLayout(parent,members,b.region==='header'?contentWidth:width,b.region)}});
   box.addEventListener('paste',e=>{e.preventDefault();document.execCommand('insertText',false,(e.clipboardData||window.clipboardData).getData('text/plain'))});
  }
  if(safeImage(p.original)){const im=element('img','reference-page',$('#reference'));im.src=p.original;im.alt='原稿对照';im.style.width=point(p.originalWidth||p.width);im.style.height=point(p.originalHeight||p.height);}
 }
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
$('#file').onchange=async e=>{let file=e.target.files[0];if(!file)return;notify('正在解析 PDF…');try{const d=await readPdf(file,'/api/import');doc=d;base=clone(d);history=[];projectToken++;$('#analysis').replaceChildren();render();notify(d.warnings.join('\n'))}catch(err){notify(err.message)}finally{e.target.value=''}};
$('#template').onchange=async e=>{let f=e.target.files[0];if(!f)return;if(!doc){notify('请先导入自己的简历');e.target.value='';return}flush();let token=projectToken;notify('正在学习模板…');try{let t=await readPdf(f,'/api/template');if(token!==projectToken)throw new Error('简历已更换，请重新选择模板');snapshot();for(const p of doc.pages){let ratio=t.width/p.width;p.width=t.width;p.height=t.height;p.top=t.top;p.bodyWidth=t.bodyWidth;for(const b of p.blocks){b.indent*=ratio;const s=t.styles[b.region==='header'?'header':b.kind];if(!s||!b.runs.length)continue;b.runs=b.runs.map(r=>({...r,...s.run,bold:b.kind==='heading'?s.run.bold:r.bold,text:r.text}));b.lineHeight=s.lineHeight;b.gap=s.gap;if(b.kind==='heading'){if(s.rule)b.rule=s.rule;else delete b.rule}}if(p.photo){p.photo.bbox=t.photoBox||p.photo.bbox.map(v=>v*ratio)}}render();notify('已迁移参考模板的字体、颜色、字号、行距和页面宽度；请对照原稿并检查标题、照片与分页。')}catch(err){notify(err.message)}finally{e.target.value=''}};
$('#original').onclick=()=>{if(!doc)return;const compare=!$('.workbody').classList.contains('compare');$('.workbody').classList.toggle('compare',compare);document.body.classList.toggle('compare-mode',compare);$('#reference-pane').hidden=!compare;$('#original').textContent=compare?'关闭原稿对照':'原稿对照';updatePreviewScale()};$('#undo').onclick=()=>{flush();if(history.length){doc=history.pop();render();notify('已撤销最后一次编辑')}};$('#reset').onclick=()=>{if(base&&confirm('恢复至首次导入的简历？')){snapshot();doc=clone(base);render()}};
$('#add').onclick=()=>{if(!doc)return;flush();snapshot();let p=doc.pages.at(-1),b=p.blocks.filter(b=>b.region==='body'&&b.kind==='paragraph').at(-1),run=b?.runs[0]||{font:'Microsoft YaHei',size:10,color:'#000000',bold:false,italic:false};p.blocks.push({id:crypto.randomUUID(),kind:'paragraph',region:'body',runs:[{...run,text:'双击编辑新增段落'}],indent:0,gap:4,lineHeight:b?.lineHeight||14,bbox:[0,0,0,0]});render()};
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));let a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function stem(){return doc.filename.replace(/\.[^.]+$/,'')}
$('#save').onclick=()=>{if(!doc)return;flush();download(stem()+'.resume.json',JSON.stringify({doc,base}),'application/json')};$('#project').onchange=async e=>{let f=e.target.files[0];if(!f)return;try{let data=JSON.parse(await f.text());if(!Array.isArray(data.doc?.pages)||!Array.isArray(data.base?.pages))throw new Error('项目格式不正确');doc=data.doc;base=data.base;history=[];projectToken++;$('#analysis').replaceChildren();render();notify('已打开项目')}catch(err){notify(err.message)}finally{e.target.value=''}};
$('#export').onclick=async()=>{if(!doc)return;flush();const copy=$('#paper').cloneNode(true);copy.querySelectorAll('[contenteditable]').forEach(el=>{el.setAttribute('contenteditable','plaintext-only');el.setAttribute('spellcheck','false')});let css=await (await fetch('/style.css')).text();download(stem()+'.html','<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>Resume</title><style>'+css+'body{padding:20px}.paper-area{width:max-content;margin:0 auto}@media print{body{padding:0}}</style></head><body>'+copy.outerHTML+'</body></html>','text/html;charset=utf-8')};$('#print').onclick=()=>{if(doc){flush();window.print()}};
function section(parent,title,text){let h=element('h3','',parent);h.textContent=title;let p=element('p','',parent);p.textContent=Array.isArray(text)?text.join('\n'):String(text||'')}
function findBlock(id){for(let p of doc.pages){let i=p.blocks.findIndex(b=>b.id===id);if(i>=0)return {p,i,b:p.blocks[i]}}}
$('#analyze').onclick=async()=>{if(!doc){notify('请先导入简历');return}flush();let jd=$('#jd').value.trim();if(!jd){notify('请粘贴 JD');return}if(!apiConfigured){await openSettings();return}let token=projectToken;let button=$('#analyze');button.disabled=true;notify('正在获取岗位分析与改写建议…');try{let result=await api('/api/jd',{jd,original:facts(base),current:facts(doc)});if(token!==projectToken)throw new Error('简历已更换，请重新分析');let panel=$('#analysis');panel.replaceChildren();let summary=element('div','analysis-summary',panel);section(summary,'岗位性质',result.role);section(summary,'JD 原词',result.keywords);section(summary,'硬性要求',result.requirements);section(summary,'真实经历匹配',result.match);section(summary,'缺口',result.gaps);section(summary,'开头竞争力建议',result.summary);for(let e of result.edits){let card=element('div','proposal',panel);element('b','',card).textContent=e.action==='delete'?'建议删除':'建议改写';section(card,'原文',e.before);if(e.action==='rewrite'){let ta=element('textarea','',card);ta.value=e.text;ta.setAttribute('aria-label','改写建议')}section(card,'原因',e.reason);section(card,'原始事实证据',e.evidence);if(e.flags.length)element('p','warning',card).textContent=e.flags.join('；');let apply=element('button','',card);apply.textContent='接受';let reject=element('button','',card);reject.textContent='保留原文';let status=element('p','done',card);apply.onclick=()=>{flush();let found=findBlock(e.id);if(!found||txt(found.b)!==e.before){status.textContent='原文已变更，请重新分析。';return}if(e.flags.length&&!confirm('存在事实或结构风险，已人工核对？'))return;snapshot();if(e.action==='delete')found.p.blocks.splice(found.i,1);else setText(found.b,card.querySelector('textarea').value);render();apply.disabled=reject.disabled=true;status.textContent='已应用'};reject.onclick=()=>{apply.disabled=reject.disabled=true;status.textContent='已保留原文'}}notify(`生成 ${result.edits.length} 条建议。注意：模型可能误判，必须人工核对。`)}catch(err){notify(err.message)}finally{button.disabled=false}};

let apiConfigured=false;
function showConfig(c){apiConfigured=c.configured;$('#api-state').textContent=c.configured?'JD API 已配置':'JD API 未配置';$('#api-base').value=c.base;$('#api-model').value=c.model;$('#api-key').value='';$('#api-key').placeholder=c.configured?'已配置，留空保留现有密钥':'输入 API Key';}
async function getConfig(){const r=await fetch('/api/settings',{cache:'no-store'});if(!r.ok)throw new Error('无法读取设置');showConfig(await r.json());}
async function openSettings(){if(!$('#settings-dialog').open)$('#settings-dialog').showModal();$('#settings-status').textContent='';try{await getConfig()}catch(e){$('#settings-status').textContent=e.message}}
function configInput(){return {base:$('#api-base').value.trim(),model:$('#api-model').value.trim(),key:$('#api-key').value.trim()}}
$('#settings-open').onclick=$('#settings-inline').onclick=openSettings;
$('#settings-close').onclick=()=>{$('#api-key').value='';$('#settings-dialog').close()};
$('#settings-dialog').addEventListener('close',()=>{$('#api-key').value=''});
async function settingsAction(path,body,onSuccess){let buttons=[...$('#settings-form').querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);$('#settings-status').textContent='处理中…';try{let data=await api(path,body);onSuccess(data)}catch(e){$('#settings-status').textContent=e.message}finally{buttons.forEach(b=>b.disabled=false)}}
$('#settings-form').onsubmit=e=>{e.preventDefault();settingsAction('/api/settings',configInput(),c=>{showConfig(c);$('#settings-status').textContent='已保存到本次运行会话。可以测试连接或关闭设置。'})};
$('#settings-test').onclick=()=>settingsAction('/api/settings/test',configInput(),()=>{$('#settings-status').textContent='连接成功，模型 JSON 输出正常。测试不会自动保存设置。'});
$('#settings-clear').onclick=()=>settingsAction('/api/settings/clear',{},c=>{showConfig(c);$('#settings-status').textContent='已清除当前会话密钥。'});
getConfig().catch(()=>{$('#api-state').textContent='无法读取 API 配置'});
