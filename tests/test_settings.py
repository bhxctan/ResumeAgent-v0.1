import unittest
from unittest.mock import patch
from agent import checked_config, test_connection as check_connection, propose
import server

class Settings(unittest.TestCase):
    def setUp(self):
        self.cfg={'key':'test-secret','base':'https://example.com/v1','model':'test-model'}
    def test_blank_key_preserves_existing(self):
        self.assertEqual(checked_config({**self.cfg,'key':''},self.cfg),self.cfg)
    def test_public_config_no_key(self):
        with patch.object(server,'CONFIG',self.cfg):
            self.assertEqual(server.public_config(),{'configured':True,'base':self.cfg['base'],'model':'test-model'})
    def test_insecure_url_rejected(self):
        with self.assertRaises(ValueError): checked_config({**self.cfg,'base':'http://example.com/v1'},self.cfg)
    def test_connection_no_resume(self):
        with patch('agent.call_model',return_value={'ok':True}) as call:
            self.assertEqual(check_connection(self.cfg),{'ok':True})
            self.assertEqual(call.call_args.args[0],self.cfg)
            self.assertEqual(call.call_args.args[1][-1]['content'],'Return {"ok": true}.')
    def test_jd_uses_config(self):
        rows=[{'id':'a','kind':'paragraph','region':'body','text':'example'}]
        with patch('agent.call_model',return_value={'edits':[]}) as call:
            propose({'jd':'example JD','original':rows,'current':rows},self.cfg)
            self.assertEqual(call.call_args.args[0],self.cfg)
if __name__=='__main__':unittest.main()
