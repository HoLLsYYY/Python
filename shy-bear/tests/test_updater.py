import copy,hashlib,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from updater import select_release,verify_candidate,version_tuple,child_environment,Updater

class ReleaseTests(unittest.TestCase):
 def release(self,version='5.1.0'):
  raw=b'MZtest app'
  return {'tag_name':'bear-v'+version,'assets':[{'name':'Bear.exe','state':'uploaded','size':len(raw),'digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'browser_download_url':f'https://github.com/HoLLsYYY/Python/releases/download/bear-v{version}/Bear.exe'}]}
 def test_newest_semantic_version(self):
  self.assertEqual(select_release([self.release('5.2.0'),self.release('5.10.0')])['version'],'5.10.0')
 def test_current_and_older_ignored(self):
  self.assertIsNone(select_release([self.release('5.0.0'),self.release('4.9.9')]))
 def test_other_project_and_prerelease_ignored(self):
  a=self.release();a['tag_name']='v99.0.0';b=self.release();b['prerelease']=True
  c=self.release();c['draft']=True
  self.assertIsNone(select_release([a,b,c]))
 def test_wrong_url_or_missing_digest_rejected(self):
  for field,value in [('browser_download_url','https://evil.example/Bear.exe'),('browser_download_url','http://github.com/HoLLsYYY/Python/releases/download/bear-v5.1.0/Bear.exe'),('digest',''),('size',999999999)]:
   a=self.release();a['assets'][0][field]=value;self.assertIsNone(select_release([a]))
 def test_duplicate_asset_rejected(self):
  a=self.release();a['assets'].append(copy.deepcopy(a['assets'][0]));self.assertIsNone(select_release([a]))
 def test_integrity_and_partial_download(self):
  info=select_release([self.release()])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'Bear.exe';p.write_bytes(b'MZtest app');verify_candidate(p,info)
   p.write_bytes(b'MZtest bad')
   with self.assertRaises(ValueError):verify_candidate(p,info)
   p.write_bytes(b'MZ')
   with self.assertRaises(ValueError):verify_candidate(p,info)
 def test_install_waits_for_animation_and_respects_disabled(self):
  fake=Mock();fake.pending={'version':'5.1.0'};fake.manual=False;fake.control.pet.active=True
  with patch('updater.launch_installer') as install:
   Updater.try_install(fake);install.assert_not_called()
   fake.control.pet.active=False;fake.control.updates.isChecked.return_value=False
   Updater.try_install(fake);install.assert_not_called()
 def test_child_runtime_is_independent(self):
  self.assertEqual(child_environment()['PYINSTALLER_RESET_ENVIRONMENT'],'1')
 def test_invalid_versions_rejected(self):
  for v in ['../9','5.1','5.0.1-beta',None]:
   with self.assertRaises(ValueError):version_tuple(v)

if __name__=='__main__':unittest.main()

