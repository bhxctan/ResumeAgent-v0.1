from playwright.sync_api import sync_playwright
from pathlib import Path
import json,os
root=Path(__file__).resolve().parents[1]/'static'
# Synthetic project deliberately uses a tall photo; the title and rule must stay together.
photo='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jY9sAAAAASUVORK5CYII='
def b(id,region,kind,text,size,gap,row=None):
 return dict(id=id,region=region,kind=kind,runs=[dict(text=text,font='Arial',size=size,color='#000000',bold=kind=='heading')],bbox=[25,30,200,50],gap=gap,lineHeight=size*1.3,**({'rowId':row} if row else {}))
p={'width':595,'height':842,'bodyWidth':535,'top':25,'photo':{'src':photo,'bbox':[470,25,565,165]},'blocks':[b('name','header','paragraph','Name',30,0),b('info','header','paragraph','Contact information',10,8),b('edu','body','heading','Education',12,30),b('p1','body','paragraph','First paragraph\nSecond line',10,8),b('p2','body','paragraph','Next paragraph',10,6),b('h2','body','heading','Experience',12,17)]}
p['blocks'][2]['rule']='#203580'
d={'filename':'sample.pdf','pages':[p],'warnings':[]}
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
 errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 css_text=(root/'style.css').read_text(); js=(root/'app.js').read_text(); config={'jd':{'base':'https://api.openai.com/v1','model':'gpt-4o-mini','configured':False},'vision':{'base':'https://api.openai.com/v1','model':'gpt-4o','configured':False}}
 page.set_content((root/'index.html').read_text().replace('<link rel="stylesheet" href="/style.css">','<style>'+css_text+'</style>').replace('<script src="/app.js"></script>',''))
 page.evaluate('(d)=>{window.fetch=async p=>p==="/style.css"?new Response(d.css):new Response(JSON.stringify(d.config));window.downloads=[];const orig=URL.createObjectURL.bind(URL);URL.createObjectURL=b=>{window.downloads.push(b);return orig(b)};HTMLAnchorElement.prototype.click=function(){};}',{'css':css_text,'config':config});page.add_script_tag(content=js);page.locator('#project').set_input_files({'name':'sample.json','mimeType':'application/json','buffer':json.dumps({'doc':d,'base':d}).encode()});page.locator('[data-id=edu]').wait_for();page.click('#layout-open')
 def change(key,val):page.locator('#layout-'+key).evaluate('(e,v)=>{e.value=String(v);e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))}',val)
 def css(sel,prop):return page.locator(sel).evaluate('(e,p)=>getComputedStyle(e)[p]',prop)
 def y(sel):return page.locator(sel).bounding_box()['y']
 def bottom(sel):return y(sel)+page.locator(sel).bounding_box()['height']
 before=y('[data-id=edu]');assert abs(before-bottom('[data-id=info]')-4*4/3)<1
 assert page.locator('.resume-body > [data-id=edu]').count()==1
 assert css('[data-id=edu]','paddingBottom')=='0px'
 assert bottom('.resume-photo')>before
 assert page.locator('.resume-photo').bounding_box()['height']<140*4/3
 assert bottom('[data-id=edu]')>=bottom('.resume-photo')+2*4/3-1
 assert css('[data-id=edu]','paddingBottom')=='0px'
 assert y('[data-id=p1]')>=bottom('[data-id=edu]')
 assert css('[data-id=edu]','borderBottomWidth')!='0px'
 header_before=y('[data-id=info]');photo_before=y('.resume-photo')
 change('headerShift',-6);assert abs(y('[data-id=info]')-header_before+8)<1
 assert abs(y('[data-id=edu]')-before)<1
 assert abs(y('.resume-photo')-photo_before)<1
 change('headerShift',3);assert abs(y('[data-id=info]')-header_before-4)<1
 assert abs(y('[data-id=edu]')-before)<1
 change('headerShift',0)
 change('headerBody',0);after=y('[data-id=edu]');assert abs(after-bottom('[data-id=info]'))<1
 change('photoScale',40);assert abs(y('[data-id=edu]')-after)<1
 assert y('[data-id=p1]')>=bottom('.resume-photo')
 change('photoScale',100);change('photoTop',20);assert abs(y('[data-id=edu]')-after)<1
 assert bottom('[data-id=edu]')>=bottom('.resume-photo')+2*4/3-1
 assert css('[data-id=edu]','paddingBottom')=='0px'
 assert y('[data-id=p1]')>=bottom('[data-id=edu]')
 change('photoScale',40);change('photoTop',0)
 change('side',40);assert abs(float(css('.resume-body','width')[:-2])-515*4/3)<1
 change('top',12);assert css('.sheet','paddingTop')=='16px'
 change('bottom',15);assert css('.sheet','paddingBottom')=='20px'
 change('bodyLine',1.5);assert css('[data-id=p1]','lineHeight')=='20px'
 change('paragraph',3);assert css('[data-id=p2]','marginTop')=='4px'
 change('section',6);assert css('[data-id=h2]','marginTop')=='8px'
 change('headerGap',1.5);assert css('[data-id=info]','marginTop')=='2px'
 change('headerLine',1.5);assert css('[data-id=info]','lineHeight')=='20px'
 change('photoTop',3);assert css('.resume-photo','top')=='4px'
 page.click('#save');saved=json.loads(page.evaluate('async()=>await downloads.at(-1).text()'));assert saved['doc']['layout']['photoScale']==40 and saved['base']==d
 page.click('#export');page.wait_for_function('downloads.length===2');html=page.evaluate('async()=>await downloads.at(-1).text()');assert 'line-height: 15pt' in html and 'padding-top: 12pt' in html
 page.click('#reset-bodyLine');assert css('[data-id=p1]','lineHeight')=='17.3333px',css('[data-id=p1]','lineHeight')
 page.click('#layout-reset');assert page.locator('#value-side').inner_text()=='原稿'
 page.click('#undo');assert page.locator('#value-side').inner_text()=='40 pt'
 page.click('#workflow-open');page.locator('#project').set_input_files({'name':'saved.json','mimeType':'application/json','buffer':json.dumps(saved).encode()});page.wait_for_timeout(200);page.click('#layout-open');assert page.locator('#value-photoScale').inner_text()=='40 %'
 assert not errors,errors
 page.emulate_media(media='print');assert css('[data-id=p1]','lineHeight')=='20px';assert css('.sheet','paddingTop')=='16px'
 print('Browser checks passed; heading and rule stay together, portrait fits above rule, header shift remains independent, sliders and export work.')
 browser.close()
