import json, base64, os, webbrowser
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from parser import parse_pdf,learn_template
from agent import propose
STATIC=Path(__file__).parent/'static'
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
        if self.path not in files: self.send_error(404); return
        data=(STATIC/files[self.path]).read_bytes(); self.send_response(200); self.send_header('Content-Type',{'/':'text/html','/app.js':'application/javascript','/style.css':'text/css'}[self.path]+'; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>30*1024*1024: raise ValueError('请求过大')
            p=json.loads(self.rfile.read(length));
            if self.path in ('/api/import','/api/template'):
                result=parse_pdf(base64.b64decode(p['data'],validate=True),str(p.get('name','resume.pdf')))
                if self.path=='/api/template': result=learn_template(result)
            elif self.path=='/api/jd': result=propose(p)
            else: self.send_error(404); return
            self.reply(200,result)
        except Exception as e: self.reply(400,{'error':str(e)[:500]})
    def reply(self,code,result):
        data=json.dumps(result,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
if __name__=='__main__':
    port=int(os.getenv('PORT','8765')); url=f'http://127.0.0.1:{port}'; server=ThreadingHTTPServer(('127.0.0.1',port),Handler); print('Resume Agent:',url); server.serve_forever()
