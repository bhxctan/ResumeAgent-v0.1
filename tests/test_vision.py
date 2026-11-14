import unittest,fitz
from unittest.mock import patch
from vision import parse_vision, test_vision_connection as check_vision

class Vision(unittest.TestCase):
    def setUp(self):
        d=fitz.open();p=d.new_page(width=595,height=842);p.insert_text((30,40),'Name',fontsize=20);p.insert_text((150,40),'Target: Operations',fontsize=10);p.insert_text((30,70),'Education',fontsize=12);p.insert_text((30,95),'School',fontsize=10);p.insert_text((220,95),'Major',fontsize=10);p.insert_text((450,95),'2025-2028',fontsize=10);p.insert_text((30,130),'Action: content',fontsize=10);p.insert_text((30,145),'Result: 100 views',fontsize=10);self.raw=d.tobytes();d.close();self.cfg={'key':'mock','base':'https://example.com/v1','model':'vision'}
    def test_semantics(self):
        def cell(text,style='s1'):return {'runs':[{'text':text,'style':style}]}
        def row(region,kind,texts):return {'region':region,'kind':kind,'gap':3,'cells':[cell(s) for s in texts]}
        obj={'top':24,'bodyWidth':535,'photo':None,'rows':[row('header','paragraph',['Name','Target: Operations']),row('body','heading',['Education']),row('body','paragraph',['School','Major','2025-2028']),row('body','paragraph',['Action: content']),row('body','paragraph',['Result: 100 views'])]}
        with patch('vision.call_model',return_value=obj) as api:
            result=parse_vision(self.raw,'test.pdf',self.cfg)
        blocks=result['pages'][0]['blocks'];self.assertEqual(blocks[0]['rowId'],blocks[1]['rowId']);self.assertEqual(len({b['rowId'] for b in blocks[3:6]}),1);self.assertNotIn('rowId',blocks[-1]);self.assertEqual(len(result['warnings']),1);self.assertEqual(result['recognition'],'vision');self.assertTrue(api.call_args.args[1][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
    def test_missing_text_warning(self):
        obj={'rows':[{'region':'header','kind':'paragraph','cells':[{'runs':[{'text':'Name','style':'s0'}]}]}]}
        with patch('vision.call_model',return_value=obj): result=parse_vision(self.raw,'test.pdf',self.cfg)
        self.assertIn('存在差异',result['warnings'][1])
    def test_invalid_structure_no_fallback(self):
        with patch('vision.call_model',return_value={'rows':[]}):
            with self.assertRaises(ValueError):parse_vision(self.raw,'test.pdf',self.cfg)
    def test_scan_photo(self):
        d=fitz.open();d.new_page(width=595,height=842);raw=d.tobytes();d.close()
        obj={'photo':[800,20,950,150],'rows':[{'region':'header','kind':'paragraph','cells':[{'runs':[{'text':'Scan','size':18,'bold':True}]}]}]}
        with patch('vision.call_model',return_value=obj): result=parse_vision(raw,'scan.pdf',self.cfg)
        self.assertTrue(result['pages'][0]['photo']['src'].startswith('data:image/png;base64,'));self.assertIn('没有可提取文字层',result['warnings'][1])
    def test_vision_connect(self):
        with patch('vision.call_model',return_value={'text':'VISION 739'}) as call:
            self.assertEqual(check_vision(self.cfg),{'ok':True});self.assertEqual(call.call_args.args[1][1]['content'][1]['type'],'image_url')
    def test_missing_key(self):
        with self.assertRaises(ValueError):parse_vision(self.raw,'test.pdf',{})
