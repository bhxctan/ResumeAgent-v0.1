import base64, unittest
from unittest.mock import patch
import fitz
import server
from vision import ocr_jd

class ModesOCR(unittest.TestCase):
    def setUp(self):
        self.config={'key':'test-key','base':'https://example.com/v1','model':'test-vision'}
        d=fitz.open(); p=d.new_page(width=400,height=500); p.insert_text((30,50),'Example JD 123'); self.pdf=d.tobytes(); self.img=p.get_pixmap().tobytes('png'); d.close()
        self.payload={'name':'test.pdf','data':base64.b64encode(self.pdf).decode()}
    def test_local_without_api(self):
        with patch('server.parse_vision') as vision:
            out=server.recognize_pdf({**self.payload,'mode':'local'},{'key':''})
            self.assertEqual(out['recognition'],'local');self.assertTrue(out['pages']);vision.assert_not_called()
    def test_vision_dispatch(self):
        with patch('server.parse_vision',return_value={'pages':[]}) as vision:
            self.assertEqual(server.recognize_pdf({**self.payload,'mode':'vision'},self.config)['recognition'],'vision');vision.assert_called_once_with(self.pdf,'test.pdf',self.config)
    def test_unknown_mode(self):
        with self.assertRaisesRegex(ValueError,'未知'): server.recognize_pdf({**self.payload,'mode':'wrong'},self.config)
    def test_ocr_preserves_text_and_uses_only_image(self):
        with patch('vision.call_model',return_value={'text':'岗位职责\n1. 分析数据\n2. [无法辨认]'}) as model:
            self.assertEqual(ocr_jd(self.img,self.config)['text'],'岗位职责\n1. 分析数据\n2. [无法辨认]');args=model.call_args.args;self.assertEqual(args[0],self.config);self.assertEqual(args[1][1]['content'][1]['image_url']['url'],'data:image/png;base64,'+base64.b64encode(self.img).decode())
    def test_ocr_bad_image_and_missing_key(self):
        with patch('vision.call_model') as model:
            for image,cfg in [(b'not-image',self.config),(self.img,{'key':''}),(b'\x89PNG\r\n\x1a\ninvalid',self.config)]:
                with self.assertRaises(ValueError):ocr_jd(image,cfg)
            model.assert_not_called()
    def test_ocr_empty(self):
        with patch('vision.call_model',return_value={'text':''}):
            with self.assertRaisesRegex(ValueError,'未识别'):ocr_jd(self.img,self.config)
