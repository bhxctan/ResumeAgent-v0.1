import json, base64, os, webbrowser
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from parser import learn_template
from vision import parse_vision,test_vision_connection
from agent import propose, environment_config, checked_config, test_connection, list_models
CONFIG=environment_config()
VISION_CONFIG={'key':os.getenv('RESUME_VISION_API_KEY',CONFIG['key']), 'base':os.getenv('RESUME_VISION_BASE_URL',CONFIG['base']).rstrip('/'), 'model':os.getenv('RESUME_VISION_MODEL','gpt-6.1-terra' if CONFIG['base']=='https://api.openai.com/v1' else CONFIG['model'])}
# Never inherit the text key when the vision endpoint differs.
if VISION_CONFIG['base']!=CONFIG['base'] and not os.getenv('RESUME_VISION_API_KEY'): VISION_CONFIG['key']=''
def public_slot(c):
    return {'configured':bool(c['key']),'base':c['base'],'model':c['model']}
def public_config():
    return {'jd':public_slot(CONFIG),'vision':public_slot(VISION_CONFIG)}
def save_slot(payload,previous):
    # Save endpoint/model without a key, so each feature can be configured independently.
    if not payload.get('key','').strip() and (not previous['key'] or payload.get('base','').strip().rstrip('/')!=previous['base']):
        c=checked_config({**payload,'key':'validation-only'},previous);c['key']='';return c
    return checked_config(payload,previous)
STATIC=Path(__file__).parent/'static'
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/api/settings': self.reply(200,public_config()); return
        files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
        if self.path not in files: self.send_error(404); return
        data=(STATIC/files[self.path]).read_bytes(); self.send_response(200); self.send_header('Content-Type',{'/':'text/html','/app.js':'application/javascript','/style.css':'text/css'}[self.path]+'; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        global CONFIG,VISION_CONFIG
        try:
            if self.headers.get('Origin') not in (None, 'http://'+self.headers.get('Host','')): raise ValueError('不允许跨站请求')
            if self.headers.get_content_type()!='application/json': raise ValueError('只接受 JSON 请求')
            length=int(self.headers.get('Content-Length','0'))
            if length>30*1024*1024: raise ValueError('请求过大')
            p=json.loads(self.rfile.read(length));
            if self.path in ('/api/import','/api/template'):
                result=parse_vision(base64.b64decode(p['data'],validate=True),str(p.get('name','resume.pdf')),VISION_CONFIG.copy())
                if self.path=='/api/template': result=learn_template(result)
            elif self.path=='/api/settings':
                new=save_slot(p['jd'],CONFIG); vision=save_slot(p['vision'],VISION_CONFIG); CONFIG=new; VISION_CONFIG=vision; result=public_config()
            elif self.path=='/api/settings/models':
                slot=p.get('slot')
                if slot not in ('jd','vision'): raise ValueError('请选择模型用途')
                result=list_models(checked_config({**p[slot],'model':'model-list'},CONFIG if slot=='jd' else VISION_CONFIG))
            elif self.path=='/api/settings/test': result=test_connection(checked_config(p['jd'],CONFIG))
            elif self.path=='/api/settings/test-vision': result=test_vision_connection(checked_config(p['vision'],VISION_CONFIG))
            elif self.path=='/api/settings/clear':
                slot=p.get('slot')
                if slot=='jd': CONFIG={**CONFIG,'key':''}
                elif slot=='vision': VISION_CONFIG={**VISION_CONFIG,'key':''}
                else: raise ValueError('请选择清除哪个模型的密钥')
                result=public_config()
            elif self.path=='/api/jd': result=propose(p,CONFIG.copy())
            else: self.send_error(404); return
            self.reply(200,result)
        except Exception as e: self.reply(400,{'error':str(e)[:500]})
    def reply(self,code,result):
        data=json.dumps(result,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
if __name__=='__main__':
    port=int(os.getenv('PORT','8765')); url=f'http://127.0.0.1:{port}'; server=ThreadingHTTPServer(('127.0.0.1',port),Handler); print('Resume Agent:',url); server.serve_forever()
