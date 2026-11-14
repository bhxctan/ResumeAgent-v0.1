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
def split_text_block(raw):
    groups=[]
    for line in raw['lines']:
        spans=[s for s in line['spans'] if s['text']]
        if not spans: continue
        bbox=line['bbox']; text=''.join(s['text'] for s in spans).strip(); heading=bool(HEAD.fullmatch(text))
        if not text: continue
        size=max(s['size'] for s in spans)
        prev=groups[-1] if groups else None
        # A separate paragraph on a large vertical gap, changed indent, bullet or heading.
        new=not prev or heading or prev['kind']=='heading' or bbox[1]-prev['last'][3]>size*.65 or abs(bbox[0]-prev['last'][0])>max(size*1.6,18) or bool(re.match(r'^[•●▪◆·]|^\d+[、.]',text))
        if new:
            prev={'id':uid(),'kind':'heading' if heading else 'paragraph','runs':[],'bbox':list(bbox),'last':bbox,'lineHeight':round(max(bbox[3]-bbox[1],size*1.12),2)}; groups.append(prev)
        else:
            prev['lineHeight']=round(max(prev['lineHeight'],bbox[1]-prev['last'][1]),2)
            prev['bbox']=[min(prev['bbox'][0],bbox[0]),min(prev['bbox'][1],bbox[1]),max(prev['bbox'][2],bbox[2]),max(prev['bbox'][3],bbox[3])]
            sep=separator(plain(prev),spans[0]['text'])
            if sep: append(prev['runs'],dict(prev['runs'][-1],text=sep))
        for s in spans: append(prev['runs'],dict(style(s),text=s['text']))
        prev['last']=bbox
    for b in groups: b.pop('last',None)
    return groups

def assign_rows(blocks):
    """Keep horizontally separated text on the same visual line in one flow row."""
    rows=[]
    for b in sorted(blocks,key=lambda b:(b['bbox'][1],b['bbox'][0])):
        box=b['bbox']; row=next((r for r in reversed(rows) if r[0]['region']==b['region'] and b['region']=='body' and b['kind']=='paragraph' and all(c['kind']=='paragraph' and abs(c['bbox'][1]-box[1])<=max(2,min(c['lineHeight'],b['lineHeight'])*.32) and (c['bbox'][2]<=box[0]+.5 or box[2]<=c['bbox'][0]+.5) for c in r)), None)
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
        result={'version':1,'filename':filename,'pages':[],'warnings':[]}
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
                gap=round(max(0,row_top-(last if last is not None else (top if region=='header' or not head else max(v['bbox'][3] for v in head)))),2)
                for b in row:
                    box=b['bbox']
                    b['gap']=gap
                    b['indent']=round(max(0,box[0]-(left if region=='body' else 0)),2)
                    if region=='body' and b['kind']=='heading':
                        for d in page.get_drawings():
                            r=d['rect']
                            if r.width>width*.35 and r.height<=3 and abs(r.y0-box[3])<9 and d.get('color'):
                                b['rule']='#'+''.join(f'{max(0,min(255,round(v*255))):02x}' for v in d['color'][:3]); break
                prev[region]=row_bottom
            result['pages'].append({'width':width,'height':height,'top':max(0,top),'bodyWidth':max(100,min(width,max(right-left+2,width-2*max(0,min(left,width-right))))),'blocks':blocks,'photo':photo,'original': 'data:image/png;base64,'+base64.b64encode(page.get_pixmap(matrix=fitz.Matrix(1.2,1.2),alpha=False).tobytes('png')).decode()})
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
