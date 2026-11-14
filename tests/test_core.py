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
    def test_mixed_size_header_same_row(self):
        d=fitz.open();p=d.new_page(width=595,height=842)
        p.insert_text((30,45),'Name',fontsize=30);p.insert_text((200,45),'Target: Operations',fontsize=12)
        p.insert_text((30,75),'Education',fontsize=12);p.insert_text((30,100),'University',fontsize=10)
        out=parse_pdf(d.tobytes());d.close();header=[b for b in out['pages'][0]['blocks'] if b['region']=='header'];self.assertEqual(len(header),2);self.assertTrue(header[0].get('rowId'));self.assertEqual(header[0]['rowId'],header[1]['rowId'])
    def test_label_and_soft_wrap(self):
        from parser import split_text_block
        def ln(y,text,x1):
            return {'bbox':(30,y,x1,y+12),'spans':[{'text':text,'bbox':(30,y,x1,y+12),'origin':(30,y+10),'size':10,'font':'Chinese','flags':0,'color':0}]}
        raw={'bbox':(30,20,550,76),'lines':[ln(20,'多形式内容创作：负责内容制作与发布',550),ln(34,'持续运营多个平台。',160),ln(48,'传播表现：累计获得多个平台反馈',550),ln(62,'并统计各项数据。',150)]}
        bs=split_text_block(raw);self.assertEqual(len(bs),2);self.assertEqual(bs[0]['sourceLines'],2);self.assertEqual(bs[1]['sourceLines'],2);self.assertTrue(bs[1]['runs'][0]['text'].startswith('传播表现：'))
    def test_guard(self):
        orig=[{'id':'a','text':'Analyzed 496 surveys','region':'body','kind':'paragraph'},{'id':'b','text':'Name','region':'header','kind':'paragraph'}];out=validate({'edits':[{'id':'a','action':'rewrite','text':'Analyzed 996 surveys','evidence':['Analyzed 496 surveys']},{'id':'b','action':'rewrite','text':'Other','evidence':['Name']}]},orig,orig);self.assertEqual(len(out['edits']),1);self.assertTrue(out['edits'][0]['flags'])
if __name__=='__main__':unittest.main()
