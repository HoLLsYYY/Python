"""Exercise the actual Windows installer using tiny disposable stand-in executables."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from updater import INSTALL_SCRIPT

@unittest.skipUnless(os.name=='nt','Windows installer')
class WindowsInstallerTests(unittest.TestCase):
 def test_replace_and_rollback(self):
  with tempfile.TemporaryDirectory(prefix='bear installer ') as tmp:
   root=Path(tmp);csc=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
   source=root/'Tiny.cs';good=root/'good.exe';bad=root/'bad.exe'
   source.write_text('using System.IO; class Tiny { static void Main(string[] args) { for(int i=0;i<args.Length-1;i++) if(args[i]=="--update-token") File.WriteAllText(args[i+1],"OK"); } }')
   subprocess.run([str(csc),'/nologo','/target:winexe','/out:'+str(good),str(source)],check=True)
   source.write_text('class Tiny { static void Main() {} }')
   subprocess.run([str(csc),'/nologo','/target:winexe','/out:'+str(bad),str(source)],check=True)
   for label,candidate in [('success',good),('rollback',bad)]:
    folder=root/(label+' with spaces');folder.mkdir();target=folder/'Bear.exe'
    target.write_bytes(good.read_bytes());old_hash=hashlib.sha256(target.read_bytes()).hexdigest()
    marker=folder/'boot ok.txt'
    state={'pid':2147483646,'target':str(target),'candidate':str(candidate),'sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'marker':str(marker)}
    statefile=folder/'install.json';statefile.write_text(json.dumps(state),encoding='utf-8')
    script=folder/'install.ps1';script.write_text(INSTALL_SCRIPT.replace('$attempt -lt 60','$attempt -lt 4'),encoding='utf-8-sig')
    result=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),'-StateFile',str(statefile)],capture_output=True,timeout=45)
    log=(folder/'last-update.txt').read_bytes();text=log.decode('utf-16' if log.startswith(b'\xff\xfe') else 'utf-8-sig')
    self.assertEqual(result.returncode,0,(result.stdout,result.stderr))
    if label=='success':self.assertTrue(marker.exists());self.assertEqual(text.strip(),'OK')
    else:self.assertIn('did not start',text);self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),old_hash)

if __name__=='__main__':unittest.main()

