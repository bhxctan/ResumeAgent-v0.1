import unittest
from unittest.mock import patch
from agent import checked_config, test_connection as check_connection, propose, list_models
import json
import urllib.error
import server

class Settings(unittest.TestCase):
    def setUp(self):
        self.cfg={'key':'test-secret','base':'https://example.com/v1','model':'test-model'}
    def test_blank_key_preserves_existing(self):
        self.assertEqual(checked_config({**self.cfg,'key':''},self.cfg),self.cfg)
    def test_public_config_no_key(self):
        with patch.object(server,'CONFIG',self.cfg):
            self.assertEqual(server.public_config()['jd'],{'configured':True,'base':self.cfg['base'],'model':'test-model'});self.assertNotIn('key',server.public_config()['vision'])
    def test_changed_endpoint_never_reuses_key(self):
        payload={**self.cfg,'base':'https://other.example/v1','key':''}
        with self.assertRaises(ValueError): checked_config(payload,self.cfg)
        self.assertEqual(server.save_slot(payload,self.cfg)['key'],'')
    def test_blank_slot_allowed(self):
        cfg={**self.cfg,'key':''}
        self.assertEqual(server.save_slot(cfg,cfg),cfg)
    def test_insecure_url_rejected(self):
        with self.assertRaises(ValueError): checked_config({**self.cfg,'base':'http://example.com/v1'},self.cfg)
    def test_connection_no_resume(self):
        with patch('agent.call_model',return_value={'ok':True}) as call:
            self.assertEqual(check_connection(self.cfg),{'ok':True})
            self.assertEqual(call.call_args.args[0],self.cfg)
            self.assertEqual(call.call_args.args[1][-1]['content'],'Return {"ok": true}.')
    def test_list_models_get_no_resume(self):
        with patch('agent.urllib.request.build_opener') as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value=json.dumps({'data':[{'id':'b'},{'id':'a'},{'id':'b'},{}]}).encode()
            self.assertEqual(list_models(self.cfg),{'models':['a','b']})
            req=opener.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url,'https://example.com/v1/models')
            self.assertEqual(req.get_method(),'GET'); self.assertIsNone(req.data)
            self.assertEqual(req.get_header('Authorization'),'Bearer test-secret')
    def test_model_list_error_does_not_echo_secret(self):
        with patch('agent.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=urllib.error.HTTPError('https://example.com/v1/models',403,'test-secret',None,None)
            with self.assertRaisesRegex(ValueError,'HTTP 403') as error: list_models(self.cfg)
            self.assertNotIn('test-secret',str(error.exception))
    def test_jd_uses_config(self):
        rows=[{'id':'a','kind':'paragraph','region':'body','text':'example'}]
        with patch('agent.call_model',return_value={'edits':[]}) as call:
            propose({'jd':'example JD','original':rows,'current':rows},self.cfg)
            self.assertEqual(call.call_args.args[0],self.cfg)
if __name__=='__main__':unittest.main()
