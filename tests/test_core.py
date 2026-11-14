import unittest,fitz
from parser import parse_pdf,learn_template
from agent import validate
class Core(unittest.TestCase):
    def test_import(self):
        d=fitz.open();p=d.new_page(width=595,height=842);p.insert_text((45,45),'Name',fontsize=18);p.insert_text((45,85),'Education',fontsize=12);p.insert_text((45,104),'Example University',fontsize=10);p.insert_text((45,140),'Experience',fontsize=12);p.insert_text((45,160),'Analyzed 496 surveys',fontsize=10);raw=d.tobytes();d.close();out=parse_pdf(raw);p=out['pages'][0];self.assertEqual(p['blocks'][0]['region'],'header');self.assertEqual(p['blocks'][1]['kind'],'heading');self.assertGreater(p['bodyWidth'],100-1);self.assertIn('heading',learn_template(out)['styles'])
    def test_horizontal_education_rows(self):
        d=fitz.open();p=d.new_page(width=595,height=842)
        p.insert_text((30,40),'Name',fontsize=18);p.insert_text((30,75),'Education',fontsize=12)
        for y,school,major,date in [(100,'Jinan University','Communication MA','2025-09 - 2028-06'),(120,'Xiangtan University','Journalism BA','2021-09 - 2025-06')]:
            for x,t in [(30,school),(220,major),(455,date)]:p.insert_text((x,y),t,fontsize=10)
        out=parse_pdf(d.tobytes());d.close();blocks=[b for b in out['pages'][0]['blocks'] if b.get('rowId')]
        self.assertEqual(len(blocks),6);self.assertEqual(len({b['rowId'] for b in blocks}),2)
        for group in (blocks[:3],blocks[3:]):
            self.assertEqual(len({b['rowId'] for b in group}),1)
            self.assertEqual(len({b['gap'] for b in group}),1)
    def test_guard(self):
        orig=[{'id':'a','text':'Analyzed 496 surveys','region':'body','kind':'paragraph'},{'id':'b','text':'Name','region':'header','kind':'paragraph'}];out=validate({'edits':[{'id':'a','action':'rewrite','text':'Analyzed 996 surveys','evidence':['Analyzed 496 surveys']},{'id':'b','action':'rewrite','text':'Other','evidence':['Name']}]},orig,orig);self.assertEqual(len(out['edits']),1);self.assertTrue(out['edits'][0]['flags'])
if __name__=='__main__':unittest.main()
