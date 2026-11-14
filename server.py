import json, base64, os, webbrowser
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from parser import parse_pdf,learn_template
from agent import propose, environment_config, checked_config, test_connection
CONFIG=environment_config()
def public_config():
    return {"configured":bool(CONFIG["key"]),"base":CONFIG["base"],"model":CONFIG["model"]}
STATIC=Path(__file__).parent/'static'
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/api/settings': self.reply(200,public_config()); return
        files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
        if self.path not in files: self.send_error(404); return
        data=(STATIC/files[self.path]).read_bytes(); self.send_response(200); self.send_header('Content-Type',{'/':'text/html','/app.js':'application/javascript','/style.css':'text/css'}[self.path]+'; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        global CONFIG
        try:
            if self.headers.get('Origin') not in (None, 'http://'+self.headers.get('Host','')): raise ValueError('不允许跨站请求')
            if self.headers.get_content_type()!='application/json': raise ValueError('只接受 JSON 请求')
            length=int(self.headers.get('Content-Length','0'))
            if length>30*1024*1024: raise ValueError('请求过大')
            p=json.loads(self.rfile.read(length));
            if self.path in ('/api/import','/api/template'):
                result=parse_pdf(base64.b64decode(p['data'],validate=True),str(p.get('name','resume.pdf')))
                if self.path=='/api/template': result=learn_template(result)
            elif self.path=='/api/settings':
                CONFIG=checked_config(p,CONFIG); result=public_config()
            elif self.path=='/api/settings/test': result=test_connection(checked_config(p,CONFIG))
            elif self.path=='/api/settings/clear':
                CONFIG={**CONFIG,'key':''}; result=public_config()
            elif self.path=='/api/jd': result=propose(p,CONFIG.copy())
            else: self.send_error(404); return
            self.reply(200,result)
        except Exception as e: self.reply(400,{'error':str(e)[:500]})
    def reply(self,code,result):
        data=json.dumps(result,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
if __name__=='__main__':
    port=int(os.getenv('PORT','8765')); url=f'http://127.0.0.1:{port}'; server=ThreadingHTTPServer(('127.0.0.1',port),Handler); print('Resume Agent:',url); server.serve_forever()
