import unittest,fitz
from parser import parse_pdf,learn_template
from agent import validate
class Core(unittest.TestCase):
    def test_import(self):
        d=fitz.open();p=d.new_page(width=595,height=842);p.insert_text((45,45),'Name',fontsize=18);p.insert_text((45,85),'Education',fontsize=12);p.insert_text((45,104),'Example University',fontsize=10);p.insert_text((45,140),'Experience',fontsize=12);p.insert_text((45,160),'Analyzed 496 surveys',fontsize=10);raw=d.tobytes();d.close();out=parse_pdf(raw);p=out['pages'][0];self.assertEqual(p['blocks'][0]['region'],'header');self.assertEqual(p['blocks'][1]['kind'],'heading');self.assertGreater(p['bodyWidth'],100-1);self.assertIn('heading',learn_template(out)['styles'])
    def test_guard(self):
        orig=[{'id':'a','text':'Analyzed 496 surveys','region':'body','kind':'paragraph'},{'id':'b','text':'Name','region':'header','kind':'paragraph'}];out=validate({'edits':[{'id':'a','action':'rewrite','text':'Analyzed 996 surveys','evidence':['Analyzed 496 surveys']},{'id':'b','action':'rewrite','text':'Other','evidence':['Name']}]},orig,orig);self.assertEqual(len(out['edits']),1);self.assertTrue(out['edits'][0]['flags'])
if __name__=='__main__':unittest.main()
