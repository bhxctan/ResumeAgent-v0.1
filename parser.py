"""Import text-based, predominantly single-column PDF resumes into normal-flow blocks."""
import base64, re, statistics, uuid
from collections import Counter
import fitz

HEAD = re.compile(r'^(教育(?:背景|经历)?|实习(?:经历|经验)?|工作(?:经历|经验)?|项目(?:经历|经验)?|校园(?:经历|实践)?|个人(?:技能|评价|优势|简介)|专业技能|技能(?:证书|荣誉)?|获奖(?:情况|经历)?|荣誉奖项|自我评价|研究经历|科研经历|求职意向|实践经历|作品集|Education|Experience|Projects|Skills|Summary|Awards|Profile|Research)(?:\s*[:：]?)$', re.I)
def uid(): return uuid.uuid4().hex[:12]
def color(n): return f'#{n & 0xffffff:06x}'
def fontname(s): return re.sub(r'^\w{6}\+', '', s or '').replace('"','').replace("'",'')
def style(s):
    return {'font':fontname(s.get('font','')), 'size':round(s.get('size',10),2), 'color':color(s.get('color',0)), 'bold':bool(s.get('flags',0)&16), 'italic':bool(s.get('flags',0)&2)}
def plain(b): return ''.join(s['text'] for s in b['runs'])
def separator(a,b):
    if not a or not b or a[-1].isspace() or b[0].isspace(): return ''
    return ' ' if a[-1].isascii() and b[0].isascii() and a[-1].isalnum() and b[0].isalnum() else ''
def append(runs, s):
    if runs and all(runs[-1].get(k)==v for k,v in s.items() if k!='text'): runs[-1]['text'] += s['text']
    else: runs.append(s.copy())
def union(a,b):
    return [min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]

def same_line(a,b):
    # Baselines differ for mixed fonts (e.g. name + job target); compare vertical overlap too.
    aa,bb=a['bbox'],b['bbox']; ha,hb=aa[3]-aa[1],bb[3]-bb[1]
    overlap=min(aa[3],bb[3])-max(aa[1],bb[1])
    baseline=abs(a.get('baseline',aa[3])-b.get('baseline',bb[3]))
    return (aa[2]<=bb[0]+.5 or bb[2]<=aa[0]+.5) and (overlap>=.55*min(ha,hb) or baseline<=max(2,min(ha,hb)*.23))

def visual_lines(raw):
    # Split large horizontal whitespace between independently positioned spans, not inline bold runs.
    for line in raw['lines']:
        spans=sorted((s for s in line['spans'] if s['text']),key=lambda s:s['bbox'][0]); groups=[]
        for span in spans:
            if not groups or span['bbox'][0]-groups[-1][-1]['bbox'][2]>max(9,min(span['size'],groups[-1][-1]['size'])*1.25): groups.append([span])
            else: groups[-1].append(span)
        for ss in groups:
            bbox=list(ss[0]['bbox'])
            for span in ss[1:]: bbox=union(bbox,span['bbox'])
            text=''.join(s['text'] for s in ss).strip()
            if text: yield ss,bbox,text

def new_label(spans,text):
    # Explicit paragraph labels, including bold Chinese labels such as “传播表现：”.
    return bool(re.match(r'^[•●▪◆·]|^\d+[、.]',text) or re.match(r'^[^：:。！？；;\n]{1,20}[：:]',text) and (spans[0].get('flags',0)&16 or re.match(r'^[\u4e00-\u9fff]{2,12}[：:]',text)))

def split_text_block(raw):
    groups=[]
    lines=list(visual_lines(raw))
    for spans,bbox,text in lines:
        heading=bool(HEAD.fullmatch(text)); size=max(s['size'] for s in spans)
        baseline=statistics.median(s.get('origin',(0,bbox[3]))[1] for s in spans)
        prev=groups[-1] if groups else None
        # Do not collapse short labels, manually separated paragraphs, or horizontally positioned cells.
        last=prev.get('last') if prev else None
        same=prev and same_line({'bbox':last,'baseline':prev['lastBaseline']},{'bbox':bbox,'baseline':baseline})
        edge=raw['bbox'][2]
        short_end=prev and edge-last[2]>size*2.2 and bool(re.search(r'[。！？；.!?;]\s*$',plain(prev)))
        new=not prev or heading or prev['kind']=='heading' or same or bbox[1]-last[3]>size*.55 or abs(bbox[0]-last[0])>max(size*1.3,14) or new_label(spans,text) or short_end
        if new:
            prev={'id':uid(),'kind':'heading' if heading else 'paragraph','runs':[],'bbox':list(bbox),'last':bbox,'lastBaseline':baseline,'baseline':baseline,'sourceLines':1,'lineHeight':round(max(bbox[3]-bbox[1],size*1.12),2)}; groups.append(prev)
        else:
            prev['sourceLines']+=1
            prev['lineHeight']=round(max(prev['lineHeight'],bbox[1]-last[1]),2)
            prev['bbox']=union(prev['bbox'],bbox)
            sep=separator(plain(prev),spans[0]['text'])
            if sep: append(prev['runs'],dict(prev['runs'][-1],text=sep))
        for span in spans: append(prev['runs'],dict(style(span),text=span['text']))
        prev['last']=bbox; prev['lastBaseline']=baseline
    for b in groups: b.pop('last',None); b.pop('lastBaseline',None)
    return groups

def assign_rows(blocks):
    """Group independent same-line cells in header and body; never group multiline paragraphs."""
    rows=[]
    for b in sorted(blocks,key=lambda b:(b['bbox'][1],b['bbox'][0])):
        row=next((r for r in reversed(rows) if b['kind']=='paragraph' and b.get('sourceLines',1)==1 and all(c['region']==b['region'] and c['kind']=='paragraph' and c.get('sourceLines',1)==1 and same_line(c,b) for c in r)),None)
        if row is None: rows.append([b])
        else: row.append(b)
    rows.sort(key=lambda r:min(b['bbox'][1] for b in r))
    for row in rows:
        row.sort(key=lambda b:b['bbox'][0])
        if len(row)>1:
            ident=uid()
            for b in row: b['rowId']=ident
    return rows

def parse_pdf(data, filename='resume.pdf'):
    if len(data)>20*1024*1024: raise ValueError('PDF 超过 20MB')
    doc=fitz.open(stream=data,filetype='pdf')
    try:
        if doc.needs_pass: raise ValueError('请先解除 PDF 密码')
        if len(doc)>10: raise ValueError('最多支持 10 页 PDF')
        result={'version':2,'filename':filename,'pages':[],'warnings':[]}
        for i,page in enumerate(doc):
            width,height=page.rect.width,page.rect.height; blocks=[]; imgs=[]; decorations=[]
            for raw in page.get_text('dict',sort=True)['blocks']:
                if raw['type']==0: blocks.extend(split_text_block(raw))
                elif raw['type']==1 and raw.get('image'):
                    x,y,x1,y1=raw['bbox']; ext=raw.get('ext','png').lower()
                    if ext not in ('png','jpeg','jpg','webp','gif','bmp'):
                        try: im=fitz.Pixmap(raw['image']); data_img=im.tobytes('png'); ext='png'
                        except Exception: continue
                    else: data_img=raw['image']
                    imgs.append({'id':uid(),'bbox':[x,y,x1,y1],'src':f'data:image/{"jpeg" if ext=="jpg" else ext};base64,'+base64.b64encode(data_img).decode()})
            if not blocks: raise ValueError(f'第 {i+1} 页没有可提取文字；扫描版需先 OCR 并人工校验')
            blocks.sort(key=lambda b:(round(b['bbox'][1]/3),b['bbox'][0]))
            headings=[b['bbox'][1] for b in blocks if b['kind']=='heading']
            possible=[im for im in imgs if im['bbox'][0]>width*.48 and im['bbox'][1]<height*.30 and im['bbox'][3]-im['bbox'][1]>32 and im['bbox'][2]-im['bbox'][0]>22]
            photo=max(possible,key=lambda im:(im['bbox'][2]-im['bbox'][0])*(im['bbox'][3]-im['bbox'][1]),default=None) if i==0 else None
            cutoff=(headings[0] if headings else min(height*.17, max(b['bbox'][3] for b in blocks))) if i==0 else 0
            if photo: cutoff=max(cutoff,photo['bbox'][3]) if not headings else cutoff
            for b in blocks:
                b['region']='header' if i==0 and b['bbox'][1]<cutoff-1 and b['kind']!='heading' else 'body'
            body=[b for b in blocks if b['region']=='body']; head=[b for b in blocks if b['region']=='header']
            left=min((b['bbox'][0] for b in body),default=30); right=max((b['bbox'][2] for b in body),default=width-30)
            # Preserve non-photo rasters in the nearest flow position; never leave them as overlapping page overlays.
            for im in imgs:
                if im is photo: continue
                blocks.append({'id':im['id'],'kind':'image','region':'body','runs':[],'bbox':im['bbox'],'src':im['src'],'lineHeight':0})
            blocks.sort(key=lambda b:(round(b['bbox'][1]/3),b['bbox'][0]))
            prev={}; top=min([b['bbox'][1] for b in blocks]+([photo['bbox'][1]] if photo else []))
            rows=assign_rows(blocks)
            blocks=[b for row in rows for b in row]
            for row in rows:
                region=row[0]['region']; last=prev.get(region)
                row_top=min(b['bbox'][1] for b in row)
                row_bottom=max(b['bbox'][3] for b in row)
                gap=round(max(0,row_top-(last if last is not None else (top if region=='header' or not head else max([v['bbox'][3] for v in head]+([photo['bbox'][3]] if photo else []))))),2)
                # The PDF bbox includes font ascenders/descenders and may also
                # include intentional fixed-layout whitespace. Do not carry large
                # fixed gaps into the editable personal-information header.
                if region=='header' and last is not None:
                    sizes=[r['size'] for b in row for r in b['runs']]
                    gap=round(min(gap,4,max(0,min(sizes,default=10)*.25)),2)
                for b in row:
                    box=b['bbox']
                    b['gap']=gap
                    if region=='header' and b.get('sourceLines',1)==1 and b['runs']:
                        size=max(r['size'] for r in b['runs'])
                        b['lineHeight']=round(size*1.12,2)
                    b['indent']=round(max(0,box[0]-left),2)
                    if region=='body' and b['kind']=='heading':
                        for d in page.get_drawings():
                            r=d['rect']
                            if r.width>width*.35 and r.height<=3 and abs(r.y0-box[3])<9 and d.get('color'):
                                b['rule']='#'+''.join(f'{max(0,min(255,round(v*255))):02x}' for v in d['color'][:3]); break
                prev[region]=row_bottom
            result['pages'].append({'width':width,'height':height,'originalWidth':width,'originalHeight':height,'top':max(0,top),'bodyWidth':max(100,min(width-12,width-2*max(6,min(left,width-right)))),'blocks':blocks,'photo':photo,'original': 'data:image/png;base64,'+base64.b64encode(page.get_pixmap(matrix=fitz.Matrix(1.2,1.2),alpha=False).tobytes('png')).decode()})
        result['warnings']=['PDF 不是段落文档；行段、标题、照片位置由启发式识别。字体缺失、矢量装饰、复杂表格或多栏可能与原稿不同，请对照原图检查。']
        return result
    finally: doc.close()

def learn_template(doc):
    p=doc['pages'][0]; result={'width':p['width'],'height':p['height'],'bodyWidth':p['bodyWidth'],'top':p['top'],'photoBox':p['photo']['bbox'] if p.get('photo') else None,'styles':{}}
    for kind in ('heading','paragraph','header'):
        bs=[b for b in p['blocks'] if (b['region']=='header' if kind=='header' else b['region']=='body' and b['kind']==kind) and b['runs']]
        if not bs: continue
        counts=Counter(tuple((k,r[k]) for k in ('font','size','color','bold','italic')) for b in bs for r in b['runs'] for _ in range(max(1,len(r['text']))))
        result['styles'][kind]={'run':dict(counts.most_common(1)[0][0]),'lineHeight':statistics.median(b['lineHeight'] for b in bs),'gap':statistics.median(b['gap'] for b in bs),'rule':next((b['rule'] for b in bs if b.get('rule')),None)}
    return result
